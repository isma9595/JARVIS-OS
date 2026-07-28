import pytest

from cognition import (
    AssistantResponseType,
    CognitiveInteractionService,
    ConversationRole,
    ConversationSessionNotFoundError,
    ConversationSessionService,
    ConversationTurnInput,
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


def test_interaction_service_keeps_no_duplicate_session_dictionary():
    session_service = ConversationSessionService()
    service = CognitiveInteractionService(session_service, lambda *_: "reply")

    assert service.session_service is session_service
    assert "_sessions" not in service.__dict__
