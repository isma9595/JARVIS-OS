"""Safe application-level activity projection for AppService."""

from __future__ import annotations

from threading import RLock

from app.app_contracts import (
    ApplicationActivityDto,
    ApplicationActivityKind,
    ApplicationActivitySnapshotDto,
    ApplicationActivityState,
    safe_history_text,
)
from core.execution_journal import ExecutionOperation, ExecutionStatus, utc_now_iso


_ACTIVE_STATES = {
    ApplicationActivityState.STARTING,
    ApplicationActivityState.RUNNING,
    ApplicationActivityState.WAITING_FOR_USER,
    ApplicationActivityState.CANCELLATION_REQUESTED,
}
_TERMINAL_STATES = {
    ApplicationActivityState.SUCCEEDED,
    ApplicationActivityState.FAILED,
    ApplicationActivityState.REJECTED,
    ApplicationActivityState.CANCELLED,
    ApplicationActivityState.UNKNOWN,
}


class ApplicationActivityTracker:
    """Project bounded operation lifecycle snapshots into Desktop-safe activity."""

    def __init__(self, *, recent_limit: int = 10):
        self.recent_limit = max(1, int(recent_limit))
        self._lock = RLock()
        self._records: dict[str, ApplicationActivityDto] = {}
        self._current_id: str | None = None
        self._revision = 0

    def snapshot_from_operations(
        self,
        operations: tuple[ExecutionOperation, ...],
    ) -> ApplicationActivitySnapshotDto:
        with self._lock:
            for operation in tuple(operations or ()):
                self._ingest_operation(operation)
            current = self._records.get(self._current_id or "")
            if current is not None and not current.is_active:
                current = self._latest_active_locked()
                self._current_id = current.activity_id if current is not None else None
            recent = self._recent_terminal_locked()
            return ApplicationActivitySnapshotDto(
                current=current,
                recent=recent,
                is_busy=current is not None and current.is_active,
                requires_user_attention=(
                    current is not None and current.requires_user_attention
                ),
                updated_at=utc_now_iso(),
                revision=self._revision,
                status_available=True,
            )

    def snapshot_unavailable(self, *, error: str = "application_activity_unavailable"):
        with self._lock:
            return ApplicationActivitySnapshotDto(
                current=None,
                recent=self._recent_terminal_locked(),
                is_busy=False,
                requires_user_attention=False,
                updated_at=utc_now_iso(),
                revision=self._revision,
                status_available=False,
                error=error,
            )

    def record_operation(self, operation: ExecutionOperation) -> ApplicationActivityDto:
        with self._lock:
            return self._ingest_operation(operation)

    def _ingest_operation(self, operation: ExecutionOperation) -> ApplicationActivityDto:
        projected = _project_operation(operation, revision=self._revision + 1)
        previous = self._records.get(projected.activity_id)
        if previous is not None and previous.state in _TERMINAL_STATES:
            if projected.state in _ACTIVE_STATES:
                return previous
            if projected.state in _TERMINAL_STATES:
                return previous

        if previous is not None and previous.to_dict() == projected.to_dict():
            return previous

        self._revision += 1
        projected = _project_operation(operation, revision=self._revision)
        self._records[projected.activity_id] = projected
        if projected.is_active:
            self._current_id = projected.activity_id
        elif self._current_id == projected.activity_id:
            current = self._latest_active_locked()
            self._current_id = current.activity_id if current is not None else None
        self._trim_locked()
        return projected

    def _latest_active_locked(self) -> ApplicationActivityDto | None:
        active = tuple(activity for activity in self._records.values() if activity.is_active)
        if not active:
            return None
        return max(active, key=lambda activity: activity.revision)

    def _recent_terminal_locked(self) -> tuple[ApplicationActivityDto, ...]:
        terminal = tuple(
            activity
            for activity in self._records.values()
            if activity.state in _TERMINAL_STATES
        )
        return tuple(
            sorted(terminal, key=lambda activity: activity.revision, reverse=True)[
                : self.recent_limit
            ]
        )

    def _trim_locked(self) -> None:
        keep_ids = {self._current_id} if self._current_id else set()
        keep_ids.update(activity.activity_id for activity in self._recent_terminal_locked())
        active_ids = {
            activity.activity_id
            for activity in self._records.values()
            if activity.is_active
        }
        keep_ids.update(active_ids)
        for activity_id in tuple(self._records):
            if activity_id not in keep_ids:
                self._records.pop(activity_id, None)


def _project_operation(
    operation: ExecutionOperation,
    *,
    revision: int,
) -> ApplicationActivityDto:
    state = _activity_state(operation)
    kind = _activity_kind(operation)
    is_active = state in _ACTIVE_STATES
    cancellation_requested = state == ApplicationActivityState.CANCELLATION_REQUESTED
    requires_attention = state == ApplicationActivityState.WAITING_FOR_USER
    finished_at = None if is_active else operation.updated_at
    source_run_id = _safe_metadata_value(operation, "workflow_resume_source_run_id")
    if source_run_id is None:
        source_run_id = _safe_metadata_value(operation, "workflow_run_id")
    return ApplicationActivityDto(
        activity_id=operation.operation_id,
        kind=kind,
        state=state,
        title=_activity_title(operation, kind),
        detail=_activity_detail(operation),
        started_at=operation.created_at,
        updated_at=operation.updated_at,
        finished_at=finished_at,
        is_active=is_active,
        requires_user_attention=requires_attention,
        cancellation_requested=cancellation_requested,
        can_cancel=bool(operation.cancellable and is_active),
        cancel_target_id=operation.operation_id if operation.cancellable and is_active else None,
        source_run_id=source_run_id,
        error_message=_activity_error(operation, state),
        revision=revision,
    )


def _activity_state(operation: ExecutionOperation) -> ApplicationActivityState:
    status = operation.status
    if not isinstance(status, ExecutionStatus):
        return ApplicationActivityState.UNKNOWN
    if _metadata_true(operation, "workflow_cancellation_requested") and status in {
        ExecutionStatus.CREATED,
        ExecutionStatus.RUNNING,
        ExecutionStatus.AWAITING_CLARIFICATION,
        ExecutionStatus.AWAITING_CONFIRMATION,
    }:
        return ApplicationActivityState.CANCELLATION_REQUESTED
    return {
        ExecutionStatus.CREATED: ApplicationActivityState.STARTING,
        ExecutionStatus.RUNNING: ApplicationActivityState.RUNNING,
        ExecutionStatus.AWAITING_CLARIFICATION: ApplicationActivityState.WAITING_FOR_USER,
        ExecutionStatus.AWAITING_CONFIRMATION: ApplicationActivityState.WAITING_FOR_USER,
        ExecutionStatus.SUCCEEDED: ApplicationActivityState.SUCCEEDED,
        ExecutionStatus.FAILED: ApplicationActivityState.FAILED,
        ExecutionStatus.CANCELLED: ApplicationActivityState.CANCELLED,
        ExecutionStatus.DENIED: ApplicationActivityState.REJECTED,
        ExecutionStatus.DUPLICATE_SUPPRESSED: ApplicationActivityState.REJECTED,
    }.get(status, ApplicationActivityState.UNKNOWN)


def _activity_kind(operation: ExecutionOperation) -> ApplicationActivityKind:
    command_id = str(operation.command_id or "")
    action_id = str(operation.action_id or "")
    metadata = operation.metadata or {}
    if command_id == "workflow.resume" or action_id == "workflow.resume":
        return ApplicationActivityKind.WORKFLOW_RESUME
    if command_id == "workflow.cancel" or action_id == "workflow.cancel":
        return ApplicationActivityKind.WORKFLOW_CANCELLATION
    if metadata.get("workflow_id") or command_id.startswith("document_review"):
        return ApplicationActivityKind.WORKFLOW_EXECUTION
    if command_id.startswith("ai.") or action_id.startswith("ai."):
        return ApplicationActivityKind.ASSISTANT_REQUEST
    if command_id.startswith("app.") or action_id.startswith("app."):
        return ApplicationActivityKind.SYSTEM_OPERATION
    if command_id or action_id:
        return ApplicationActivityKind.COMMAND_EXECUTION
    return ApplicationActivityKind.UNKNOWN


def _activity_title(operation: ExecutionOperation, kind: ApplicationActivityKind) -> str:
    label = operation.command_id or operation.action_id
    if label:
        return safe_history_text(label, max_length=120)
    return {
        ApplicationActivityKind.WORKFLOW_EXECUTION: "Workflow execution",
        ApplicationActivityKind.WORKFLOW_RESUME: "Workflow resume",
        ApplicationActivityKind.WORKFLOW_CANCELLATION: "Workflow cancellation",
        ApplicationActivityKind.ASSISTANT_REQUEST: "Assistant request",
        ApplicationActivityKind.SYSTEM_OPERATION: "System operation",
        ApplicationActivityKind.COMMAND_EXECUTION: "Command execution",
    }.get(kind, "Application activity")


def _activity_detail(operation: ExecutionOperation) -> str:
    summary = operation.safe_result_summary
    if summary:
        return safe_history_text(summary, max_length=180)
    command = operation.command_id or operation.action_id or "operation"
    return safe_history_text(f"{operation.source} {command}", max_length=180)


def _activity_error(
    operation: ExecutionOperation,
    state: ApplicationActivityState,
) -> str | None:
    if state not in {
        ApplicationActivityState.FAILED,
        ApplicationActivityState.REJECTED,
        ApplicationActivityState.CANCELLED,
        ApplicationActivityState.UNKNOWN,
    }:
        return None
    return safe_history_text(
        operation.safe_error_code or "Safe activity detail unavailable.",
        max_length=120,
    )


def _metadata_true(operation: ExecutionOperation, key: str) -> bool:
    value = (operation.metadata or {}).get(key)
    return str(value).strip().lower() in {"1", "true", "yes"}


def _safe_metadata_value(operation: ExecutionOperation, key: str) -> str | None:
    value = (operation.metadata or {}).get(key)
    if value in {None, ""}:
        return None
    return safe_history_text(value, max_length=80)
