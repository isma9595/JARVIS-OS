"""Typed contracts for small in-memory linear workflows."""

from __future__ import annotations

from dataclasses import dataclass, fields
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping
import re

from core.execution_journal import safe_journal_metadata, safe_journal_text


_WORKFLOW_PATH_PATTERN = re.compile(r"(?i)\b[a-z]:[\\/][^\r\n\t ]+")
_WORKFLOW_USER_PATH_PATTERN = re.compile(r"(?i)([\\/]|^)(users|home)[\\/][^\\/\s]+")
_WORKFLOW_TECHNICAL_PATTERN = re.compile(r"(?i)(traceback|runtimeerror|exception|backend)")


class WorkflowStepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class WorkflowRunStatus(Enum):
    CREATED = "created"
    RUNNING = "running"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DENIED = "denied"


class WorkflowRunHistoryState(Enum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_FOR_CONFIRMATION = "waiting_for_confirmation"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


class WorkflowStepHistoryState(Enum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_FOR_CONFIRMATION = "waiting_for_confirmation"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


TERMINAL_WORKFLOW_STATUSES = {
    WorkflowRunStatus.SUCCEEDED,
    WorkflowRunStatus.FAILED,
    WorkflowRunStatus.CANCELLED,
    WorkflowRunStatus.DENIED,
}


@dataclass(frozen=True)
class WorkflowStepDefinition:
    step_id: str
    display_name_ru: str
    requires_confirmation: bool = False
    cancellable: bool = True
    verification_step: bool = False
    safe_metadata: Mapping[str, object] = MappingProxyType({})

    def __post_init__(self) -> None:
        object.__setattr__(self, "step_id", safe_journal_text(self.step_id, max_length=80))
        object.__setattr__(
            self,
            "display_name_ru",
            safe_journal_text(self.display_name_ru, max_length=120),
        )
        object.__setattr__(
            self,
            "safe_metadata",
            safe_journal_metadata(self.safe_metadata),
        )

    def to_dict(self) -> dict[str, object]:
        return _contract_dict(self)


@dataclass(frozen=True)
class WorkflowStepResult:
    step_id: str
    status: WorkflowStepStatus
    safe_message: str
    safe_output_metadata: Mapping[str, object] = MappingProxyType({})
    error_code: str | None = None
    requires_confirmation: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "step_id", safe_journal_text(self.step_id, max_length=80))
        object.__setattr__(
            self,
            "safe_message",
            safe_journal_text(self.safe_message, max_length=220),
        )
        object.__setattr__(
            self,
            "safe_output_metadata",
            safe_journal_metadata(self.safe_output_metadata),
        )
        if self.error_code is not None:
            object.__setattr__(
                self,
                "error_code",
                safe_journal_text(self.error_code, max_length=80),
            )

    def to_dict(self) -> dict[str, object]:
        return _contract_dict(self)


@dataclass(frozen=True)
class WorkflowRunSnapshot:
    workflow_id: str
    operation_id: str
    current_step_id: str | None
    current_step_name: str | None
    current_step_index: int
    total_steps: int
    completed_step_ids: tuple[str, ...]
    status: WorkflowRunStatus
    progress_percent: int
    awaiting_confirmation: bool
    cancellable: bool
    verified: bool
    safe_metadata: Mapping[str, object] = MappingProxyType({})

    def __post_init__(self) -> None:
        object.__setattr__(self, "workflow_id", safe_journal_text(self.workflow_id, max_length=80))
        object.__setattr__(self, "operation_id", safe_journal_text(self.operation_id, max_length=80))
        object.__setattr__(
            self,
            "current_step_id",
            safe_journal_text(self.current_step_id, max_length=80)
            if self.current_step_id is not None
            else None,
        )
        object.__setattr__(
            self,
            "current_step_name",
            safe_journal_text(self.current_step_name, max_length=120)
            if self.current_step_name is not None
            else None,
        )
        object.__setattr__(self, "completed_step_ids", tuple(self.completed_step_ids))
        object.__setattr__(self, "progress_percent", min(100, max(0, int(self.progress_percent))))
        object.__setattr__(self, "safe_metadata", safe_journal_metadata(self.safe_metadata))

    def to_dict(self) -> dict[str, object]:
        return _contract_dict(self)


@dataclass(frozen=True)
class WorkflowStepHistory:
    step_id: str
    step_index: int
    display_name: str
    operation_type: str | None
    state: WorkflowStepHistoryState
    started_at: str | None = None
    completed_at: str | None = None
    safe_result_summary: str | None = None
    safe_error_summary: str | None = None
    requires_confirmation: bool = False
    preview: bool = False
    metadata: Mapping[str, object] = MappingProxyType({})

    def __post_init__(self) -> None:
        object.__setattr__(self, "step_id", safe_workflow_text(self.step_id, max_length=80))
        object.__setattr__(self, "step_index", max(0, int(self.step_index)))
        object.__setattr__(
            self,
            "display_name",
            safe_workflow_text(self.display_name, max_length=120) or "Workflow step",
        )
        object.__setattr__(
            self,
            "operation_type",
            safe_workflow_text(self.operation_type, max_length=100)
            if self.operation_type is not None
            else None,
        )
        object.__setattr__(
            self,
            "started_at",
            safe_workflow_text(self.started_at, max_length=80) if self.started_at else None,
        )
        object.__setattr__(
            self,
            "completed_at",
            safe_workflow_text(self.completed_at, max_length=80)
            if self.completed_at
            else None,
        )
        object.__setattr__(
            self,
            "safe_result_summary",
            safe_workflow_text(self.safe_result_summary, max_length=220)
            if self.safe_result_summary
            else None,
        )
        object.__setattr__(
            self,
            "safe_error_summary",
            safe_workflow_text(self.safe_error_summary, max_length=160)
            if self.safe_error_summary
            else None,
        )
        object.__setattr__(
            self,
            "metadata",
            safe_workflow_history_metadata(self.metadata),
        )

    def to_dict(self) -> dict[str, object]:
        return _contract_dict(self)


@dataclass(frozen=True)
class WorkflowRunHistory:
    run_id: str
    operation_id: str
    workflow_id: str
    workflow_name: str | None
    objective_summary: str
    state: WorkflowRunHistoryState
    created_at: str
    started_at: str | None
    completed_at: str | None
    total_step_count: int
    completed_step_count: int
    active_step_id: str | None = None
    active_step_name: str | None = None
    safe_result_summary: str | None = None
    safe_failure_summary: str | None = None
    cancelled: bool = False
    waiting_for_confirmation: bool = False
    steps: tuple[WorkflowStepHistory, ...] = ()
    metadata: Mapping[str, object] = MappingProxyType({})

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", safe_workflow_text(self.run_id, max_length=80))
        object.__setattr__(self, "operation_id", safe_workflow_text(self.operation_id, max_length=80))
        object.__setattr__(self, "workflow_id", safe_workflow_text(self.workflow_id, max_length=80))
        object.__setattr__(
            self,
            "workflow_name",
            safe_workflow_text(self.workflow_name, max_length=120)
            if self.workflow_name is not None
            else None,
        )
        object.__setattr__(
            self,
            "objective_summary",
            safe_workflow_text(self.objective_summary, max_length=220)
            or "Workflow objective unavailable.",
        )
        object.__setattr__(
            self,
            "created_at",
            safe_workflow_text(self.created_at, max_length=80) or "unknown",
        )
        object.__setattr__(
            self,
            "started_at",
            safe_workflow_text(self.started_at, max_length=80) if self.started_at else None,
        )
        object.__setattr__(
            self,
            "completed_at",
            safe_workflow_text(self.completed_at, max_length=80)
            if self.completed_at
            else None,
        )
        object.__setattr__(self, "total_step_count", max(0, int(self.total_step_count)))
        object.__setattr__(
            self,
            "completed_step_count",
            min(self.total_step_count, max(0, int(self.completed_step_count))),
        )
        object.__setattr__(
            self,
            "active_step_id",
            safe_workflow_text(self.active_step_id, max_length=80)
            if self.active_step_id is not None
            else None,
        )
        object.__setattr__(
            self,
            "active_step_name",
            safe_workflow_text(self.active_step_name, max_length=120)
            if self.active_step_name is not None
            else None,
        )
        object.__setattr__(
            self,
            "safe_result_summary",
            safe_workflow_text(self.safe_result_summary, max_length=220)
            if self.safe_result_summary
            else None,
        )
        object.__setattr__(
            self,
            "safe_failure_summary",
            safe_workflow_text(self.safe_failure_summary, max_length=160)
            if self.safe_failure_summary
            else None,
        )
        object.__setattr__(self, "steps", tuple(self.steps))
        object.__setattr__(self, "metadata", safe_workflow_history_metadata(self.metadata))

    @property
    def progress_percent(self) -> int:
        if self.total_step_count <= 0:
            return 100 if self.state == WorkflowRunHistoryState.COMPLETED else 0
        if self.state == WorkflowRunHistoryState.COMPLETED:
            return 100
        return min(99, max(0, int((self.completed_step_count / self.total_step_count) * 100)))

    def to_dict(self) -> dict[str, object]:
        return _contract_dict(self)


@dataclass(frozen=True)
class WorkflowHistoryResult:
    ok: bool
    runs: tuple[WorkflowRunHistory, ...]
    limit: int
    max_limit: int
    empty: bool
    error: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "runs", tuple(self.runs))
        object.__setattr__(self, "limit", max(1, int(self.limit)))
        object.__setattr__(self, "max_limit", max(1, int(self.max_limit)))
        object.__setattr__(
            self,
            "error",
            safe_workflow_text(self.error, max_length=120) if self.error else None,
        )

    def to_dict(self) -> dict[str, object]:
        return _contract_dict(self)

    def safe_text_ru(self) -> str:
        if not self.ok:
            return "\n".join(
                [
                    "Workflow history:",
                    "- status: unavailable",
                    f"- error: {safe_workflow_text(self.error or 'workflow_history_unavailable')}",
                    "- no secrets",
                ]
            )
        if not self.runs:
            return "\n".join(
                [
                    "Workflow history:",
                    "- status: empty",
                    f"- limit: {self.limit}",
                    "- no runs",
                    "- no secrets",
                ]
            )
        return "\n".join(
            [
                "Workflow history:",
                "- status: ready",
                f"- runs: {len(self.runs)}",
                f"- limit: {self.limit}",
                "- newest first",
                "- no secrets",
                "",
                *[
                    (
                        f"{safe_workflow_text(run.created_at, max_length=40)} | "
                        f"{run.state.value} | "
                        f"{safe_workflow_text(run.workflow_id, max_length=80)} | "
                        f"{safe_workflow_text(run.objective_summary, max_length=120)}"
                    )
                    for run in self.runs
                ],
            ]
        )


def _contract_dict(value: object) -> dict[str, object]:
    result: dict[str, object] = {}
    for field in fields(value):
        item = getattr(value, field.name)
        if isinstance(item, Enum):
            result[field.name] = item.value
        elif isinstance(item, Mapping):
            result[field.name] = dict(item)
        elif isinstance(item, tuple):
            result[field.name] = tuple(
                child.to_dict() if hasattr(child, "to_dict") else child for child in item
            )
        else:
            result[field.name] = item
    return result


def safe_workflow_metadata(metadata: Mapping[str, Any] | None) -> Mapping[str, object]:
    return safe_journal_metadata(metadata)


def safe_workflow_text(value: Any, *, max_length: int = 160) -> str:
    safe = safe_journal_text(value, max_length=max_length)
    safe = _WORKFLOW_PATH_PATTERN.sub("[PATH REDACTED]", safe)
    safe = _WORKFLOW_USER_PATH_PATTERN.sub("[PATH REDACTED]", safe)
    if _WORKFLOW_TECHNICAL_PATTERN.search(safe):
        safe = "Safe workflow detail unavailable."
    if len(safe) > max_length:
        return safe[: max_length - 3].rstrip() + "..."
    return safe


def safe_workflow_history_metadata(metadata: Mapping[str, Any] | None) -> Mapping[str, object]:
    safe = dict(safe_workflow_metadata(metadata))
    return MappingProxyType(
        {
            safe_workflow_text(key, max_length=64): safe_workflow_text(value, max_length=140)
            for key, value in safe.items()
            if safe_workflow_text(key, max_length=64)
        }
    )
