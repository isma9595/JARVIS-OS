"""Planner-specific AppService orchestration."""

from collections.abc import Callable

from app.app_contracts import AppCommandPreview, AppCommandResult, AppCommandSource
from app.text_normalization import normalize_control_text
from planner import (
    MultiStepPlanner,
    PlanExecutor,
    PlanParseStatus,
    PlanSideEffect,
    PlanSnapshot,
    PlanStatus,
    PlanStepSnapshot,
    TERMINAL_PLAN_STATUSES,
)


LanguageCodeProvider = Callable[[], str]
LocalizedTextFormatter = Callable[[str, str], str]
SafeTextPreviewer = Callable[[str], str]


class PlannerCommandService:
    """Focused application service for planner preview and execution routes.

    Callable dependencies are stable value-level contracts, not AppService
    references. ``language_code`` returns the active locale code,
    ``localized_text`` selects between already-supplied safe RU/EN strings, and
    ``safe_text_preview`` returns a redacted bounded preview string.
    """

    def __init__(
        self,
        *,
        multi_step_planner: MultiStepPlanner,
        plan_executor: PlanExecutor,
        language_code: LanguageCodeProvider,
        localized_text: LocalizedTextFormatter,
        safe_text_preview: SafeTextPreviewer,
    ):
        self._multi_step_planner = multi_step_planner
        self._plan_executor = plan_executor
        self._language_code = language_code
        self._localized_text = localized_text
        self._safe_text_preview = safe_text_preview

    def preview_command(
        self,
        input_text: str,
        normalized_text: str,
    ) -> AppCommandPreview | None:
        language_code = self._language_code()
        kind = self._multi_step_planner.command_kind(input_text, language_code=language_code)
        if kind == PlanParseStatus.NOT_PLANNER_COMMAND:
            return None

        active = self._multi_step_planner.snapshot()
        valid = True
        error_code = None
        step_count = getattr(active, "total_steps", None)
        status = getattr(getattr(active, "status", None), "value", None)
        requires_confirmation = False
        risk_level = "read_only"
        read_only = True
        active_plan_id = None
        active_plan_status = None
        active_step_id = None
        active_step_capability_id = None
        active_step_name = None
        operation_id = None

        if kind == PlanParseStatus.CREATED:
            parsed = self._multi_step_planner.preview_create_from_text(
                input_text,
                language_code=language_code,
            )
            valid = parsed.status == PlanParseStatus.CREATED
            error_code = parsed.safe_error_code
            step_count = getattr(parsed.snapshot, "total_steps", None)
            status = getattr(getattr(parsed.snapshot, "status", None), "value", None)
            projected_step = self._next_effective_step(parsed.snapshot)
            if projected_step is not None:
                risk_level = getattr(projected_step, "risk_level", None) or "read_only"
                requires_confirmation = bool(
                    getattr(projected_step, "requires_confirmation", False)
                )
                read_only = (
                    getattr(projected_step, "side_effect", None)
                    == PlanSideEffect.READ_ONLY.value
                )
                active_step_id = self._safe_optional_preview_text(
                    getattr(projected_step, "step_id", None)
                )
                active_step_capability_id = self._safe_optional_preview_text(
                    getattr(projected_step, "capability_id", None)
                )
                active_step_name = self._safe_optional_preview_text(
                    getattr(projected_step, "display_name", None)
                )
        elif kind == PlanParseStatus.EXECUTE:
            projected_step = self._next_effective_step(active)
            active_plan_id = self._safe_optional_preview_text(getattr(active, "plan_id", None))
            active_plan_status = self._safe_optional_preview_text(status)
            if projected_step is not None:
                risk_level = getattr(projected_step, "risk_level", None) or "read_only"
                requires_confirmation = bool(
                    getattr(projected_step, "requires_confirmation", False)
                )
                read_only = (
                    getattr(projected_step, "side_effect", None)
                    == PlanSideEffect.READ_ONLY.value
                )
                active_step_id = self._safe_optional_preview_text(
                    getattr(projected_step, "step_id", None)
                )
                active_step_capability_id = self._safe_optional_preview_text(
                    getattr(projected_step, "capability_id", None)
                )
                active_step_name = self._safe_optional_preview_text(
                    getattr(projected_step, "display_name", None)
                )

        if not valid:
            return AppCommandPreview(
                input_text=input_text,
                normalized_text=normalized_text,
                registry_match_id=None,
                title_ru=None,
                category="planner",
                risk_level="read_only",
                read_only=True,
                voice_auto_allowed=False,
                requires_confirmation=False,
                requires_network=False,
                requires_ai_key=False,
                requires_privacy_check=False,
                app_ready=False,
                known_command=False,
                safe_summary_ru=(
                    "Planner preview rejected the text safely"
                    + (f": {error_code}" if error_code else ".")
                    + " No plan was created, replaced, executed, cancelled, or persisted."
                ),
            )

        summary_parts = [
            f"Planner command preview: {kind.value}.",
            "Preview is read-only and does not create, replace, execute, or cancel a plan.",
        ]
        if active is None and kind in {
            PlanParseStatus.SHOW,
            PlanParseStatus.EXECUTE,
            PlanParseStatus.CANCEL,
        }:
            summary_parts.append("Active plan: none.")
        elif status:
            summary_parts.append(f"Plan status: {status}.")
        if step_count is not None:
            summary_parts.append(f"Plan steps: {step_count}.")
        if requires_confirmation:
            summary_parts.append("Effective next step requires confirmation.")
        if kind == PlanParseStatus.EXECUTE and active_plan_id:
            summary_parts.append(f"Active plan id: {active_plan_id}.")
            summary_parts.append(f"Active plan status: {active_plan_status or 'none'}.")
            summary_parts.append("Operation id: none before execution.")
            if active_step_id:
                summary_parts.append(
                    f"Active step: {active_step_id} {active_step_capability_id or 'unknown'}."
                )

        return AppCommandPreview(
            input_text=input_text,
            normalized_text=normalized_text,
            registry_match_id="planner.general_multi_step",
            title_ru="General multi-step planner",
            category="planner",
            risk_level=risk_level,
            read_only=read_only,
            voice_auto_allowed=False,
            requires_confirmation=requires_confirmation,
            requires_network=False,
            requires_ai_key=False,
            requires_privacy_check=False,
            app_ready=True,
            known_command=True,
            safe_summary_ru=" ".join(summary_parts),
            active_plan_id=active_plan_id,
            active_plan_status=active_plan_status,
            active_step_id=active_step_id,
            active_step_capability_id=active_step_capability_id,
            active_step_name=active_step_name,
            operation_id=operation_id,
        )

    def handle_command(
        self,
        input_text: str,
        source: AppCommandSource,
        *,
        idempotency_key: str | None,
    ) -> AppCommandResult | None:
        language_code = self._language_code()
        kind = self._multi_step_planner.command_kind(input_text, language_code=language_code)
        normalized = normalize_control_text(input_text)
        active = self._multi_step_planner.snapshot()
        if (
            active is not None
            and active.status == PlanStatus.AWAITING_CONFIRMATION
            and normalized in {"да", "подтверждаю", "подтвердить", "yes"}
        ):
            execution = self._plan_executor.resume(active)
            if execution.snapshot is not None:
                self._multi_step_planner.set_status(
                    execution.status,
                    operation_id=execution.operation_id,
                    step_statuses={
                        step.step_id: step.status for step in execution.snapshot.steps
                    },
                    step_messages={
                        step.step_id: step.safe_message for step in execution.snapshot.steps
                    },
                    step_errors={
                        step.step_id: step.error_code for step in execution.snapshot.steps
                    },
                    current_step_id=execution.snapshot.current_step_id,
                    safe_message=execution.safe_message,
                )
            snapshot = self._multi_step_planner.snapshot() or execution.snapshot
            return self._app_result(
                input_text,
                source,
                snapshot,
                executed=True,
                message=execution.safe_message,
            )

        if (
            active is not None
            and active.status == PlanStatus.AWAITING_CONFIRMATION
            and normalized in {"отмена", "отмени", "нет", "cancel", "no"}
        ):
            execution = self._plan_executor.cancel(active)
            snapshot = execution.snapshot
            self._multi_step_planner.set_status(
                PlanStatus.CANCELLED,
                operation_id=execution.operation_id,
                current_step_id=None,
                safe_message=self._localized_text("План отменён.", "Plan cancelled."),
            )
            snapshot = self._multi_step_planner.snapshot() or snapshot
            return self._app_result(
                input_text,
                source,
                snapshot,
                executed=False,
                message=self._localized_text("План отменён.", "Plan cancelled."),
            )

        if kind == PlanParseStatus.NOT_PLANNER_COMMAND:
            return None
        if kind == PlanParseStatus.CREATED:
            parsed = self._multi_step_planner.create_from_text(
                input_text,
                language_code=language_code,
            )
            return self._app_result(
                input_text,
                source,
                parsed.snapshot,
                executed=False,
                ok=parsed.status == PlanParseStatus.CREATED,
                message=parsed.safe_message,
                error=parsed.safe_error_code,
            )
        if kind == PlanParseStatus.SHOW:
            snapshot = self._multi_step_planner.snapshot()
            message = (
                self._localized_text("Активного плана нет.", "There is no active plan.")
                if snapshot is None
                else snapshot.safe_message
            )
            return self._app_result(
                input_text,
                source,
                snapshot,
                executed=False,
                message=message,
            )
        if kind == PlanParseStatus.CANCEL:
            snapshot = self._multi_step_planner.snapshot()
            if snapshot is None:
                return self._app_result(
                    input_text,
                    source,
                    None,
                    executed=False,
                    message=self._localized_text(
                        "Активного плана нет.",
                        "There is no active plan.",
                    ),
                )
            execution = self._plan_executor.cancel(snapshot)
            updated = self._multi_step_planner.set_status(
                PlanStatus.CANCELLED,
                operation_id=execution.operation_id,
                current_step_id=None,
                safe_message=self._localized_text("План отменён.", "Plan cancelled."),
            )
            return self._app_result(
                input_text,
                source,
                updated,
                executed=False,
                message=self._localized_text("План отменён.", "Plan cancelled."),
            )
        if kind == PlanParseStatus.EXECUTE:
            snapshot = self._multi_step_planner.snapshot()
            if snapshot is None:
                return self._app_result(
                    input_text,
                    source,
                    None,
                    executed=False,
                    ok=False,
                    message=self._localized_text(
                        "Активного плана нет.",
                        "There is no active plan.",
                    ),
                    error="no_active_plan",
                )
            if snapshot.status in TERMINAL_PLAN_STATUSES:
                return self._app_result(
                    input_text,
                    source,
                    snapshot,
                    executed=False,
                    message=self._localized_text(
                        "Терминальный план не выполняется повторно.",
                        "A terminal plan is not executed again.",
                    ),
                    error="terminal_plan_not_reexecuted",
                )
            if snapshot.status == PlanStatus.AWAITING_CONFIRMATION:
                return self._app_result(
                    input_text,
                    source,
                    snapshot,
                    executed=False,
                    message=self._localized_text(
                        "Требуется явное подтверждение или отмена. Повтор execute plan не является подтверждением.",
                        "Explicit confirmation or cancellation is required. Repeating execute plan is not confirmation.",
                    ),
                    error="explicit_confirmation_required",
                )
            execution = self._plan_executor.start(
                snapshot,
                self._multi_step_planner.steps(),
                source=source.value,
                idempotency_key=idempotency_key,
            )
            if execution.snapshot is not None:
                updated = self._multi_step_planner.set_status(
                    execution.status,
                    operation_id=execution.operation_id,
                    step_statuses={
                        step.step_id: step.status for step in execution.snapshot.steps
                    },
                    step_messages={
                        step.step_id: step.safe_message for step in execution.snapshot.steps
                    },
                    step_errors={
                        step.step_id: step.error_code for step in execution.snapshot.steps
                    },
                    current_step_id=execution.snapshot.current_step_id,
                    safe_message=execution.safe_message,
                )
            else:
                updated = snapshot
            return self._app_result(
                input_text,
                source,
                updated,
                executed=True,
                message=execution.safe_message,
                error=execution.safe_error_code,
            )
        return None

    def _app_result(
        self,
        input_text: str,
        source: AppCommandSource,
        snapshot: PlanSnapshot | None,
        *,
        executed: bool,
        ok: bool = True,
        message: str | None = None,
        error: str | None = None,
    ) -> AppCommandResult:
        output = self._snapshot_text(snapshot, message=message)
        return AppCommandResult(
            ok=ok and error is None,
            input_text=input_text,
            output_text=output,
            source=source,
            registry_match_id="planner.general_multi_step",
            category="planner",
            risk_level="read_only" if not executed else "planner_controlled",
            executed=executed,
            requires_confirmation=bool(getattr(snapshot, "awaiting_confirmation", False)),
            network_may_be_used=False,
            response_executed_as_command=False,
            error=error,
            operation_id=getattr(snapshot, "operation_id", None),
            operation_status=getattr(getattr(snapshot, "status", None), "value", None),
            workflow_id=(
                "general_multi_step_plan"
                if getattr(snapshot, "operation_id", None)
                else None
            ),
            workflow_status=getattr(getattr(snapshot, "status", None), "value", None),
            current_step_id=getattr(snapshot, "current_step_id", None),
            current_step_name=None,
            completed_steps=tuple(
                step.step_id
                for step in getattr(snapshot, "steps", ())
                if step.status.value == "succeeded"
            ),
            total_steps=getattr(snapshot, "total_steps", None),
            progress_percent=getattr(snapshot, "progress_percent", None),
            awaiting_confirmation=bool(getattr(snapshot, "awaiting_confirmation", False)),
            user_message=message,
            plan_id=getattr(snapshot, "plan_id", None),
            plan_status=getattr(getattr(snapshot, "status", None), "value", None),
            plan_step_count=getattr(snapshot, "total_steps", None),
        )

    def _snapshot_text(self, snapshot: PlanSnapshot | None, *, message: str | None = None) -> str:
        if snapshot is None:
            return message or self._localized_text(
                "Активного плана нет.",
                "There is no active plan.",
            )
        lines = [
            message or snapshot.safe_message,
            f"plan_id: {snapshot.plan_id}",
            f"status: {snapshot.status.value}",
            f"operation_id: {snapshot.operation_id or 'none'}",
            f"steps: {snapshot.total_steps}",
            f"current_step: {snapshot.current_step_id or 'none'}",
            f"progress: {snapshot.progress_percent}",
            f"awaiting_confirmation: {'yes' if snapshot.awaiting_confirmation else 'no'}",
        ]
        for step in snapshot.steps:
            lines.append(
                f"{step.position}. {step.display_name} [{step.capability_id}] "
                f"{step.status.value}: {step.safe_message}"
            )
        return "\n".join(lines)

    def _safe_optional_preview_text(self, value: object) -> str | None:
        if value is None:
            return None
        text = self._safe_text_preview(str(value))
        return None if text == "<empty>" else text

    @staticmethod
    def _next_effective_step(snapshot: PlanSnapshot | None) -> PlanStepSnapshot | None:
        if snapshot is None or getattr(snapshot, "status", None) in TERMINAL_PLAN_STATUSES:
            return None
        steps = tuple(getattr(snapshot, "steps", ()) or ())
        current_step_id = getattr(snapshot, "current_step_id", None)
        if current_step_id:
            for step in steps:
                if step.step_id == current_step_id:
                    return step
            return None
        for step in steps:
            status_value = getattr(getattr(step, "status", None), "value", None)
            if status_value in {"succeeded", "cancelled", "skipped"}:
                continue
            return step
        return None
