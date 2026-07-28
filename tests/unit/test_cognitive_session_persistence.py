from concurrent.futures import ThreadPoolExecutor

import pytest

from cognition import (
    ConversationPersistenceLoadResult,
    ConversationPersistenceWriteError,
    ConversationRole,
    ConversationSessionClosedError,
    ConversationSessionService,
    ConversationSessionStatus,
    LocalConversationSessionRepository,
)


class FailingRepository:
    def __init__(self):
        self.records = []

    def load_records(self):
        return ConversationPersistenceLoadResult()

    def save_record(self, record):
        self.records.append(record)
        raise ConversationPersistenceWriteError("write failed")

    def delete_record(self, session_id):
        raise ConversationPersistenceWriteError("delete failed")

    def close(self):
        return None


def test_in_memory_behavior_remains_supported_without_repository():
    service = ConversationSessionService()

    session = service.create_session()
    service.append_user_turn(session.session_id, "hello", "test")

    assert service.persistence_load_result.loaded_count == 0
    assert service.get_snapshot(session.session_id).turn_count == 1


def test_session_creation_turns_and_close_are_persisted(tmp_path):
    repository = LocalConversationSessionRepository(tmp_path)
    service = ConversationSessionService(repository=repository)

    session = service.create_session()
    user = service.append_user_turn(session.session_id, "hello", "test")
    assistant = service.append_assistant_turn(session.session_id, "hi", "assistant")
    closed = service.close_session(session.session_id)
    loaded = repository.load_records()

    assert closed.status is ConversationSessionStatus.CLOSED
    assert loaded.loaded_count == 1
    record = loaded.records[0]
    assert record.session_id == session.session_id
    assert record.status is ConversationSessionStatus.CLOSED
    assert record.turn_count == 2
    assert record.last_turn_id == assistant.turn_id
    assert [turn.turn_id for turn in record.turns] == [user.turn_id, assistant.turn_id]


def test_restart_restores_ids_status_ordering_and_next_sequence(tmp_path):
    first_service = ConversationSessionService(
        repository=LocalConversationSessionRepository(tmp_path)
    )
    session = first_service.create_session()
    first_service.append_user_turn(session.session_id, "first", "test")
    first_service.append_assistant_turn(session.session_id, "second", "assistant")

    restarted = ConversationSessionService(repository=LocalConversationSessionRepository(tmp_path))
    snapshot = restarted.get_snapshot(session.session_id)
    turns = restarted.turns_snapshot(session.session_id)
    next_turn = restarted.append_user_turn(session.session_id, "third", "test")

    assert restarted.persistence_load_result.loaded_count == 1
    assert snapshot.session_id == session.session_id
    assert snapshot.status is ConversationSessionStatus.ACTIVE
    assert snapshot.turn_count == 2
    assert [turn.sequence for turn in turns] == [1, 2]
    assert [turn.role for turn in turns] == [ConversationRole.USER, ConversationRole.ASSISTANT]
    assert next_turn.sequence == 3


def test_closed_session_remains_closed_after_restart(tmp_path):
    first_service = ConversationSessionService(
        repository=LocalConversationSessionRepository(tmp_path)
    )
    session = first_service.create_session()
    first_service.close_session(session.session_id)

    restarted = ConversationSessionService(repository=LocalConversationSessionRepository(tmp_path))

    assert restarted.get_snapshot(session.session_id).status is ConversationSessionStatus.CLOSED
    with pytest.raises(ConversationSessionClosedError):
        restarted.append_user_turn(session.session_id, "hello", "test")


def test_corrupt_record_does_not_contaminate_valid_recovered_session(tmp_path):
    repository = LocalConversationSessionRepository(tmp_path)
    service = ConversationSessionService(repository=repository)
    valid = service.create_session()
    service.append_user_turn(valid.session_id, "safe", "test")
    (tmp_path / "broken.json").write_text("{", encoding="utf-8")

    restarted = ConversationSessionService(repository=LocalConversationSessionRepository(tmp_path))

    assert restarted.get_snapshot(valid.session_id).turn_count == 1
    assert restarted.persistence_load_result.corrupt_record_ids == ("broken",)


def test_sensitive_raw_text_is_not_persisted_by_default(tmp_path):
    service = ConversationSessionService(repository=LocalConversationSessionRepository(tmp_path))
    session = service.create_session()

    service.append_user_turn(
        session.session_id,
        "please use token=sk-test-1234567890secret for this command",
        "test",
    )

    persisted_text = next(tmp_path.glob("*.json")).read_text(encoding="utf-8")
    assert "sk-test" not in persisted_text
    assert "please use token" not in persisted_text
    assert "[redacted sensitive content]" in persisted_text
    assert "execution" not in persisted_text.lower()
    assert "provider" not in persisted_text.lower()


def test_write_failure_does_not_publish_unstored_session_or_turn():
    create_service = ConversationSessionService(repository=FailingRepository())

    with pytest.raises(ConversationPersistenceWriteError):
        create_service.create_session()
    assert create_service._sessions == {}

    class FlipRepository(FailingRepository):
        def __init__(self):
            self.records = []
            self.fail = False

        def save_record(self, record):
            if self.fail:
                raise ConversationPersistenceWriteError("write failed")
            self.records.append(record)

    repository = FlipRepository()
    service = ConversationSessionService(repository=repository)
    session = service.create_session()
    repository.fail = True

    with pytest.raises(ConversationPersistenceWriteError):
        service.append_user_turn(session.session_id, "unstored", "test")

    assert service.get_snapshot(session.session_id).turn_count == 0


def test_loaded_turn_snapshots_are_detached_from_authoritative_state(tmp_path):
    service = ConversationSessionService(repository=LocalConversationSessionRepository(tmp_path))
    session = service.create_session()
    service.append_user_turn(session.session_id, "hello", "test")

    restarted = ConversationSessionService(repository=LocalConversationSessionRepository(tmp_path))
    turns = restarted.turns_snapshot(session.session_id)
    mutated = turns + turns

    assert len(mutated) == 2
    assert restarted.get_snapshot(session.session_id).turn_count == 1


def test_concurrent_persistent_mutations_preserve_order_and_storage(tmp_path):
    service = ConversationSessionService(repository=LocalConversationSessionRepository(tmp_path))
    session = service.create_session()

    with ThreadPoolExecutor(max_workers=8) as executor:
        tuple(
            executor.map(
                lambda index: service.append_user_turn(session.session_id, f"turn {index}", "test"),
                range(25),
            )
        )

    restarted = ConversationSessionService(repository=LocalConversationSessionRepository(tmp_path))
    turns = restarted.turns_snapshot(session.session_id)

    assert [turn.sequence for turn in turns] == list(range(1, 26))
    assert restarted.get_snapshot(session.session_id).turn_count == 25
