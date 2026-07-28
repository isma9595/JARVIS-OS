from dataclasses import FrozenInstanceError

from app.activity import ApplicationActivityTracker
from app.app_contracts import ApplicationActivityState
from core.execution_journal import ExecutionOperation, ExecutionStatus, utc_now_iso


def operation(
    operation_id,
    *,
    status=ExecutionStatus.RUNNING,
    command_id="app.status",
    metadata=None,
    error=None,
    summary=None,
    cancellable=True,
):
    now = utc_now_iso()
    return ExecutionOperation(
        operation_id=operation_id,
        idempotency_key=f"idem-{operation_id}",
        source="desktop_ui",
        request_fingerprint=f"fingerprint-{operation_id}",
        status=status,
        created_at=now,
        updated_at=now,
        command_id=command_id,
        metadata=metadata or {},
        cancellable=cancellable,
        safe_error_code=error,
        safe_result_summary=summary,
    )


def test_terminal_state_cannot_return_to_active():
    tracker = ApplicationActivityTracker()
    tracker.record_operation(operation("op-a", status=ExecutionStatus.SUCCEEDED))

    tracker.record_operation(operation("op-a", status=ExecutionStatus.RUNNING))
    snapshot = tracker.snapshot_from_operations(())

    assert snapshot.current is None
    assert snapshot.is_busy is False
    assert len(snapshot.recent) == 1
    assert snapshot.recent[0].state == ApplicationActivityState.SUCCEEDED


def test_stale_completion_does_not_replace_newer_current_activity():
    tracker = ApplicationActivityTracker()
    tracker.record_operation(operation("op-a", status=ExecutionStatus.RUNNING))
    tracker.record_operation(operation("op-b", status=ExecutionStatus.RUNNING))

    tracker.record_operation(operation("op-a", status=ExecutionStatus.SUCCEEDED))
    snapshot = tracker.snapshot_from_operations(())

    assert snapshot.current is not None
    assert snapshot.current.activity_id == "op-b"
    assert snapshot.current.state == ApplicationActivityState.RUNNING
    assert [activity.activity_id for activity in snapshot.recent] == ["op-a"]


def test_launch_failure_clears_busy_state_and_sanitizes_error():
    tracker = ApplicationActivityTracker()
    tracker.record_operation(operation("op-a", status=ExecutionStatus.CREATED))

    tracker.record_operation(
        operation(
            "op-a",
            status=ExecutionStatus.FAILED,
            error="Traceback RuntimeError C:/Users/User/raw.log sk-test-1234567890secret",
        )
    )
    snapshot = tracker.snapshot_from_operations(())
    text = snapshot.safe_text_ru()

    assert snapshot.current is None
    assert snapshot.is_busy is False
    assert snapshot.recent[0].state == ApplicationActivityState.FAILED
    assert "Traceback" not in text
    assert "RuntimeError" not in text
    assert "C:/Users/User" not in text
    assert "sk-test" not in text


def test_duplicate_terminal_notification_is_idempotent():
    tracker = ApplicationActivityTracker()
    first = operation("op-a", status=ExecutionStatus.SUCCEEDED, summary="done")
    second = operation("op-a", status=ExecutionStatus.FAILED, error="late failure")

    tracker.record_operation(first)
    tracker.record_operation(first)
    tracker.record_operation(second)
    snapshot = tracker.snapshot_from_operations(())

    assert len(snapshot.recent) == 1
    assert snapshot.recent[0].state == ApplicationActivityState.SUCCEEDED
    assert snapshot.current is None


def test_cancellation_completion_race_produces_one_terminal_state():
    cancellation_wins = ApplicationActivityTracker()
    cancellation_wins.record_operation(
        operation(
            "op-a",
            status=ExecutionStatus.RUNNING,
            metadata={"workflow_cancellation_requested": "true"},
        )
    )
    cancellation_wins.record_operation(operation("op-a", status=ExecutionStatus.CANCELLED))
    cancellation_wins.record_operation(operation("op-a", status=ExecutionStatus.SUCCEEDED))

    completion_wins = ApplicationActivityTracker()
    completion_wins.record_operation(operation("op-b", status=ExecutionStatus.RUNNING))
    completion_wins.record_operation(operation("op-b", status=ExecutionStatus.SUCCEEDED))
    completion_wins.record_operation(operation("op-b", status=ExecutionStatus.CANCELLED))

    cancelled = cancellation_wins.snapshot_from_operations(()).recent[0]
    completed = completion_wins.snapshot_from_operations(()).recent[0]

    assert cancelled.state == ApplicationActivityState.CANCELLED
    assert cancelled.cancellation_requested is False
    assert completed.state == ApplicationActivityState.SUCCEEDED


def test_snapshot_detachment_and_immutability():
    tracker = ApplicationActivityTracker()
    tracker.record_operation(operation("op-a", status=ExecutionStatus.RUNNING))
    snapshot = tracker.snapshot_from_operations(())
    current = snapshot.current

    tracker.record_operation(operation("op-a", status=ExecutionStatus.SUCCEEDED))
    refreshed = tracker.snapshot_from_operations(())

    assert current is not None
    assert current.state == ApplicationActivityState.RUNNING
    assert refreshed.current is None
    assert refreshed.recent[0].state == ApplicationActivityState.SUCCEEDED
    try:
        snapshot.recent.append("new")
    except AttributeError:
        pass
    else:
        raise AssertionError("recent collection must be immutable")
    try:
        current.title = "changed"
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("activity DTO must be frozen")


def test_unknown_malformed_state_fails_safely():
    tracker = ApplicationActivityTracker()
    tracker.record_operation(
        operation(
            "op-a",
            status="Traceback RuntimeError C:/Users/User/raw.log sk-test-1234567890secret",
            command_id="app.status",
            error="Traceback RuntimeError C:/Users/User/raw.log sk-test-1234567890secret",
        )
    )

    snapshot = tracker.snapshot_from_operations(())
    text = snapshot.safe_text_ru()

    assert snapshot.current is None
    assert snapshot.recent[0].state == ApplicationActivityState.UNKNOWN
    assert snapshot.status_available is True
    assert "Traceback" not in text
    assert "C:/Users/User" not in text
    assert "sk-test" not in text


def test_recent_outcomes_are_bounded_newest_first():
    tracker = ApplicationActivityTracker(recent_limit=3)
    for index in range(5):
        tracker.record_operation(
            operation(f"op-{index}", status=ExecutionStatus.SUCCEEDED)
        )

    snapshot = tracker.snapshot_from_operations(())

    assert [activity.activity_id for activity in snapshot.recent] == [
        "op-4",
        "op-3",
        "op-2",
    ]
    assert snapshot.current is None
