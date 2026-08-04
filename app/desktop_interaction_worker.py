"""Serialized Desktop interaction lifecycle without UI or domain ownership."""

from dataclasses import dataclass, field
from enum import Enum
from threading import Condition, Event, Thread
from typing import Callable
from uuid import uuid4


class DesktopInteractionLifecycle(str, Enum):
    NEW = "new"
    IDLE = "idle"
    BUSY = "busy"
    SHUTTING_DOWN = "shutting_down"
    STOPPED = "stopped"


class DesktopInteractionKind(str, Enum):
    TYPED_TURN = "typed_turn"
    VOICE_REQUEST = "voice_request"
    WORKFLOW_RESUME = "workflow_resume"


class DesktopInteractionCompletionStatus(str, Enum):
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class DesktopInteractionCancelled(Exception):
    """Explicit acknowledgement that cooperative cancellation was observed."""


class DesktopInteractionCancellationToken:
    """A bounded cooperative cancellation signal passed to an operation."""

    def __init__(self) -> None:
        self._event = Event()

    @property
    def cancel_requested(self) -> bool:
        return self._event.is_set()

    @property
    def cancelled(self) -> bool:
        return self.cancel_requested

    def wait(self, timeout: float | None = None) -> bool:
        return self._event.wait(timeout)

    def raise_if_cancelled(self) -> None:
        if self.cancel_requested:
            raise DesktopInteractionCancelled()

    def _request_cancel(self) -> None:
        self._event.set()


@dataclass(frozen=True)
class DesktopInteractionSnapshot:
    lifecycle: DesktopInteractionLifecycle
    active_interaction_id: str | None
    active_kind: DesktopInteractionKind | None
    cancellation_requested: bool
    thread_started: bool
    thread_alive: bool
    thread_daemon: bool | None
    worker_thread_id: int | None
    completion_pending: bool


@dataclass(frozen=True)
class DesktopInteractionSubmission:
    accepted: bool
    interaction_id: str | None
    kind: DesktopInteractionKind | None
    rejection_reason: str | None = None


@dataclass(frozen=True)
class DesktopInteractionCancellationResult:
    accepted: bool
    interaction_id: str | None
    cancellation_requested: bool
    rejection_reason: str | None = None


@dataclass(frozen=True)
class DesktopInteractionCompletion:
    interaction_id: str
    kind: DesktopInteractionKind
    status: DesktopInteractionCompletionStatus
    cancellation_requested: bool
    result: object = field(default=None, repr=False, compare=False)
    exception: BaseException | None = field(default=None, repr=False, compare=False)
    error_code: str | None = None


Operation = Callable[[DesktopInteractionCancellationToken], object]


class DesktopInteractionWorker:
    """Own one reusable non-daemon thread and one bounded interaction slot."""

    THREAD_NAME = "jarvis-desktop-interaction-worker"

    def __init__(self) -> None:
        self._condition = Condition()
        self._lifecycle = DesktopInteractionLifecycle.NEW
        self._thread: Thread | None = None
        self._work: tuple[str, DesktopInteractionKind, Operation, DesktopInteractionCancellationToken] | None = None
        self._completion: DesktopInteractionCompletion | None = None
        self._active_interaction_id: str | None = None
        self._active_kind: DesktopInteractionKind | None = None
        self._active_token: DesktopInteractionCancellationToken | None = None
        self._shutdown_requested = False
        self._operation_start_gate: Callable[[], object] = lambda: None

    def snapshot(self) -> DesktopInteractionSnapshot:
        with self._condition:
            thread = self._thread
            token = self._active_token
            completion = self._completion
            return DesktopInteractionSnapshot(
                lifecycle=self._lifecycle,
                active_interaction_id=self._active_interaction_id,
                active_kind=self._active_kind,
                cancellation_requested=(
                    completion.cancellation_requested
                    if completion is not None
                    else bool(token and token.cancel_requested)
                ),
                thread_started=thread is not None,
                thread_alive=bool(thread and thread.is_alive()),
                thread_daemon=thread.daemon if thread is not None else None,
                worker_thread_id=thread.ident if thread is not None else None,
                completion_pending=self._completion is not None,
            )

    def submit(
        self,
        kind: DesktopInteractionKind | str,
        operation: Operation,
    ) -> DesktopInteractionSubmission:
        operation_kind = DesktopInteractionKind(kind)
        with self._condition:
            if self._shutdown_requested or self._lifecycle in {
                DesktopInteractionLifecycle.SHUTTING_DOWN,
                DesktopInteractionLifecycle.STOPPED,
            }:
                return DesktopInteractionSubmission(
                    False, None, operation_kind, "worker_shutting_down"
                )
            if self._active_interaction_id is not None or self._completion is not None:
                return DesktopInteractionSubmission(False, None, operation_kind, "worker_busy")

            interaction_id = f"desktop-interaction-{uuid4()}"
            token = DesktopInteractionCancellationToken()
            self._active_interaction_id = interaction_id
            self._active_kind = operation_kind
            self._active_token = token
            self._work = (interaction_id, operation_kind, operation, token)
            self._lifecycle = DesktopInteractionLifecycle.BUSY
            if self._thread is None:
                self._thread = Thread(
                    target=self._run,
                    name=self.THREAD_NAME,
                    daemon=False,
                )
                self._thread.start()
            self._condition.notify_all()
            return DesktopInteractionSubmission(True, interaction_id, operation_kind)

    def request_cancel(
        self, interaction_id: str | None = None
    ) -> DesktopInteractionCancellationResult:
        with self._condition:
            active_id = self._active_interaction_id
            token = self._active_token
            if active_id is None or token is None:
                return DesktopInteractionCancellationResult(
                    False, interaction_id, False, "worker_idle"
                )
            if interaction_id is not None and interaction_id != active_id:
                return DesktopInteractionCancellationResult(
                    False, interaction_id, token.cancel_requested, "stale_interaction"
                )
            completion = self._completion
            if completion is not None:
                return DesktopInteractionCancellationResult(
                    False,
                    active_id,
                    completion.cancellation_requested,
                    "interaction_completed",
                )
            token._request_cancel()
            self._condition.notify_all()
            return DesktopInteractionCancellationResult(True, active_id, True)

    def wait_for_completion(self, timeout: float | None = None) -> bool:
        with self._condition:
            return self._condition.wait_for(lambda: self._completion is not None, timeout)

    def take_completion(
        self, interaction_id: str | None = None
    ) -> DesktopInteractionCompletion | None:
        with self._condition:
            completion = self._completion
            if completion is None:
                return None
            if interaction_id is not None and completion.interaction_id != interaction_id:
                return None
            self._completion = None
            self._active_interaction_id = None
            self._active_kind = None
            self._active_token = None
            if self._lifecycle is not DesktopInteractionLifecycle.STOPPED:
                self._lifecycle = (
                    DesktopInteractionLifecycle.SHUTTING_DOWN
                    if self._shutdown_requested
                    else DesktopInteractionLifecycle.IDLE
                )
            self._condition.notify_all()
            return completion

    def request_shutdown(self) -> DesktopInteractionSnapshot:
        with self._condition:
            self._shutdown_requested = True
            if self._active_token is not None and self._completion is None:
                self._active_token._request_cancel()
            if self._thread is None:
                self._lifecycle = DesktopInteractionLifecycle.STOPPED
            elif self._lifecycle is not DesktopInteractionLifecycle.STOPPED:
                self._lifecycle = DesktopInteractionLifecycle.SHUTTING_DOWN
            self._condition.notify_all()
        return self.snapshot()

    def join(self, timeout: float | None = None) -> bool:
        with self._condition:
            thread = self._thread
        if thread is None:
            return True
        thread.join(timeout)
        return not thread.is_alive()

    def _run(self) -> None:
        while True:
            with self._condition:
                self._condition.wait_for(
                    lambda: self._work is not None
                    or self._shutdown_requested
                )
                if self._work is None:
                    self._lifecycle = DesktopInteractionLifecycle.STOPPED
                    self._condition.notify_all()
                    return
                interaction_id, kind, operation, token = self._work
                self._work = None

            self._operation_start_gate()
            try:
                token.raise_if_cancelled()
                result = operation(token)
            except DesktopInteractionCancelled:
                status = DesktopInteractionCompletionStatus.CANCELLED
                result = None
                exception = None
                error_code = None
            except BaseException as exc:
                status = DesktopInteractionCompletionStatus.FAILED
                result = None
                exception = exc
                error_code = type(exc).__name__
            else:
                status = DesktopInteractionCompletionStatus.COMPLETED
                exception = None
                error_code = None

            with self._condition:
                completion = DesktopInteractionCompletion(
                    interaction_id,
                    kind,
                    status,
                    status is DesktopInteractionCompletionStatus.CANCELLED
                    or token.cancel_requested,
                    result=result,
                    exception=exception,
                    error_code=error_code,
                )
                self._completion = completion
                self._lifecycle = (
                    DesktopInteractionLifecycle.SHUTTING_DOWN
                    if self._shutdown_requested
                    else DesktopInteractionLifecycle.BUSY
                )
                self._condition.notify_all()
