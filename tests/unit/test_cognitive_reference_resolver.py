from dataclasses import FrozenInstanceError

import pytest

from cognition import (
    ConversationContextProjector,
    ConversationSessionService,
    IntentCategory,
    IntentConfidence,
    IntentEvidence,
    InterpretedIntent,
    InvalidReferenceResolutionInputError,
    ReferenceKind,
    ReferenceResolutionInput,
    ReferenceResolutionStatus,
    RuleBasedReferenceResolver,
)


def _intent(category=IntentCategory.CONVERSATION):
    return InterpretedIntent(
        category=category,
        confidence=IntentConfidence.MEDIUM,
        safe_user_text="test",
        evidence=(
            IntentEvidence(evidence_type="rule", safe_excerpt="test", rule_id="test"),
        ),
        requires_reference_resolution=False,
        may_require_clarification=False,
        is_actionable_request=category is IntentCategory.ACTION_REQUEST,
        interpreter_id="test",
        interpreter_version="1",
        context_turn_count_used=1,
    )


def _resolution_input(*turns, current_text: str, intent_category=IntentCategory.CONVERSATION):
    session_service = ConversationSessionService()
    session = session_service.create_session()
    for role, text in turns:
        if role == "assistant":
            session_service.append_assistant_turn(session.session_id, text, "assistant")
        else:
            session_service.append_user_turn(session.session_id, text, "test")
    current_turn = session_service.append_user_turn(session.session_id, current_text, "test")
    source_session, source_turns = session_service.context_source(session.session_id)
    context = ConversationContextProjector().project(source_session, source_turns)
    return session_service, ReferenceResolutionInput(
        current_user_turn=current_turn,
        context=context,
        interpreted_intent=_intent(intent_category),
    )


def _first_reference(result):
    assert len(result.references) == 1
    return result.references[0]


def test_no_reference_input_is_not_applicable_and_deterministic():
    _, resolution_input = _resolution_input(current_text="hello there")
    resolver = RuleBasedReferenceResolver()

    first = resolver.resolve(resolution_input)
    second = resolver.resolve(resolution_input)

    assert first.references == ()
    assert first.has_unresolved_references is False
    assert first.has_ambiguous_references is False
    assert first.to_dict() == second.to_dict()


def test_previous_response_resolves_nearest_assistant_turn():
    _, resolution_input = _resolution_input(
        ("assistant", "first assistant"),
        ("user", "my earlier request"),
        ("assistant", "latest assistant"),
        current_text="use your previous response",
    )

    reference = _first_reference(RuleBasedReferenceResolver().resolve(resolution_input))

    assert reference.status is ReferenceResolutionStatus.RESOLVED
    assert reference.detected_reference.kind is ReferenceKind.PREVIOUS_RESPONSE
    assert reference.selected_candidate.role.value == "assistant"
    assert reference.selected_candidate.safe_excerpt == "latest assistant"


def test_previous_request_resolves_nearest_prior_user_turn_excluding_current():
    _, resolution_input = _resolution_input(
        ("user", "first request"),
        ("assistant", "reply"),
        ("user", "latest request"),
        current_text="compare with my previous request",
    )

    reference = _first_reference(RuleBasedReferenceResolver().resolve(resolution_input))

    assert reference.status is ReferenceResolutionStatus.RESOLVED
    assert reference.detected_reference.kind is ReferenceKind.PREVIOUS_REQUEST
    assert reference.selected_candidate.role.value == "user"
    assert reference.selected_candidate.safe_excerpt == "latest request"


def test_previous_message_resolves_immediately_prior_eligible_turn():
    _, resolution_input = _resolution_input(
        ("user", "first request"),
        ("assistant", "last reply"),
        current_text="summarize the last message",
    )

    reference = _first_reference(RuleBasedReferenceResolver().resolve(resolution_input))

    assert reference.status is ReferenceResolutionStatus.RESOLVED
    assert reference.selected_candidate.safe_excerpt == "last reply"


def test_previous_question_resolves_nearest_observable_question():
    _, resolution_input = _resolution_input(
        ("assistant", "What file?"),
        ("user", "notes.txt"),
        ("assistant", "Which mode?"),
        current_text="answer the previous question",
    )

    reference = _first_reference(RuleBasedReferenceResolver().resolve(resolution_input))

    assert reference.status is ReferenceResolutionStatus.RESOLVED
    assert reference.detected_reference.safe_surface_text == "previous question"
    assert reference.selected_candidate.safe_excerpt == "Which mode?"


def test_previous_result_resolves_only_visible_result_like_turn():
    _, resolution_input = _resolution_input(
        ("assistant", "Result: completed safely"),
        current_text="explain the last result",
    )

    reference = _first_reference(RuleBasedReferenceResolver().resolve(resolution_input))

    assert reference.status is ReferenceResolutionStatus.RESOLVED
    assert reference.detected_reference.kind is ReferenceKind.PREVIOUS_RESULT
    assert "Result" in reference.selected_candidate.safe_excerpt


def test_previous_result_without_visible_candidate_is_unresolved():
    _, resolution_input = _resolution_input(
        ("assistant", "plain reply"),
        current_text="explain the last result",
    )

    result = RuleBasedReferenceResolver().resolve(resolution_input)
    reference = _first_reference(result)

    assert reference.status is ReferenceResolutionStatus.UNRESOLVED
    assert result.has_unresolved_references is True


def test_explicit_quote_resolves_unique_match_and_duplicate_is_ambiguous():
    _, unique = _resolution_input(
        ("assistant", "alpha beta"),
        ("user", "gamma delta"),
        current_text='what about "alpha beta"',
    )
    _, duplicate = _resolution_input(
        ("assistant", "same phrase"),
        ("user", "same phrase"),
        current_text='what about "same phrase"',
    )

    unique_reference = _first_reference(RuleBasedReferenceResolver().resolve(unique))
    duplicate_result = RuleBasedReferenceResolver().resolve(duplicate)
    duplicate_reference = _first_reference(duplicate_result)

    assert unique_reference.status is ReferenceResolutionStatus.RESOLVED
    assert unique_reference.detected_reference.kind is ReferenceKind.EXPLICIT_QUOTE
    assert duplicate_reference.status is ReferenceResolutionStatus.AMBIGUOUS
    assert duplicate_result.has_ambiguous_references is True


def test_neutral_reference_resolves_only_one_salient_candidate():
    _, one_candidate = _resolution_input(
        ("assistant", "single target"),
        current_text="do it",
        intent_category=IntentCategory.ACTION_REQUEST,
    )
    _, multiple_candidates = _resolution_input(
        ("user", "first target"),
        ("assistant", "second target"),
        current_text="do it",
        intent_category=IntentCategory.ACTION_REQUEST,
    )

    resolved = _first_reference(RuleBasedReferenceResolver().resolve(one_candidate))
    ambiguous = _first_reference(RuleBasedReferenceResolver().resolve(multiple_candidates))

    assert resolved.status is ReferenceResolutionStatus.RESOLVED
    assert resolved.detected_reference.kind is ReferenceKind.PRONOUN
    assert resolved.selected_candidate.safe_excerpt == "single target"
    assert ambiguous.status is ReferenceResolutionStatus.AMBIGUOUS


def test_truncated_context_does_not_create_false_certainty():
    session_service = ConversationSessionService()
    session = session_service.create_session()
    session_service.append_assistant_turn(session.session_id, "omitted target", "assistant")
    current_turn = session_service.append_user_turn(session.session_id, "do it", "test")
    source_session, source_turns = session_service.context_source(session.session_id)
    context = ConversationContextProjector(max_turns=1).project(source_session, source_turns)

    result = RuleBasedReferenceResolver().resolve(
        ReferenceResolutionInput(
            current_user_turn=current_turn,
            context=context,
            interpreted_intent=_intent(IntentCategory.ACTION_REQUEST),
        )
    )

    reference = _first_reference(result)
    assert reference.status is ReferenceResolutionStatus.UNRESOLVED


def test_russian_reference_phrases_are_deliberately_narrow():
    _, resolution_input = _resolution_input(
        ("assistant", "\u043e\u0442\u0432\u0435\u0442"),
        current_text="\u0438\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u0439 \u0442\u0432\u043e\u0439 \u043f\u0440\u0435\u0434\u044b\u0434\u0443\u0449\u0438\u0439 \u043e\u0442\u0432\u0435\u0442",
    )

    reference = _first_reference(RuleBasedReferenceResolver().resolve(resolution_input))

    assert reference.status is ReferenceResolutionStatus.RESOLVED
    assert reference.detected_reference.kind is ReferenceKind.PREVIOUS_RESPONSE


def test_cancellation_intent_does_not_resolve_that_as_authorization_target():
    _, resolution_input = _resolution_input(
        ("assistant", "target"),
        current_text="cancel that",
        intent_category=IntentCategory.CANCELLATION,
    )

    result = RuleBasedReferenceResolver().resolve(resolution_input)

    assert result.references == ()


def test_reference_output_is_safe_bounded_and_immutable():
    _, resolution_input = _resolution_input(
        ("assistant", "secret token=sk-test-1234567890secret"),
        current_text="use the previous message",
    )

    reference = _first_reference(RuleBasedReferenceResolver().resolve(resolution_input))

    assert reference.status is ReferenceResolutionStatus.UNRESOLVED
    assert "sk-test" not in str(reference.to_dict())
    assert len(reference.detected_reference.safe_surface_text) <= 80


def test_reference_candidate_excerpt_is_bounded():
    _, resolution_input = _resolution_input(
        ("assistant", "x" * 300),
        current_text="use the previous message",
    )

    reference = _first_reference(RuleBasedReferenceResolver().resolve(resolution_input))

    assert reference.status is ReferenceResolutionStatus.RESOLVED
    assert len(reference.selected_candidate.safe_excerpt) <= 160
    with pytest.raises(FrozenInstanceError):
        reference.context_turn_count_used = 0


def test_resolver_rejects_malformed_input_with_typed_error():
    with pytest.raises(InvalidReferenceResolutionInputError):
        RuleBasedReferenceResolver().resolve(object())


def test_resolver_does_not_mutate_session_or_context():
    session_service, resolution_input = _resolution_input(
        ("assistant", "single target"),
        current_text="do it",
        intent_category=IntentCategory.ACTION_REQUEST,
    )
    before = session_service.turns_snapshot(resolution_input.current_user_turn.session_id)

    result = RuleBasedReferenceResolver().resolve(resolution_input)
    after = session_service.turns_snapshot(resolution_input.current_user_turn.session_id)

    assert result.references[0].status is ReferenceResolutionStatus.RESOLVED
    assert [(turn.sequence, turn.role) for turn in before] == [
        (turn.sequence, turn.role) for turn in after
    ]
    assert resolution_input.context.turns[-1].safe_text == "do it"
