import pytest

from cognition import (
    AssistantResponseType,
    CognitiveInteractionService,
    ConversationContextProjector,
    ConversationPersistenceWriteError,
    ConversationRole,
    ConversationSessionNotFoundError,
    ConversationSessionService,
    ConversationTurnInput,
    ResponseCompositionResult,
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
                )
            )
            return ResponseCompositionResult(
                response_type=AssistantResponseType.MESSAGE,
                text="reply",
                context_turn_count_used=composition_input.context.included_turn_count,
                composition_source="test",
            )

    service = CognitiveInteractionService(
        session_service=session_service,
        context_projector=TrackingProjector(),
        response_composer=TrackingComposer(),
    )

    result = service.handle_turn(ConversationTurnInput(text="hello", source="test"))
    turns = session_service.turns_snapshot(result.session.session_id)

    assert events == [("project", 1), ("compose", 1, 1)]
    assert [turn.sequence for turn in turns] == [1, 2]
    assert result.context.included_turn_count == 1
    assert result.composition.context_turn_count_used == 1


def test_projection_failure_preserves_user_turn_without_assistant_turn():
    session_service = ConversationSessionService()

    class FailingProjector:
        def project(self, *_):
            raise RuntimeError("projection failed")

    class UnusedComposer:
        def compose(self, *_):
            raise AssertionError("composer should not run")

    service = CognitiveInteractionService(
        session_service=session_service,
        context_projector=FailingProjector(),
        response_composer=UnusedComposer(),
    )

    with pytest.raises(RuntimeError):
        service.handle_turn(ConversationTurnInput(text="hello", source="test"))

    sessions = list(session_service._sessions)
    turns = session_service.turns_snapshot(sessions[0])
    assert [turn.sequence for turn in turns] == [1]
    assert [turn.role for turn in turns] == [ConversationRole.USER]


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
