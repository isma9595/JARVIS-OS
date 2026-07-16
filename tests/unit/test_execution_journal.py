import json
from dataclasses import FrozenInstanceError

from core.execution_journal import (
    ExecutionJournal,
    ExecutionOperation,
    ExecutionStatus,
    safe_journal_metadata,
    utc_now_iso,
)


def _operation(operation_id, key="key", status=ExecutionStatus.CREATED, metadata=None):
    now = utc_now_iso()
    return ExecutionOperation(
        operation_id=operation_id,
        idempotency_key=key,
        source="test",
        request_fingerprint=f"fp:{operation_id}",
        status=status,
        created_at=now,
        updated_at=now,
        metadata=safe_journal_metadata(metadata),
    )


def test_operation_ids_are_unique_and_ordering_is_deterministic():
    journal = ExecutionJournal(max_size=5)

    first = journal.add(_operation("op-1"))
    second = journal.add(_operation("op-2"))

    assert first.operation_id != second.operation_id
    assert [item.operation_id for item in journal.recent()] == ["op-1", "op-2"]


def test_journal_is_bounded():
    journal = ExecutionJournal(max_size=2)

    journal.add(_operation("op-1"))
    journal.add(_operation("op-2"))
    journal.add(_operation("op-3"))

    assert [item.operation_id for item in journal.recent()] == ["op-2", "op-3"]
    assert journal.get("op-1") is None


def test_snapshots_are_immutable_and_safely_copied():
    journal = ExecutionJournal()
    journal.add(_operation("op-1", metadata={"token": "sk-test-1234567890secret"}))

    snapshot = journal.get("op-1")

    try:
        snapshot.status = ExecutionStatus.SUCCEEDED
        mutated = True
    except FrozenInstanceError:
        mutated = False
    assert mutated is False
    assert snapshot.metadata["token"] == "[REDACTED]"
    assert journal.get("op-1").status == ExecutionStatus.CREATED


def test_cyrillic_serialization_and_redaction_rules():
    journal = ExecutionJournal()
    journal.add(
        _operation(
            "op-1",
            metadata={
                "summary": "статус системы",
                "api_key": "sk-test-1234567890secret",
                "raw_audio": b"audio",
                "provider_response": "full provider response",
                "document_contents": "full document",
            },
        )
    )

    data = journal.recent_dicts()[0]
    encoded = json.dumps(data, ensure_ascii=False)

    assert "статус системы" in encoded
    assert "sk-test-1234567890secret" not in encoded
    assert data["metadata"]["api_key"] == "[REDACTED]"
    assert data["metadata"]["raw_audio"] == "[REDACTED]"
    assert data["metadata"]["provider_response"] == "[REDACTED]"
    assert data["metadata"]["document_contents"] == "[REDACTED]"
