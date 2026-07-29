import pytest

from cognition import (
    AssistantResponseType,
    ClarificationCoordinationError,
    ClarificationRequest,
    ClarificationReason,
    ClarificationStatus,
    CognitiveInteractionService,
    ConversationContextProjector,
    ConversationPersistenceWriteError,
    ConversationRole,
    ConversationSessionNotFoundError,
    ConversationSessionService,
    ConversationTurnInput,
    IntentCategory,
    IntentConfidence,
    IntentEvidence,
    IntentInterpretationError,
    InterpretedIntent,
    DetectedReference,
    ReferenceCandidate,
    ReferenceKind,
    ReferenceResolutionError,
    ReferenceResolutionResult,
    ReferenceResolutionStatus,
    ResolvedReference,
    ResponseCompositionResult,
)


def _test_intent(*, context_turn_count_used: int = 1) -> InterpretedIntent:
    return InterpretedIntent(
        category=IntentCategory.CONVERSATION,
        confidence=IntentConfidence.LOW,
        safe_user_text="hello",
        evidence=(
            IntentEvidence(
                evidence_type="rule",
                safe_excerpt="hello",
                rule_id="conversation_fallback",
            ),
        ),
        requires_reference_resolution=False,
        may_require_clarification=False,
        is_actionable_request=False,
        interpreter_id="test",
        interpreter_version="1",
        context_turn_count_used=context_turn_count_used,
    )


def _test_references(*, context_turn_count_used: int = 1) -> ReferenceResolutionResult:
    candidate = ReferenceCandidate(
        turn_id="turn-1",
        turn_sequence=1,
        role=ConversationRole.USER,
        safe_excerpt="hello",
        match_reason="test",
        recency_rank=1,
        confidence=IntentConfidence.LOW,
    )
    resolved = ResolvedReference(
        detected_reference=DetectedReference(
            kind=ReferenceKind.PREVIOUS_REQUEST,
            safe_surface_text="previous request",
            rule_id="test",
        ),
        status=ReferenceResolutionStatus.RESOLVED,
        selected_candidate=candidate,
        candidates=(candidate,),
        confidence=IntentConfidence.MEDIUM,
        context_turn_count_used=context_turn_count_used,
        resolver_id="test",
        resolver_version="1",
    )
    return ReferenceResolutionResult(
        references=(resolved,),
        has_unresolved_references=False,
        has_ambiguous_references=False,
        context_turn_count_used=context_turn_count_used,
        resolver_id="test",
        resolver_version="1",
    )


def test_missing_session_id_creates_session_and_invokes_delegate_once():
    calls = []
    session_service = ConversationSessionService()

    def delegate(turn_input, user_turn):
        calls.append((turn_input, user_turn))
        return f"reply to {user_turn.text}"

    service = CognitiveInteractionService(session_service, delegate)

    result = service.handle_turn(ConversationTurnInput(text="hello", source="test"))
    turns = session_service.turns_snapshot(result.session.session_id)

    assert len(calls) == 1
    assert result.session.turn_count == 2
    assert result.response.session_id == result.session.session_id
    assert result.response.turn_id == turns[1].turn_id
    assert result.response.text == "reply to hello"
    assert result.response.response_type is AssistantResponseType.MESSAGE
    assert [(turn.sequence, turn.role) for turn in turns] == [
        (1, ConversationRole.USER),
        (2, ConversationRole.ASSISTANT),
    ]


def test_supplied_active_session_is_reused():
    session_service = ConversationSessionService()
    session = session_service.create_session()
    service = CognitiveInteractionService(session_service, lambda *_: "reply")

    result = service.handle_turn(
        ConversationTurnInput(text="hello", source="test", session_id=session.session_id)
    )

    assert result.session.session_id == session.session_id
    assert result.session.turn_count == 2


def test_unknown_session_id_raises_predictable_domain_error():
    service = CognitiveInteractionService(ConversationSessionService(), lambda *_: "reply")

    with pytest.raises(ConversationSessionNotFoundError):
        service.handle_turn(
            ConversationTurnInput(text="hello", source="test", session_id="missing")
        )


def test_delegate_failure_records_safe_error_response_without_corrupting_sequence():
    session_service = ConversationSessionService()

    def failing_delegate(*_):
        raise RuntimeError("provider-like failure sk-test-1234567890secret")

    service = CognitiveInteractionService(session_service, failing_delegate)

    result = service.handle_turn(ConversationTurnInput(text="hello", source="test"))
    turns = session_service.turns_snapshot(result.session.session_id)

    assert result.response.response_type is AssistantResponseType.ERROR
    assert result.response.text == "Conversation response generation failed safely."
    assert [turn.sequence for turn in turns] == [1, 2]
    assert [turn.role for turn in turns] == [ConversationRole.USER, ConversationRole.ASSISTANT]
    assert "sk-test" not in result.response.text


def test_context_projector_runs_after_user_turn_and_composer_runs_once():
    events = []
    session_service = ConversationSessionService()

    class TrackingProjector(ConversationContextProjector):
        def project(self, session, turns):
            events.append(("project", len(turns)))
            return super().project(session, turns)

    class TrackingComposer:
        def compose(self, composition_input):
            events.append(
                (
                    "compose",
                    composition_input.context.included_turn_count,
                    composition_input.current_user_turn.sequence,
                    composition_input.interpreted_intent.category,
                    len(composition_input.reference_resolution.references),
                )
            )
            return ResponseCompositionResult(
                response_type=AssistantResponseType.MESSAGE,
                text="reply",
                context_turn_count_used=composition_input.context.included_turn_count,
                composition_source="test",
            )

    class TrackingInterpreter:
        def interpret(self, interpretation_input):
            events.append(
                (
                    "interpret",
                    interpretation_input.context.included_turn_count,
                    interpretation_input.current_user_turn.sequence,
                )
            )
            return _test_intent(
                context_turn_count_used=interpretation_input.context.included_turn_count
            )

    class TrackingResolver:
        def resolve(self, resolution_input):
            events.append(
                (
                    "resolve",
                    resolution_input.context.included_turn_count,
                    resolution_input.current_user_turn.sequence,
                    resolution_input.interpreted_intent.category,
                )
            )
            return _test_references(
                context_turn_count_used=resolution_input.context.included_turn_count
            )

    service = CognitiveInteractionService(
        session_service=session_service,
        context_projector=TrackingProjector(),
        intent_interpreter=TrackingInterpreter(),
        reference_resolver=TrackingResolver(),
        response_composer=TrackingComposer(),
    )

    result = service.handle_turn(ConversationTurnInput(text="hello", source="test"))
    turns = session_service.turns_snapshot(result.session.session_id)

    assert events == [
        ("project", 1),
        ("interpret", 1, 1),
        ("resolve", 1, 1, IntentCategory.CONVERSATION),
        ("compose", 1, 1, IntentCategory.CONVERSATION, 1),
    ]
    assert [turn.sequence for turn in turns] == [1, 2]
    assert result.context.included_turn_count == 1
    assert result.composition.context_turn_count_used == 1
    assert result.intent.category is IntentCategory.CONVERSATION
    assert result.references.references[0].status is ReferenceResolutionStatus.RESOLVED


def test_interaction_service_calls_coordinator_between_resolver_and_composer_once():
    events = []
    session_service = ConversationSessionService()

    class TrackingInterpreter:
        def interpret(self, interpretation_input):
            events.append("interpret")
            return _test_intent(
                context_turn_count_used=interpretation_input.context.included_turn_count
            )

    class TrackingResolver:
        def resolve(self, resolution_input):
            events.append("resolve")
            return _test_references(
                context_turn_count_used=resolution_input.context.included_turn_count
            )

    class TrackingCoordinator:
        def coordinate(self, coordination_input):
            events.append(
                (
                    "coordinate",
                    coordination_input.reference_resolution is not None,
                    coordination_input.interpreted_intent.category,
                )
            )
            return ClarificationRequest(
                status=ClarificationStatus.NEEDED,
                reason=ClarificationReason.UNCLEAR_CONFIRMATION,
                safe_question="What are you confirming?",
                options=(),
                related_reference_count=0,
                context_turn_count_used=coordination_input.context.included_turn_count,
                coordinator_id="test",
                coordinator_version="1",
                rule_id="test_rule",
            )

    class TrackingComposer:
        def compose(self, composition_input):
            events.append(
                (
                    "compose",
                    composition_input.clarification_request.status,
                    composition_input.clarification_request.safe_question,
                )
            )
            return ResponseCompositionResult(
                response_type=AssistantResponseType.MESSAGE,
                text=composition_input.clarification_request.safe_question,
                context_turn_count_used=composition_input.context.included_turn_count,
                composition_source="test",
            )

    service = CognitiveInteractionService(
        session_service=session_service,
        intent_interpreter=TrackingInterpreter(),
        reference_resolver=TrackingResolver(),
        clarification_coordinator=TrackingCoordinator(),
        response_composer=TrackingComposer(),
    )

    result = service.handle_turn(ConversationTurnInput(text="yes", source="test"))
    turns = session_service.turns_snapshot(result.session.session_id)

    assert events == [
        "interpret",
        "resolve",
        ("coordinate", True, IntentCategory.CONVERSATION),
        ("compose", ClarificationStatus.NEEDED, "What are you confirming?"),
    ]
    assert result.clarification.status is ClarificationStatus.NEEDED
    assert result.response.text == "What are you confirming?"
    assert [turn.role for turn in turns] == [ConversationRole.USER, ConversationRole.ASSISTANT]


def test_projection_failure_preserves_user_turn_without_assistant_turn():
    session_service = ConversationSessionService()

    class FailingProjector:
        def project(self, *_):
            raise RuntimeError("projection failed")

    class UnusedComposer:
        def compose(self, *_):
            raise AssertionError("composer should not run")

    class UnusedInterpreter:
        def interpret(self, *_):
            raise AssertionError("interpreter should not run")

    class UnusedResolver:
        def resolve(self, *_):
            raise AssertionError("resolver should not run")

    service = CognitiveInteractionService(
        session_service=session_service,
        context_projector=FailingProjector(),
        intent_interpreter=UnusedInterpreter(),
        reference_resolver=UnusedResolver(),
        response_composer=UnusedComposer(),
    )

    with pytest.raises(RuntimeError):
        service.handle_turn(ConversationTurnInput(text="hello", source="test"))

    sessions = list(session_service._sessions)
    turns = session_service.turns_snapshot(sessions[0])
    assert [turn.sequence for turn in turns] == [1]
    assert [turn.role for turn in turns] == [ConversationRole.USER]


def test_intent_failure_records_safe_error_and_skips_composer():
    session_service = ConversationSessionService()

    class FailingInterpreter:
        def interpret(self, *_):
            raise IntentInterpretationError("secret sk-test-1234567890secret")

    class UnusedComposer:
        def compose(self, *_):
            raise AssertionError("composer should not run")

    class UnusedResolver:
        def resolve(self, *_):
            raise AssertionError("resolver should not run")

    service = CognitiveInteractionService(
        session_service=session_service,
        context_projector=ConversationContextProjector(),
        intent_interpreter=FailingInterpreter(),
        reference_resolver=UnusedResolver(),
        response_composer=UnusedComposer(),
    )

    result = service.handle_turn(ConversationTurnInput(text="hello", source="test"))
    turns = session_service.turns_snapshot(result.session.session_id)

    assert result.response.response_type is AssistantResponseType.ERROR
    assert result.response.text == "Conversation intent interpretation failed safely."
    assert result.intent is None
    assert result.composition.composition_source == "intent_error_fallback"
    assert [turn.sequence for turn in turns] == [1, 2]
    assert [turn.role for turn in turns] == [ConversationRole.USER, ConversationRole.ASSISTANT]
    assert "sk-test" not in result.response.text


def test_reference_resolution_failure_records_safe_error_and_skips_composer():
    session_service = ConversationSessionService()

    class FailingResolver:
        def resolve(self, *_):
            raise ReferenceResolutionError("secret sk-test-1234567890secret")

    class UnusedComposer:
        def compose(self, *_):
            raise AssertionError("composer should not run")

    service = CognitiveInteractionService(
        session_service=session_service,
        context_projector=ConversationContextProjector(),
        reference_resolver=FailingResolver(),
        response_composer=UnusedComposer(),
    )

    result = service.handle_turn(ConversationTurnInput(text="hello", source="test"))
    turns = session_service.turns_snapshot(result.session.session_id)

    assert result.response.response_type is AssistantResponseType.ERROR
    assert result.response.text == "Conversation reference resolution failed safely."
    assert result.intent is not None
    assert result.references is None
    assert result.composition.composition_source == "reference_error_fallback"
    assert [turn.sequence for turn in turns] == [1, 2]
    assert [turn.role for turn in turns] == [ConversationRole.USER, ConversationRole.ASSISTANT]
    assert "sk-test" not in result.response.text


def test_clarification_coordination_failure_records_safe_error_and_skips_composer():
    session_service = ConversationSessionService()

    class FailingCoordinator:
        def coordinate(self, *_):
            raise ClarificationCoordinationError("secret sk-test-1234567890secret")

    class UnusedComposer:
        def compose(self, *_):
            raise AssertionError("composer should not run")

    service = CognitiveInteractionService(
        session_service=session_service,
        context_projector=ConversationContextProjector(),
        clarification_coordinator=FailingCoordinator(),
        response_composer=UnusedComposer(),
    )

    result = service.handle_turn(ConversationTurnInput(text="hello", source="test"))
    turns = session_service.turns_snapshot(result.session.session_id)

    assert result.response.response_type is AssistantResponseType.ERROR
    assert result.response.text == "Conversation clarification coordination failed safely."
    assert result.intent is not None
    assert result.references is not None
    assert result.clarification is None
    assert result.composition.composition_source == "clarification_error_fallback"
    assert [turn.sequence for turn in turns] == [1, 2]
    assert "sk-test" not in result.response.text


def test_composition_failure_records_safe_error_response():
    session_service = ConversationSessionService()

    class FailingComposer:
        def compose(self, *_):
            raise RuntimeError("provider-like failure sk-test-1234567890secret")

    service = CognitiveInteractionService(
        session_service=session_service,
        context_projector=ConversationContextProjector(),
        response_composer=FailingComposer(),
    )

    result = service.handle_turn(ConversationTurnInput(text="hello", source="test"))
    turns = session_service.turns_snapshot(result.session.session_id)

    assert result.response.response_type is AssistantResponseType.ERROR
    assert result.response.text == "Conversation response generation failed safely."
    assert [turn.sequence for turn in turns] == [1, 2]


def test_assistant_append_persistence_failure_does_not_return_unrecorded_success():
    class FlipRepository:
        def __init__(self):
            self.records = []
            self.fail_after_records = 2

        def load_records(self):
            from cognition import ConversationPersistenceLoadResult

            return ConversationPersistenceLoadResult()

        def save_record(self, record):
            if len(self.records) >= self.fail_after_records:
                raise ConversationPersistenceWriteError("write failed")
            self.records.append(record)

        def delete_record(self, session_id):
            return None

        def close(self):
            return None

    session_service = ConversationSessionService(repository=FlipRepository())
    service = CognitiveInteractionService(session_service, lambda *_: "reply")

    with pytest.raises(ConversationPersistenceWriteError):
        service.handle_turn(ConversationTurnInput(text="hello", source="test"))

    session_id = next(iter(session_service._sessions))
    turns = session_service.turns_snapshot(session_id)
    assert [turn.sequence for turn in turns] == [1]


def test_interaction_service_keeps_no_duplicate_session_dictionary():
    session_service = ConversationSessionService()
    service = CognitiveInteractionService(session_service, lambda *_: "reply")

    assert service.session_service is session_service
    assert "_sessions" not in service.__dict__
