from threading import Event, current_thread

import pytest

from app.desktop_interaction_worker import (
    DesktopInteractionCompletionStatus,
    DesktopInteractionKind,
    DesktopInteractionLifecycle,
    DesktopInteractionWorker as _DesktopInteractionWorker,
)


TIMEOUT = 2.0


class _WorkerTestHarness:
    def __init__(self):
        self._workers = []
        self._release_events = []

    def create_worker(self):
        worker = _DesktopInteractionWorker()
        self._workers.append(worker)
        return worker

    def create_release_event(self):
        event = Event()
        self._release_events.append(event)
        return event

    def cleanup(self):
        failures = []
        for index, event in enumerate(self._release_events, start=1):
            try:
                event.set()
            except Exception as exc:
                failures.append(f"release event {index}: {type(exc).__name__}")

        for index, worker in enumerate(reversed(self._workers), start=1):
            try:
                worker.request_cancel()
            except Exception as exc:
                failures.append(f"worker {index} cancel: {type(exc).__name__}")
            try:
                worker.request_shutdown()
            except Exception as exc:
                failures.append(f"worker {index} shutdown: {type(exc).__name__}")

        for index, worker in enumerate(reversed(self._workers), start=1):
            try:
                joined = worker.join(TIMEOUT)
            except Exception as exc:
                failures.append(f"worker {index} join: {type(exc).__name__}")
                continue
            if not joined:
                failures.append(f"worker {index} remained alive after bounded join")
                continue
            snapshot = worker.snapshot()
            if snapshot.thread_alive:
                failures.append(f"worker {index} snapshot remained alive")
            if snapshot.lifecycle is not DesktopInteractionLifecycle.STOPPED:
                failures.append(f"worker {index} did not reach STOPPED")

        if failures:
            pytest.fail("; ".join(failures), pytrace=False)


@pytest.fixture
def worker_harness():
    harness = _WorkerTestHarness()
    try:
        yield harness
    finally:
        harness.cleanup()


@pytest.fixture
def worker(worker_harness):
    return worker_harness.create_worker()


def _finish(worker, interaction_id):
    assert worker.wait_for_completion(TIMEOUT)
    completion = worker.take_completion(interaction_id)
    assert completion is not None
    return completion


def _stop(worker):
    worker.request_shutdown()
    assert worker.join(TIMEOUT)
    assert worker.snapshot().lifecycle is DesktopInteractionLifecycle.STOPPED


def test_construction_is_lazy_and_snapshot_is_bounded(worker):
    snapshot = worker.snapshot()

    assert snapshot.lifecycle is DesktopInteractionLifecycle.NEW
    assert snapshot.thread_started is False
    assert snapshot.thread_alive is False
    assert "secret-user-command" not in repr(snapshot)
    _stop(worker)


def test_first_submission_uses_one_non_daemon_background_thread_and_stable_id(worker):
    submitting_thread = current_thread().ident
    operation_thread = []

    submission = worker.submit(
        DesktopInteractionKind.TYPED_TURN,
        lambda _token: operation_thread.append(current_thread().ident) or "ok",
    )
    completion = _finish(worker, submission.interaction_id)
    snapshot = worker.snapshot()

    assert submission.accepted is True
    assert submission.interaction_id.startswith("desktop-interaction-")
    assert completion.interaction_id == submission.interaction_id
    assert completion.status is DesktopInteractionCompletionStatus.COMPLETED
    assert operation_thread == [snapshot.worker_thread_id]
    assert operation_thread[0] != submitting_thread
    assert snapshot.thread_started is True
    assert snapshot.thread_daemon is False
    _stop(worker)


def test_busy_rejects_duplicate_without_backlog_and_completion_is_consumed_once(
    worker, worker_harness
):
    entered = Event()
    release = worker_harness.create_release_event()
    calls = []

    first = worker.submit(
        DesktopInteractionKind.TYPED_TURN,
        lambda _token: entered.set() or release.wait(TIMEOUT) or calls.append("first"),
    )
    assert entered.wait(TIMEOUT)
    duplicate = worker.submit(
        DesktopInteractionKind.VOICE_REQUEST,
        lambda _token: calls.append("duplicate"),
    )
    release.set()
    completion = _finish(worker, first.interaction_id)

    assert duplicate.accepted is False
    assert duplicate.interaction_id is None
    assert calls == []
    assert completion.status is DesktopInteractionCompletionStatus.COMPLETED
    assert worker.take_completion(first.interaction_id) is None
    _stop(worker)


def test_worker_is_reused_only_after_completion_is_consumed(worker):
    first = worker.submit(DesktopInteractionKind.TYPED_TURN, lambda _token: "one")
    assert worker.wait_for_completion(TIMEOUT)
    rejected = worker.submit(DesktopInteractionKind.VOICE_REQUEST, lambda _token: "no")
    first_completion = worker.take_completion(first.interaction_id)
    thread_id = worker.snapshot().worker_thread_id
    second = worker.submit(DesktopInteractionKind.VOICE_REQUEST, lambda _token: "two")
    second_completion = _finish(worker, second.interaction_id)

    assert rejected.accepted is False
    assert first_completion.result == "one"
    assert second_completion.result == "two"
    assert worker.snapshot().worker_thread_id == thread_id
    _stop(worker)


def test_early_cancellation_does_not_start_callable(worker, worker_harness):
    gate_entered = Event()
    gate_release = worker_harness.create_release_event()
    calls = []
    worker._operation_start_gate = lambda: gate_entered.set() or gate_release.wait(TIMEOUT)

    submission = worker.submit(
        DesktopInteractionKind.TYPED_TURN,
        lambda _token: calls.append("called"),
    )
    assert gate_entered.wait(TIMEOUT)
    cancelled = worker.request_cancel(submission.interaction_id)
    repeated = worker.request_cancel(submission.interaction_id)
    gate_release.set()
    completion = _finish(worker, submission.interaction_id)

    assert cancelled.accepted is True
    assert repeated.accepted is True
    assert calls == []
    assert completion.status is DesktopInteractionCompletionStatus.CANCELLED
    _stop(worker)


def test_token_aware_operation_can_confirm_cooperative_cancellation(worker):
    entered = Event()

    def operation(token):
        entered.set()
        assert token.wait(TIMEOUT)
        token.raise_if_cancelled()

    submission = worker.submit(DesktopInteractionKind.WORKFLOW_RESUME, operation)
    assert entered.wait(TIMEOUT)
    result = worker.request_cancel(submission.interaction_id)
    completion = _finish(worker, submission.interaction_id)

    assert result.accepted is True
    assert completion.status is DesktopInteractionCompletionStatus.CANCELLED
    assert completion.cancellation_requested is True
    _stop(worker)


def test_late_cancel_does_not_relabel_opaque_normal_result(worker, worker_harness):
    entered = Event()
    release = worker_harness.create_release_event()

    def opaque(_token):
        entered.set()
        release.wait(TIMEOUT)
        return "side effect completed"

    submission = worker.submit(DesktopInteractionKind.TYPED_TURN, opaque)
    assert entered.wait(TIMEOUT)
    worker.request_cancel(submission.interaction_id)
    release.set()
    completion = _finish(worker, submission.interaction_id)

    assert completion.status is DesktopInteractionCompletionStatus.COMPLETED
    assert completion.cancellation_requested is True
    assert completion.result == "side effect completed"
    _stop(worker)


def test_cancel_after_completion_publication_is_rejected_and_result_stays_truthful(
    worker, worker_harness
):
    entered = Event()
    release = worker_harness.create_release_event()
    captured_tokens = []

    def operation(token):
        captured_tokens.append(token)
        entered.set()
        assert release.wait(TIMEOUT)
        return "completed before cancellation request"

    submission = worker.submit(DesktopInteractionKind.TYPED_TURN, operation)
    assert entered.wait(TIMEOUT)
    release.set()
    assert worker.wait_for_completion(TIMEOUT)

    published = worker.snapshot()
    assert len(captured_tokens) == 1
    assert captured_tokens[0].cancel_requested is False
    assert published.completion_pending is True
    assert published.cancellation_requested is False

    cancellation = worker.request_cancel(submission.interaction_id)
    after_cancellation = worker.snapshot()

    assert cancellation.accepted is False
    assert cancellation.interaction_id == submission.interaction_id
    assert cancellation.rejection_reason == "interaction_completed"
    assert cancellation.cancellation_requested is False
    assert captured_tokens[0].cancel_requested is False
    assert after_cancellation.completion_pending is True
    assert after_cancellation.cancellation_requested is False

    completion = worker.take_completion(submission.interaction_id)
    assert completion is not None
    assert completion.status is DesktopInteractionCompletionStatus.COMPLETED
    assert completion.result == "completed before cancellation request"
    assert completion.cancellation_requested is False
    assert worker.take_completion(submission.interaction_id) is None
    _stop(worker)


def test_failure_is_safe_and_worker_survives(worker):

    def fail(_token):
        raise RuntimeError("C:\\private\\secret.txt token=very-secret")

    first = worker.submit(DesktopInteractionKind.TYPED_TURN, fail)
    completion = _finish(worker, first.interaction_id)

    assert completion.status is DesktopInteractionCompletionStatus.FAILED
    assert completion.error_code == "RuntimeError"
    assert "secret" not in repr(completion).lower()
    second = worker.submit(DesktopInteractionKind.VOICE_REQUEST, lambda _token: "ok")
    assert _finish(worker, second.interaction_id).result == "ok"
    _stop(worker)


def test_idle_and_stale_cancellation_are_safe_noops(worker):
    assert worker.request_cancel().accepted is False
    assert worker.request_cancel("desktop-interaction-stale").accepted is False
    _stop(worker)


def test_shutdown_idle_is_idempotent_and_rejects_submission(worker):
    worker.request_shutdown()
    worker.request_shutdown()

    assert worker.join(TIMEOUT)
    assert worker.submit(DesktopInteractionKind.TYPED_TURN, lambda _token: None).accepted is False
    assert worker.snapshot().lifecycle is DesktopInteractionLifecycle.STOPPED


def test_shutdown_busy_requests_cancel_but_never_forces_noncooperative_callable(
    worker, worker_harness
):
    entered = Event()
    release = worker_harness.create_release_event()

    def noncooperative(_token):
        entered.set()
        release.wait(TIMEOUT)
        return "finished"

    submission = worker.submit(DesktopInteractionKind.TYPED_TURN, noncooperative)
    assert entered.wait(TIMEOUT)
    worker.request_shutdown()

    assert worker.snapshot().lifecycle is DesktopInteractionLifecycle.SHUTTING_DOWN
    assert worker.join(0.01) is False
    assert worker.submit(DesktopInteractionKind.VOICE_REQUEST, lambda _token: None).accepted is False
    release.set()
    completion = _finish(worker, submission.interaction_id)
    assert completion.status is DesktopInteractionCompletionStatus.COMPLETED
    assert worker.join(TIMEOUT)
    assert worker.snapshot().thread_alive is False


def test_shutdown_stops_with_pending_completion_and_preserves_exactly_once_delivery(worker):
    submission = worker.submit(
        DesktopInteractionKind.TYPED_TURN,
        lambda _token: "completed before shutdown",
    )
    assert worker.wait_for_completion(TIMEOUT)

    worker.request_shutdown()
    assert worker.join(TIMEOUT) is True

    snapshot = worker.snapshot()
    assert snapshot.lifecycle is DesktopInteractionLifecycle.STOPPED
    assert snapshot.completion_pending is True
    completion = worker.take_completion(submission.interaction_id)
    assert completion is not None
    assert completion.status is DesktopInteractionCompletionStatus.COMPLETED
    assert completion.result == "completed before shutdown"
    assert worker.take_completion(submission.interaction_id) is None
    assert worker.snapshot().lifecycle is DesktopInteractionLifecycle.STOPPED


def test_shutdown_during_opaque_operation_stops_after_safe_normal_return(
    worker, worker_harness
):
    entered = Event()
    release = worker_harness.create_release_event()

    def opaque(_token):
        entered.set()
        release.wait(TIMEOUT)
        return "opaque result"

    submission = worker.submit(DesktopInteractionKind.TYPED_TURN, opaque)
    assert entered.wait(TIMEOUT)
    worker.request_cancel(submission.interaction_id)
    worker.request_shutdown()
    release.set()

    assert worker.join(TIMEOUT) is True
    completion = worker.take_completion(submission.interaction_id)
    assert completion is not None
    assert completion.status is DesktopInteractionCompletionStatus.COMPLETED
    assert completion.cancellation_requested is True
    assert completion.result == "opaque result"
    assert worker.take_completion(submission.interaction_id) is None
    assert worker.snapshot().lifecycle is DesktopInteractionLifecycle.STOPPED
