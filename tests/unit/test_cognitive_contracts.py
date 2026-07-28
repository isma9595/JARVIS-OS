from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError

import pytest

from cognition import (
    AssistantResponseType,
    ConversationRole,
    ConversationSessionClosedError,
    ConversationSessionNotFoundError,
    ConversationSessionService,
    ConversationSessionStatus,
    ConversationTurnInput,
    InvalidConversationTurnError,
)


def test_conversation_turn_input_is_immutable_json_safe_and_validates_text():
    turn_input = ConversationTurnInput(
        text="hello api key=sk-test-1234567890secret",
        source="test",
    )

    assert turn_input.text == "hello [REDACTED]"
    assert turn_input.to_dict() == {
        "text": "hello [REDACTED]",
        "source": "test",
        "session_id": None,
        "locale": None,
    }
    with pytest.raises(FrozenInstanceError):
        turn_input.text = "changed"
    with pytest.raises(InvalidConversationTurnError):
        ConversationTurnInput(text=" ", source="test")


def test_session_creation_snapshot_and_unique_ids():
    service = ConversationSessionService()

    first = service.create_session()
    second = service.create_session()

    assert first.session_id.startswith("cog-session-")
    assert second.session_id.startswith("cog-session-")
    assert first.session_id != second.session_id
    assert first.status is ConversationSessionStatus.ACTIVE
    assert first.turn_count == 0
    assert first.last_turn_id is None
    assert first.to_dict()["status"] == "active"


def test_session_turns_are_ordered_and_turn_count_is_deterministic():
    service = ConversationSessionService()
    session = service.create_session()

    user = service.append_user_turn(session.session_id, "hello", "test")
    assistant = service.append_assistant_turn(session.session_id, "hi", "assistant")
    snapshot = service.get_snapshot(session.session_id)
    turns = service.turns_snapshot(session.session_id)

    assert [turn.sequence for turn in turns] == [1, 2]
    assert [turn.role for turn in turns] == [ConversationRole.USER, ConversationRole.ASSISTANT]
    assert snapshot.turn_count == 2
    assert snapshot.last_turn_id == assistant.turn_id
    assert user.turn_id != assistant.turn_id


def test_session_snapshots_and_turns_are_detached_from_internal_state():
    service = ConversationSessionService()
    session = service.create_session()
    service.append_user_turn(session.session_id, "hello", "test")

    turns = service.turns_snapshot(session.session_id)
    mutated_copy = turns + turns

    assert len(mutated_copy) == 2
    assert service.get_snapshot(session.session_id).turn_count == 1


def test_unknown_session_and_closed_session_fail_safely():
    service = ConversationSessionService()

    with pytest.raises(ConversationSessionNotFoundError):
        service.get_snapshot("missing")

    session = service.create_session()
    closed = service.close_session(session.session_id)

    assert closed.status is ConversationSessionStatus.CLOSED
    with pytest.raises(ConversationSessionClosedError):
        service.append_user_turn(session.session_id, "hello", "test")


def test_concurrent_session_creation_has_unique_stable_ids():
    service = ConversationSessionService()

    with ThreadPoolExecutor(max_workers=8) as executor:
        sessions = tuple(executor.map(lambda _: service.create_session(), range(40)))

    session_ids = {session.session_id for session in sessions}
    assert len(session_ids) == 40
    assert all(session.turn_count == 0 for session in sessions)


def test_concurrent_turn_append_preserves_per_session_sequence():
    service = ConversationSessionService()
    session = service.create_session()

    with ThreadPoolExecutor(max_workers=8) as executor:
        tuple(
            executor.map(
                lambda index: service.append_user_turn(
                    session.session_id,
                    f"turn {index}",
                    "test",
                ),
                range(50),
            )
        )

    turns = service.turns_snapshot(session.session_id)
    assert [turn.sequence for turn in turns] == list(range(1, 51))
    assert service.get_snapshot(session.session_id).turn_count == 50


def test_minimal_response_type_does_not_speculate_about_future_states():
    assert {item.value for item in AssistantResponseType} == {"message", "error"}
