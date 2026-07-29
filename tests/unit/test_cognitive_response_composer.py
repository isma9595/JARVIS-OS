import pytest

from cognition import (
    AssistantResponseType,
    CompatibilityResponseComposer,
    ConversationContextProjector,
    ConversationSessionService,
    IntentCategory,
    IntentConfidence,
    IntentEvidence,
    InterpretedIntent,
    ResponseCompositionInput,
)


def _intent():
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
        context_turn_count_used=1,
    )


def _composition_input(*, interpreted_intent=None):
    session_service = ConversationSessionService()
    session = session_service.create_session()
    user_turn = session_service.append_user_turn(session.session_id, "hello", "test")
    source_session, turns = session_service.context_source(session.session_id)
    context = ConversationContextProjector().project(source_session, turns)
    return session_service, ResponseCompositionInput(
        current_user_turn=user_turn,
        context=context,
        source="test",
        locale="en-US",
        session=source_session,
        interpreted_intent=interpreted_intent,
    )


def test_compatibility_composer_invokes_delegate_once_with_bounded_context():
    calls = []
    _, composition_input = _composition_input()

    def delegate(received_input):
        calls.append(received_input)
        return f"context turns: {received_input.context.included_turn_count}"

    result = CompatibilityResponseComposer(delegate).compose(composition_input)

    assert calls == [composition_input]
    assert result.response_type is AssistantResponseType.MESSAGE
    assert result.text == "context turns: 1"
    assert result.context_turn_count_used == 1
    assert result.composition_source == "compatibility_delegate"


def test_compatibility_composer_observably_uses_interpreted_intent():
    _, composition_input = _composition_input(interpreted_intent=_intent())

    result = CompatibilityResponseComposer(lambda _: "reply").compose(composition_input)

    assert result.text == "reply"
    assert result.composition_source == "compatibility_delegate:conversation"


def test_compatibility_composer_sanitizes_output_and_does_not_mutate_session():
    session_service, composition_input = _composition_input()
    before = session_service.get_snapshot(composition_input.current_user_turn.session_id)

    result = CompatibilityResponseComposer(
        lambda _: "token=sk-test-1234567890secret"
    ).compose(composition_input)

    after = session_service.get_snapshot(composition_input.current_user_turn.session_id)
    assert result.text == "[REDACTED]"
    assert before.turn_count == after.turn_count == 1


def test_composer_failure_is_not_swallowed_at_boundary():
    _, composition_input = _composition_input()

    def failing_delegate(_):
        raise RuntimeError("delegate failed")

    with pytest.raises(RuntimeError):
        CompatibilityResponseComposer(failing_delegate).compose(composition_input)


def test_response_composition_contract_has_no_metadata_escape_hatch():
    _, composition_input = _composition_input()
    result = CompatibilityResponseComposer(lambda _: "reply").compose(composition_input)

    payload = result.to_dict()

    assert payload == {
        "response_type": "message",
        "text": "reply",
        "context_turn_count_used": 1,
        "composition_source": "compatibility_delegate",
    }
    assert "metadata" not in payload
