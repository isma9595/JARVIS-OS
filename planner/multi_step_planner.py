"""Deterministic parser and session plan state for bounded linear plans."""

from __future__ import annotations

import re
from uuid import uuid4

from planner.capability_registry import PlannerCapabilityRegistry
from planner.contracts import (
    MAX_PLAN_STEPS,
    MAX_PLAN_TEXT_LENGTH,
    PlanParseResult,
    PlanParseStatus,
    PlanSnapshot,
    PlanStatus,
    PlanStepDefinition,
    PlanStepSnapshot,
    PlanStepStatus,
    contains_control_characters,
    contains_credential_like_value,
    default_plan_step_message,
    safe_plan_text,
)


TERMINAL_PLAN_STATUSES = {
    PlanStatus.SUCCEEDED,
    PlanStatus.FAILED,
    PlanStatus.CANCELLED,
    PlanStatus.BLOCKED,
}


class MultiStepPlanner:
    """Create and inspect one active session plan without executing steps."""

    CREATE_PREFIXES_RU = ("составь план:", "создай план:", "спланируй:")
    CREATE_PREFIXES_EN = ("create plan:", "plan:")
    SHOW_RU = {"покажи план", "покажи текущий план"}
    SHOW_EN = {"show plan", "show current plan"}
    EXECUTE_RU = {"выполни план", "запусти план"}
    EXECUTE_EN = {"execute plan", "run plan"}
    CANCEL_RU = {"отмени план", "отменить текущий план"}
    CANCEL_EN = {"cancel plan", "cancel current plan"}

    def __init__(self, registry: PlannerCapabilityRegistry):
        self.registry = registry
        self._active_plan: _PlanState | None = None

    @property
    def active_plan(self) -> PlanSnapshot | None:
        return self.snapshot()

    def snapshot(self) -> PlanSnapshot | None:
        if self._active_plan is None:
            return None
        return self._active_plan.snapshot()

    def replace_with_snapshot(self, snapshot: PlanSnapshot, steps: tuple[PlanStepDefinition, ...]) -> None:
        self._active_plan = _PlanState(
            plan_id=snapshot.plan_id,
            goal_summary=snapshot.goal_summary,
            language_code=snapshot.language_code,
            steps=steps,
            registry=self.registry,
            status=snapshot.status,
        )

    def create_from_text(
        self,
        text: str,
        *,
        language_code: str,
        activate: bool = True,
    ) -> PlanParseResult:
        raw = str(text or "").strip()
        normalized = self._normalize(raw)
        body = self._creation_body(raw, normalized)
        if body is None:
            return PlanParseResult(PlanParseStatus.NOT_PLANNER_COMMAND)
        if activate and self._active_plan is not None and self._active_plan.status in {
            PlanStatus.RUNNING,
            PlanStatus.AWAITING_CONFIRMATION,
        }:
            return PlanParseResult(
                PlanParseStatus.ERROR,
                snapshot=self._active_plan.snapshot(),
                safe_message=self._text(language_code, "Сначала отмените текущий план.", "Cancel the current plan first."),
                safe_error_code="active_plan_not_replaceable",
            )
        validation = self._validate_text(body, language_code)
        if validation is not None:
            return validation
        parts = self._split_steps(body)
        if not parts:
            return PlanParseResult(
                PlanParseStatus.ERROR,
                safe_message=self._text(language_code, "План пуст.", "The plan is empty."),
                safe_error_code="empty_plan",
            )
        if len(parts) > MAX_PLAN_STEPS:
            return PlanParseResult(
                PlanParseStatus.ERROR,
                safe_message=self._text(language_code, "В плане больше 8 этапов.", "The plan has more than 8 steps."),
                safe_error_code="too_many_steps",
            )
        steps: list[PlanStepDefinition] = []
        for index, part in enumerate(parts, start=1):
            parsed = self._parse_step(part, index, language_code)
            if isinstance(parsed, PlanParseResult):
                return parsed
            steps.append(parsed)
        plan = _PlanState(
            plan_id=("plan-" + uuid4().hex) if activate else "plan-preview",
            goal_summary=safe_plan_text(body, 220),
            language_code=language_code,
            steps=tuple(steps),
            registry=self.registry,
            status=PlanStatus.PROPOSED,
        )
        if activate:
            self._active_plan = plan
        return PlanParseResult(
            PlanParseStatus.CREATED,
            snapshot=plan.snapshot(message=self._text(language_code, "План составлен.", "Plan created.")),
            safe_message=self._text(language_code, "План составлен.", "Plan created."),
        )

    def preview_create_from_text(self, text: str, *, language_code: str) -> PlanParseResult:
        return self.create_from_text(text, language_code=language_code, activate=False)

    def command_kind(self, text: str, *, language_code: str) -> PlanParseStatus:
        raw = str(text or "").strip()
        normalized = self._normalize(raw)
        if self._creation_body(raw, normalized) is not None:
            return PlanParseStatus.CREATED
        if normalized in self.SHOW_RU or normalized in self.SHOW_EN:
            return PlanParseStatus.SHOW
        if normalized in self.EXECUTE_RU or normalized in self.EXECUTE_EN:
            return PlanParseStatus.EXECUTE
        if normalized in self.CANCEL_RU or normalized in self.CANCEL_EN:
            return PlanParseStatus.CANCEL
        return PlanParseStatus.NOT_PLANNER_COMMAND

    def set_status(
        self,
        status: PlanStatus,
        *,
        operation_id: str | None = None,
        step_statuses: dict[str, PlanStepStatus] | None = None,
        step_messages: dict[str, str] | None = None,
        step_errors: dict[str, str | None] | None = None,
        current_step_id: str | None = None,
        safe_message: str | None = None,
    ) -> PlanSnapshot | None:
        if self._active_plan is None:
            return None
        self._active_plan.status = status
        if operation_id is not None:
            self._active_plan.operation_id = operation_id
        if step_statuses:
            self._active_plan.step_statuses.update(step_statuses)
        if step_messages:
            self._active_plan.step_messages.update(step_messages)
        if step_errors:
            self._active_plan.step_errors.update(step_errors)
        self._active_plan.current_step_id = current_step_id
        return self._active_plan.snapshot(message=safe_message)

    def steps(self) -> tuple[PlanStepDefinition, ...]:
        return self._active_plan.steps if self._active_plan is not None else ()

    def _creation_body(self, raw: str, normalized: str) -> str | None:
        raw_lower = str(raw or "").strip().lower()
        for prefix in self.CREATE_PREFIXES_RU + self.CREATE_PREFIXES_EN:
            if raw_lower.startswith(prefix):
                return raw[len(prefix) :].strip()
        return None

    def _validate_text(self, text: str, language_code: str) -> PlanParseResult | None:
        if not text.strip():
            return PlanParseResult(PlanParseStatus.ERROR, safe_message=self._text(language_code, "План пуст.", "The plan is empty."), safe_error_code="empty_plan")
        if len(text) > MAX_PLAN_TEXT_LENGTH:
            return PlanParseResult(PlanParseStatus.ERROR, safe_message=self._text(language_code, "Текст плана слишком длинный.", "The plan text is too long."), safe_error_code="plan_text_too_large")
        if contains_control_characters(text):
            return PlanParseResult(PlanParseStatus.ERROR, safe_message=self._text(language_code, "Текст плана содержит управляющие символы.", "The plan text contains control characters."), safe_error_code="control_characters_rejected")
        if contains_credential_like_value(text):
            return PlanParseResult(PlanParseStatus.ERROR, safe_message=self._text(language_code, "План содержит похожие на секрет значения: [REDACTED].", "The plan contains credential-like values: [REDACTED]."), safe_error_code="credential_like_value_rejected")
        return None

    def _split_steps(self, body: str) -> tuple[str, ...]:
        prepared = re.sub(r"\b(?:затем|потом|после этого|then)\b", ";", body, flags=re.IGNORECASE)
        return tuple(part.strip() for part in prepared.split(";") if part.strip())

    def _parse_step(self, text: str, position: int, language_code: str) -> PlanStepDefinition | PlanParseResult:
        normalized = self._normalize(text)
        exact: tuple[str, dict[str, object], str] | None = None
        ambiguous = False
        if normalized in {"статус системы", "состояние системы", "system status"}:
            exact = ("system.status", {}, text)
        elif normalized in {"профиль запуска", "статус запуска", "startup profile", "startup status"}:
            exact = ("startup.profile", {}, text)
        elif normalized in {"текущий язык", "покажи текущий язык", "покажи язык", "current language", "show language"}:
            exact = ("language.get", {}, text)
        elif normalized.startswith(("язык ", "установить язык ", "set language to ", "language ")):
            value = self._language_value(text, normalized)
            if not value:
                return self._unrecognized(position, language_code)
            exact = ("language.set", {"language_code": value}, f"language={value}")
        elif normalized in {"покажи память", "покажи что ты помнишь обо мне", "show memory", "show what you remember about me"}:
            exact = ("memory.list", {}, text)
        elif normalized in {"покажи тестовое слово", "show test word"}:
            exact = ("memory.recall", {"key": "тестовое слово" if language_code != "en-US" else "test word"}, text)
        elif normalized.startswith(("что ты помнишь о ", "что ты помнишь об ", "что ты помнишь про ", "what do you remember about ")):
            key = self._strip_first_matching(text, ("что ты помнишь о ", "что ты помнишь об ", "что ты помнишь про ", "what do you remember about "))
            exact = ("memory.recall", {"key": key}, f"key={key}")
        elif normalized.startswith(("запомни тестовое слово ", "remember test word ")):
            value = text.split()[-1].strip()
            key = "тестовое слово" if language_code != "en-US" else "test word"
            exact = ("memory.remember", {"key": key, "value": value}, f"{key}={value}")
        elif normalized.startswith(("запомни", "remember")):
            parsed = self._parse_remember(text)
            if parsed is None:
                return self._clarify(position, language_code)
            exact = ("memory.remember", {"key": parsed[0], "value": parsed[1]}, f"{parsed[0]}={parsed[1]}")
        elif normalized in {"забудь все что ты помнишь обо мне", "забудь все, что ты помнишь обо мне", "forget everything you remember about me"}:
            exact = ("memory.forget_all", {}, text)
        elif normalized.startswith(("забудь ", "forget ")):
            key = self._strip_first_matching(text, ("забудь ", "forget "))
            if not key:
                return self._clarify(position, language_code)
            exact = ("memory.forget", {"key": key}, f"key={key}")
        elif normalized in {"покажи статус", "show status"}:
            ambiguous = True

        if ambiguous:
            return self._clarify(position, language_code)
        if exact is None:
            return self._unrecognized(position, language_code)
        capability_id, arguments, summary = exact
        if capability_id not in self.registry:
            return self._unrecognized(position, language_code)
        if any(not str(value or "").strip() for value in arguments.values()):
            return self._clarify(position, language_code)
        descriptor = self.registry.descriptor(capability_id)
        return PlanStepDefinition(
            step_id=f"step-{position}",
            position=position,
            capability_id=capability_id,
            arguments=arguments,
            safe_argument_summary=summary,
            requires_confirmation=descriptor.requires_confirmation,
            risk_level=descriptor.risk_level,
        )

    def _unrecognized(self, position: int, language_code: str) -> PlanParseResult:
        return PlanParseResult(
            PlanParseStatus.ERROR,
            safe_message=self._text(language_code, f"Не удалось распознать этап {position}.", f"Step {position} could not be recognized."),
            safe_error_code="planner_step_unrecognized",
            step_index=position,
        )

    def _clarify(self, position: int, language_code: str) -> PlanParseResult:
        return PlanParseResult(
            PlanParseStatus.CLARIFICATION_REQUIRED,
            safe_message=self._text(language_code, f"Нужно уточнить этап {position}.", f"Step {position} needs clarification."),
            safe_error_code="planner_step_ambiguous",
            step_index=position,
        )

    @staticmethod
    def _normalize(text: str) -> str:
        normalized = str(text or "").strip().lower().replace("ё", "е")
        normalized = re.sub(r"[,:]+", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized

    @staticmethod
    def _strip_first_matching(text: str, prefixes: tuple[str, ...]) -> str:
        lower = text.lower()
        for prefix in prefixes:
            if lower.startswith(prefix):
                return text[len(prefix) :].strip()
        return ""

    @staticmethod
    def _parse_remember(text: str) -> tuple[str, str] | None:
        body = re.sub(r"(?is)^\s*(?:запомни(?:\s*,?\s*что|:)?|remember(?:\s+that|:)?)\s+", "", text).strip()
        for separator in (" — ", " – ", " - ", "=", ":"):
            if separator in body:
                left, right = body.split(separator, 1)
                return left.strip(), right.strip()
        match = re.match(r"(?is)^(.+?)\s+is\s+(.+)$", body)
        if match:
            return match.group(1).strip(), match.group(2).strip()
        return None

    @staticmethod
    def _language_value(text: str, normalized: str) -> str:
        if "english" in normalized or "англий" in normalized or "en-us" in normalized:
            return "en-US"
        if "russian" in normalized or "русск" in normalized or "ru-ru" in normalized:
            return "ru-RU"
        return text.split()[-1].strip()

    @staticmethod
    def _text(language_code: str, ru: str, en: str) -> str:
        return en if language_code == "en-US" else ru


class _PlanState:
    def __init__(
        self,
        *,
        plan_id: str,
        goal_summary: str,
        language_code: str,
        steps: tuple[PlanStepDefinition, ...],
        registry: PlannerCapabilityRegistry,
        status: PlanStatus,
    ):
        self.plan_id = plan_id
        self.operation_id: str | None = None
        self.goal_summary = goal_summary
        self.language_code = language_code
        self.steps = steps
        self.registry = registry
        self.status = status
        self.step_statuses = {step.step_id: PlanStepStatus.PENDING for step in steps}
        self.step_messages = {step.step_id: "" for step in steps}
        self.step_errors: dict[str, str | None] = {step.step_id: None for step in steps}
        self.current_step_id: str | None = None

    def snapshot(self, message: str | None = None) -> PlanSnapshot:
        completed = sum(1 for status in self.step_statuses.values() if status == PlanStepStatus.SUCCEEDED)
        if self.status == PlanStatus.SUCCEEDED:
            progress = 100
        elif not self.steps:
            progress = 0
        else:
            progress = min(99, int((completed / len(self.steps)) * 100))
        current_index = 0
        if self.current_step_id:
            for step in self.steps:
                if step.step_id == self.current_step_id:
                    current_index = step.position - 1
                    break
        elif self.status in TERMINAL_PLAN_STATUSES:
            current_index = len(self.steps)
        snapshots = []
        for step in self.steps:
            descriptor = self.registry.descriptor(step.capability_id)
            status = self.step_statuses.get(step.step_id, PlanStepStatus.PENDING)
            snapshots.append(
                PlanStepSnapshot(
                    step_id=step.step_id,
                    position=step.position,
                    capability_id=step.capability_id,
                    display_name=descriptor.display_name(self.language_code),
                    status=status,
                    safe_message=self.step_messages.get(step.step_id) or default_plan_step_message(status, self.language_code),
                    safe_argument_summary=step.safe_argument_summary,
                    risk_level=step.risk_level,
                    side_effect=descriptor.side_effect.value,
                    requires_confirmation=step.requires_confirmation,
                    is_current=step.step_id == self.current_step_id,
                    error_code=self.step_errors.get(step.step_id),
                )
            )
        return PlanSnapshot(
            plan_id=self.plan_id,
            operation_id=self.operation_id,
            goal_summary=self.goal_summary,
            language_code=self.language_code,
            status=self.status,
            current_step_id=self.current_step_id,
            current_step_index=current_index,
            total_steps=len(self.steps),
            completed_steps=completed,
            progress_percent=progress,
            awaiting_confirmation=self.status == PlanStatus.AWAITING_CONFIRMATION,
            cancellable=self.status not in TERMINAL_PLAN_STATUSES,
            steps=tuple(snapshots),
            safe_message=message or self._default_plan_message(),
        )

    def _default_plan_message(self) -> str:
        if self.status == PlanStatus.PROPOSED:
            return "The plan has not been executed." if self.language_code == "en-US" else "План ещё не выполнялся."
        if self.status == PlanStatus.SUCCEEDED:
            return "Plan completed." if self.language_code == "en-US" else "План завершён."
        if self.status == PlanStatus.CANCELLED:
            return "Plan cancelled." if self.language_code == "en-US" else "План отменён."
        return self.status.value
