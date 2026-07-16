"""Typed contracts for the bounded general multi-step planner."""

from __future__ import annotations

from dataclasses import dataclass, fields
from enum import Enum
from types import MappingProxyType
from typing import Any, Callable, Mapping
import re

from core.execution_journal import safe_journal_metadata, safe_journal_text


MAX_PLAN_STEPS = 8
MAX_PLAN_TEXT_LENGTH = 1200


_SECRET_PATTERN = re.compile(
    r"(?is)(sk-[a-z0-9_-]{8,}|api[_ -]?key\s*[:=]?\s*\S+|access[_ -]?token\s*[:=]?\s*\S+|"
    r"token\s*[:=]?\s*\S+|password\s*[:=]?\s*\S+|-----BEGIN [A-Z ]*PRIVATE KEY-----)"
)
_CONTROL_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class PlanStatus(Enum):
    PROPOSED = "proposed"
    READY = "ready"
    RUNNING = "running"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"


class PlanStepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


class PlanParseStatus(Enum):
    NOT_PLANNER_COMMAND = "not_planner_command"
    CREATED = "created"
    SHOW = "show"
    EXECUTE = "execute"
    CANCEL = "cancel"
    ERROR = "error"
    CLARIFICATION_REQUIRED = "clarification_required"


class PlanSideEffect(Enum):
    READ_ONLY = "read_only"
    BOUNDED_LOCAL_STATE = "bounded_local_state"


@dataclass(frozen=True)
class PlanCapabilityDescriptor:
    capability_id: str
    display_name_ru: str
    display_name_en: str
    category: str
    risk_level: str
    side_effect: PlanSideEffect
    requires_confirmation: bool
    argument_schema: Mapping[str, object]
    safe_description: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "capability_id", safe_plan_text(self.capability_id, 80))
        object.__setattr__(self, "display_name_ru", safe_plan_text(self.display_name_ru, 120))
        object.__setattr__(self, "display_name_en", safe_plan_text(self.display_name_en, 120))
        object.__setattr__(self, "category", safe_plan_text(self.category, 80))
        object.__setattr__(self, "risk_level", safe_plan_text(self.risk_level, 80))
        object.__setattr__(self, "argument_schema", safe_journal_metadata(self.argument_schema))
        object.__setattr__(self, "safe_description", safe_plan_text(self.safe_description, 180))

    def display_name(self, language_code: str) -> str:
        return self.display_name_en if language_code == "en-US" else self.display_name_ru

    def to_dict(self) -> dict[str, object]:
        return _contract_dict(self)


@dataclass(frozen=True)
class PlanCapability:
    descriptor: PlanCapabilityDescriptor
    executor: Callable[[Mapping[str, object]], object]
    policy_factory: Callable[[Mapping[str, object], bool], object]


@dataclass(frozen=True)
class PlanStepDefinition:
    step_id: str
    position: int
    capability_id: str
    arguments: Mapping[str, object]
    safe_argument_summary: str
    requires_confirmation: bool
    risk_level: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "step_id", safe_plan_text(self.step_id, 80))
        object.__setattr__(self, "capability_id", safe_plan_text(self.capability_id, 80))
        object.__setattr__(self, "arguments", safe_journal_metadata(self.arguments))
        object.__setattr__(self, "safe_argument_summary", safe_plan_text(self.safe_argument_summary, 160))
        object.__setattr__(self, "risk_level", safe_plan_text(self.risk_level, 80))

    def to_dict(self) -> dict[str, object]:
        return _contract_dict(self)


@dataclass(frozen=True)
class PlanStepSnapshot:
    step_id: str
    position: int
    capability_id: str
    display_name: str
    status: PlanStepStatus
    safe_message: str
    requires_confirmation: bool
    error_code: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "step_id", safe_plan_text(self.step_id, 80))
        object.__setattr__(self, "capability_id", safe_plan_text(self.capability_id, 80))
        object.__setattr__(self, "display_name", safe_plan_text(self.display_name, 120))
        object.__setattr__(self, "safe_message", safe_plan_text(self.safe_message, 220))
        if self.error_code is not None:
            object.__setattr__(self, "error_code", safe_plan_text(self.error_code, 80))

    def to_dict(self) -> dict[str, object]:
        return _contract_dict(self)


@dataclass(frozen=True)
class PlanSnapshot:
    plan_id: str
    operation_id: str | None
    goal_summary: str
    language_code: str
    status: PlanStatus
    current_step_id: str | None
    current_step_index: int
    total_steps: int
    completed_steps: int
    progress_percent: int
    awaiting_confirmation: bool
    cancellable: bool
    steps: tuple[PlanStepSnapshot, ...]
    safe_message: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "plan_id", safe_plan_text(self.plan_id, 80))
        if self.operation_id is not None:
            object.__setattr__(self, "operation_id", safe_plan_text(self.operation_id, 80))
        object.__setattr__(self, "goal_summary", safe_plan_text(self.goal_summary, 220))
        object.__setattr__(self, "language_code", safe_plan_text(self.language_code, 16))
        object.__setattr__(self, "progress_percent", min(100, max(0, int(self.progress_percent))))
        object.__setattr__(self, "steps", tuple(self.steps))
        object.__setattr__(self, "safe_message", safe_plan_text(self.safe_message, 240))

    def to_dict(self) -> dict[str, object]:
        return _contract_dict(self)


@dataclass(frozen=True)
class PlanExecutionResult:
    plan_id: str
    operation_id: str | None
    status: PlanStatus
    completed_steps: int
    total_steps: int
    progress_percent: int
    safe_message: str
    safe_error_code: str | None = None
    snapshot: PlanSnapshot | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "plan_id", safe_plan_text(self.plan_id, 80))
        if self.operation_id is not None:
            object.__setattr__(self, "operation_id", safe_plan_text(self.operation_id, 80))
        object.__setattr__(self, "progress_percent", min(100, max(0, int(self.progress_percent))))
        object.__setattr__(self, "safe_message", safe_plan_text(self.safe_message, 240))
        if self.safe_error_code is not None:
            object.__setattr__(self, "safe_error_code", safe_plan_text(self.safe_error_code, 80))

    def to_dict(self) -> dict[str, object]:
        return _contract_dict(self)


@dataclass(frozen=True)
class PlanParseResult:
    status: PlanParseStatus
    snapshot: PlanSnapshot | None = None
    safe_message: str = ""
    safe_error_code: str | None = None
    step_index: int | None = None


def safe_plan_text(value: Any, max_length: int = 220) -> str:
    text = _SECRET_PATTERN.sub("[REDACTED]", str(value or ""))
    text = text.replace("\r", " ").replace("\n", " ").strip()
    if len(text) > max_length:
        return text[: max_length - 3].rstrip() + "..."
    return text


def contains_control_characters(value: str) -> bool:
    return bool(_CONTROL_PATTERN.search(str(value or "")))


def contains_credential_like_value(value: str) -> bool:
    return bool(_SECRET_PATTERN.search(str(value or "")))


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
                element.to_dict() if hasattr(element, "to_dict") else element
                for element in item
            )
        elif hasattr(item, "to_dict"):
            result[field.name] = item.to_dict()
        else:
            result[field.name] = item
    return result


EMPTY_MAPPING: Mapping[str, object] = MappingProxyType({})
