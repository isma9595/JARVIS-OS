from core.execution_coordinator import ExecutionCoordinator
from core.execution_journal import ExecutionStatus


def test_same_key_and_fingerprint_returns_existing_operation_and_marks_duplicate():
    coordinator = ExecutionCoordinator()
    fingerprint = coordinator.create_request_fingerprint(
        source="test",
        text="статус системы",
        command_id="system.status",
    )

    first = coordinator.register(
        source="test",
        idempotency_key="same-key",
        request_fingerprint=fingerprint,
        command_id="system.status",
    )
    duplicate = coordinator.register(
        source="test",
        idempotency_key="same-key",
        request_fingerprint=fingerprint,
        command_id="system.status",
    )

    assert duplicate.duplicate is True
    assert duplicate.operation.operation_id == first.operation.operation_id
    assert duplicate.operation.duplicate_suppressed is True


def test_same_key_different_fingerprint_is_denied_conflict():
    coordinator = ExecutionCoordinator()
    first_fp = coordinator.create_request_fingerprint(source="test", text="one")
    second_fp = coordinator.create_request_fingerprint(source="test", text="two")

    coordinator.register(
        source="test",
        idempotency_key="same-key",
        request_fingerprint=first_fp,
    )
    conflict = coordinator.register(
        source="test",
        idempotency_key="same-key",
        request_fingerprint=second_fp,
    )

    assert conflict.conflict is True
    assert conflict.operation.status == ExecutionStatus.DENIED
    assert conflict.operation.safe_error_code == "idempotency_conflict"

    retry_original = coordinator.register(
        source="test",
        idempotency_key="same-key",
        request_fingerprint=first_fp,
    )

    assert retry_original.duplicate is True
    assert retry_original.operation.safe_error_code is None


def test_new_key_allows_new_intentional_operation():
    coordinator = ExecutionCoordinator()
    fingerprint = coordinator.create_request_fingerprint(source="test", text="same")

    first = coordinator.register(
        source="test",
        idempotency_key="key-1",
        request_fingerprint=fingerprint,
    )
    second = coordinator.register(
        source="test",
        idempotency_key="key-2",
        request_fingerprint=fingerprint,
    )

    assert first.operation.operation_id != second.operation.operation_id
    assert second.duplicate is False
    assert second.conflict is False


def test_cancellation_is_single_operation_scoped_and_terminal_noop():
    coordinator = ExecutionCoordinator()
    first = coordinator.register(
        source="test",
        idempotency_key="key-1",
        request_fingerprint="fp-1",
    )
    second = coordinator.register(
        source="test",
        idempotency_key="key-2",
        request_fingerprint="fp-2",
    )

    cancelled = coordinator.cancel(first.operation.operation_id)

    assert cancelled.status == ExecutionStatus.CANCELLED
    assert first.token.cancelled is True
    assert second.token.cancelled is False

    terminal = coordinator.cancel(first.operation.operation_id)

    assert terminal.status == ExecutionStatus.CANCELLED
