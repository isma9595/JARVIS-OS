import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from cognition import (
    CONVERSATION_SESSION_SCHEMA_VERSION,
    MAX_PERSISTED_TURN_SUMMARY_LENGTH,
    ConversationPersistenceCorruptionError,
    ConversationPersistenceLoadError,
    ConversationRole,
    ConversationSessionStatus,
    ConversationTurn,
    LocalConversationSessionRepository,
    PersistedConversationSessionRecord,
    PersistedConversationTurnSummary,
    PersistedTurnContentClassification,
)


def _turn(sequence=1, text="hello", role=ConversationRole.USER):
    return ConversationTurn(
        turn_id=f"turn-{sequence}",
        session_id="cog-session-test",
        sequence=sequence,
        role=role,
        text=text,
        source="Test Source",
        created_at=f"2026-07-28T00:00:0{sequence}+00:00",
    )


def _record(*turns):
    return PersistedConversationSessionRecord.from_session(
        session_id="cog-session-test",
        status=ConversationSessionStatus.ACTIVE,
        created_at="2026-07-28T00:00:00+00:00",
        updated_at="2026-07-28T00:00:02+00:00",
        turns=tuple(turns),
    )


def test_persisted_record_serializes_deterministically_and_is_versioned():
    record = _record(_turn(), _turn(2, "hi", ConversationRole.ASSISTANT))

    first = record.to_json()
    second = record.to_json()
    payload = json.loads(first)

    assert first == second
    assert payload["schema_version"] == CONVERSATION_SESSION_SCHEMA_VERSION
    assert payload["turn_count"] == 2
    assert payload["last_turn_id"] == "turn-2"
    assert "metadata" not in payload
    assert "text" not in payload["turns"][0]
    assert payload["turns"][0]["summary_text"] == "hello"


def test_unsupported_schema_and_malformed_fields_are_rejected():
    record = _record(_turn()).to_dict()
    record["schema_version"] = 999

    with pytest.raises(ConversationPersistenceLoadError):
        PersistedConversationSessionRecord.from_dict(record)

    malformed = _record(_turn()).to_dict()
    malformed["turns"][0]["sequence"] = 3

    with pytest.raises(ConversationPersistenceCorruptionError):
        PersistedConversationSessionRecord.from_dict(malformed)

    unexpected = _record(_turn()).to_dict()
    unexpected["metadata"] = {"escape": "hatch"}

    with pytest.raises(ConversationPersistenceCorruptionError):
        PersistedConversationSessionRecord.from_dict(unexpected)

    overlong_summary = _record(_turn()).to_dict()
    overlong_summary["turns"][0]["summary_text"] = (
        "x" * (MAX_PERSISTED_TURN_SUMMARY_LENGTH + 1)
    )

    with pytest.raises(ConversationPersistenceCorruptionError):
        PersistedConversationSessionRecord.from_dict(overlong_summary)


def test_persisted_dtos_are_detached_and_immutable():
    record = _record(_turn())
    payload = record.to_dict()
    payload["turns"].append(record.turns[0].to_dict())

    assert record.turn_count == 1
    with pytest.raises(FrozenInstanceError):
        record.session_id = "changed"


def test_sensitive_turn_projection_is_bounded_redacted_and_deterministic():
    secret_turn = _turn(text="use api key=sk-test-1234567890secret now")
    long_turn = _turn(2, text="x" * (MAX_PERSISTED_TURN_SUMMARY_LENGTH + 50))

    secret_summary = PersistedConversationTurnSummary.from_turn(secret_turn)
    long_summary = PersistedConversationTurnSummary.from_turn(long_turn)

    assert secret_summary.summary_text == "[redacted sensitive content]"
    assert secret_summary.content_classification is (
        PersistedTurnContentClassification.REDACTED_SENSITIVE_CONTENT
    )
    assert "sk-test" not in secret_summary.to_dict()["summary_text"]
    assert len(long_summary.summary_text) <= MAX_PERSISTED_TURN_SUMMARY_LENGTH
    assert long_summary == PersistedConversationTurnSummary.from_turn(long_turn)


def test_local_repository_missing_storage_starts_clean_and_creates_parent(tmp_path):
    storage_dir = tmp_path / "nested" / "sessions"
    repository = LocalConversationSessionRepository(storage_dir)

    assert not storage_dir.exists()
    assert repository.load_records().loaded_count == 0
    assert not storage_dir.exists()

    repository.save_record(_record(_turn(text="hello unicode Привет")))

    stored_files = list(storage_dir.glob("*.json"))
    assert len(stored_files) == 1
    assert stored_files[0].read_text(encoding="utf-8")
    assert not list(storage_dir.glob("*.tmp"))


def test_default_storage_uses_versioned_local_app_data_layout(tmp_path, monkeypatch):
    local_app_data = tmp_path / "LocalAppData"
    monkeypatch.delenv("JARVIS_COGNITIVE_SESSION_DIR", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(local_app_data))

    repository = LocalConversationSessionRepository()

    assert repository.storage_dir == (
        local_app_data / "JARVIS-OS" / "data" / "v1" / "cognition" / "sessions"
    )
    assert not repository.storage_dir.exists()


def test_storage_override_is_exact_final_path(tmp_path, monkeypatch):
    override = tmp_path / "exact-session-store"
    monkeypatch.setenv("JARVIS_COGNITIVE_SESSION_DIR", str(override))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "ignored"))

    repository = LocalConversationSessionRepository()

    assert repository.storage_dir == override
    assert repository.storage_dir.name != "v1"
    assert not repository.storage_dir.exists()


def test_fallback_storage_path_is_independent_of_current_working_directory(
    tmp_path,
    monkeypatch,
):
    home = tmp_path / "profile"
    first_cwd = tmp_path / "first"
    second_cwd = tmp_path / "second"
    first_cwd.mkdir()
    second_cwd.mkdir()
    monkeypatch.delenv("JARVIS_COGNITIVE_SESSION_DIR", raising=False)
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))

    monkeypatch.chdir(first_cwd)
    first = LocalConversationSessionRepository().storage_dir
    monkeypatch.chdir(second_cwd)
    second = LocalConversationSessionRepository().storage_dir

    expected = home / ".jarvis-os" / "data" / "v1" / "cognition" / "sessions"
    assert first == second == expected
    assert not expected.exists()


def test_local_repository_save_load_round_trip_and_per_session_isolation(tmp_path):
    repository = LocalConversationSessionRepository(tmp_path)
    first = _record(_turn())
    second = PersistedConversationSessionRecord.from_session(
        session_id="cog-session-second",
        status=ConversationSessionStatus.CLOSED,
        created_at="2026-07-28T00:00:00+00:00",
        updated_at="2026-07-28T00:00:03+00:00",
        turns=(_turn(text="other").__class__(
            turn_id="second-turn",
            session_id="cog-session-second",
            sequence=1,
            role=ConversationRole.USER,
            text="other",
            source="test",
            created_at="2026-07-28T00:00:01+00:00",
        ),),
    )

    repository.save_record(first)
    repository.save_record(second)
    loaded = repository.load_records()

    assert loaded.loaded_count == 2
    assert {record.session_id for record in loaded.records} == {
        "cog-session-test",
        "cog-session-second",
    }
    assert loaded.rejected_count == 0


def test_local_repository_corrupt_and_unsupported_records_are_observable(tmp_path):
    repository = LocalConversationSessionRepository(tmp_path)
    repository.save_record(_record(_turn()))
    (tmp_path / "bad-json.json").write_text("{", encoding="utf-8")
    unsupported = _record(_turn()).to_dict()
    unsupported["session_id"] = "cog-session-unsupported"
    unsupported["schema_version"] = 999
    (tmp_path / "cog-session-unsupported.json").write_text(
        json.dumps(unsupported),
        encoding="utf-8",
    )

    loaded = repository.load_records()

    assert loaded.loaded_count == 1
    assert loaded.corrupt_record_ids == ("bad-json",)
    assert loaded.unsupported_schema_record_ids == ("cog-session-unsupported",)
    assert loaded.rejected_count == 2


def test_local_repository_delete_is_explicit_lifecycle_operation(tmp_path):
    repository = LocalConversationSessionRepository(tmp_path)
    repository.save_record(_record(_turn()))

    repository.delete_record("cog-session-test")

    assert repository.load_records().loaded_count == 0
