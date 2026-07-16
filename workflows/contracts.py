"""Typed contracts for small in-memory linear workflows."""

from __future__ import annotations

from dataclasses import dataclass, fields
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping

from core.execution_journal import safe_journal_metadata, safe_journal_text


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


def _contract_dict(value: object) -> dict[str, object]:
    result: dict[str, object] = {}
    for field in fields(value):
        item = getattr(value, field.name)
        if isinstance(item, Enum):
            result[field.name] = item.value
        elif isinstance(item, Mapping):
            result[field.name] = dict(item)
        elif isinstance(item, tuple):
            result[field.name] = tuple(item)
        else:
            result[field.name] = item
    return result


def safe_workflow_metadata(metadata: Mapping[str, Any] | None) -> Mapping[str, object]:
    return safe_journal_metadata(metadata)
