"""Thin planner executor built on existing execution and workflow boundaries."""

from __future__ import annotations

from dataclasses import dataclass, field

from core.execution_coordinator import ExecutionCoordinator
from core.policy_boundary import PolicyDecisionBoundary
from planner.capability_registry import PlannerCapabilityRegistry
from planner.contracts import (
    PlanExecutionResult,
    PlanSnapshot,
    PlanStatus,
    PlanStepDefinition,
    PlanStepStatus,
)
from workflows.contracts import WorkflowStepDefinition, WorkflowStepResult, WorkflowStepStatus
from workflows.runner import WorkflowExecutableStep, WorkflowRunner


@dataclass
class _ExecutionState:
    plan: PlanSnapshot
    calls: list[str] = field(default_factory=list)
    step_statuses: dict[str, PlanStepStatus] = field(default_factory=dict)
    step_messages: dict[str, str] = field(default_factory=dict)
    step_errors: dict[str, str | None] = field(default_factory=dict)


class PlanExecutor:
    def __init__(
        self,
        *,
        registry: PlannerCapabilityRegistry,
        execution_coordinator: ExecutionCoordinator,
        policy_boundary: PolicyDecisionBoundary,
    ):
        self.registry = registry
        self.execution_coordinator = execution_coordinator
        self.policy_boundary = policy_boundary
        self._runners: dict[str, WorkflowRunner[_ExecutionState]] = {}
        self._states: dict[str, _ExecutionState] = {}

    def start(self, plan: PlanSnapshot, steps, *, source: str, idempotency_key: str | None = None) -> PlanExecutionResult:
        if plan.status in {PlanStatus.SUCCEEDED, PlanStatus.FAILED, PlanStatus.CANCELLED, PlanStatus.BLOCKED}:
            return self._result(plan, "Terminal plan was not executed again.", "terminal_plan_not_reexecuted")
        fingerprint = self.execution_coordinator.create_request_fingerprint(
            source=source,
            text=plan.goal_summary,
            command_id="planner.execute",
            action_id=plan.plan_id,
        )
        registration = self.execution_coordinator.register(
            source=source,
            idempotency_key=idempotency_key or f"planner-{plan.plan_id}",
            request_fingerprint=fingerprint,
            command_id="planner.execute",
            action_id=plan.plan_id,
            metadata={"plan_id": plan.plan_id, "step_count": plan.total_steps},
        )
        if registration.conflict:
            return PlanExecutionResult(
                plan_id=plan.plan_id,
                operation_id=registration.operation.operation_id,
                status=PlanStatus.BLOCKED,
                completed_steps=0,
                total_steps=plan.total_steps,
                progress_percent=0,
                safe_message="Idempotency conflict. No plan step was executed.",
                safe_error_code="idempotency_conflict",
            )
        if registration.duplicate and plan.operation_id:
            return self.resume(plan)

        state = _ExecutionState(plan=plan)
        runner = self._build_runner(plan, steps)
        self._runners[plan.plan_id] = runner
        self._states[plan.plan_id] = state
        snapshot = runner.start(
            operation=registration.operation,
            state=state,
            token=registration.token,
            safe_metadata={"plan_id": plan.plan_id},
        )
        return self._from_workflow(plan, snapshot, state)

    def resume(self, plan: PlanSnapshot) -> PlanExecutionResult:
        if plan.plan_id not in self._runners or not plan.operation_id:
            return self._result(plan, "No running plan can be resumed.", "plan_not_resumable")
        snapshot = self._runners[plan.plan_id].resume(plan.operation_id)
        state = self._states[plan.plan_id]
        return self._from_workflow(plan, snapshot, state)

    def cancel(self, plan: PlanSnapshot) -> PlanExecutionResult:
        if plan.plan_id in self._runners and plan.operation_id:
            snapshot = self._runners[plan.plan_id].cancel(plan.operation_id, reason="plan_cancelled")
            state = self._states[plan.plan_id]
            return self._from_workflow(plan, snapshot, state)
        return PlanExecutionResult(
            plan_id=plan.plan_id,
            operation_id=plan.operation_id,
            status=PlanStatus.CANCELLED,
            completed_steps=plan.completed_steps,
            total_steps=plan.total_steps,
            progress_percent=plan.progress_percent,
            safe_message="Plan cancelled.",
        )

    def _build_runner(self, plan: PlanSnapshot, steps) -> WorkflowRunner[_ExecutionState]:
        workflow_steps = []
        step_by_id = {step.step_id: step for step in steps}
        for step in steps:
            capability = self.registry.get(step.capability_id)

            def make_action(step_id: str, capability_id: str, arguments):
                def action(state: _ExecutionState, token):
                    token.raise_if_cancelled()
                    state.step_statuses[step_id] = PlanStepStatus.RUNNING
                    state.calls.append(capability_id)
                    try:
                        result = self.registry.get(capability_id).executor(arguments)
                    except Exception:
                        state.step_statuses[step_id] = PlanStepStatus.FAILED
                        state.step_errors[step_id] = "planner_capability_failed"
                        state.step_messages[step_id] = "Plan step failed safely."
                        return WorkflowStepResult(
                            step_id=step_id,
                            status=WorkflowStepStatus.FAILED,
                            safe_message="Plan step failed safely.",
                            error_code="planner_capability_failed",
                        )
                    message = getattr(result, "safe_message", None) or getattr(result, "output_text", None) or "Plan step completed."
                    state.step_statuses[step_id] = PlanStepStatus.SUCCEEDED
                    state.step_messages[step_id] = str(message)
                    return WorkflowStepResult(
                        step_id=step_id,
                        status=WorkflowStepStatus.SUCCEEDED,
                        safe_message=str(message),
                    )

                return action

            def make_policy(step_id: str):
                def policy(state: _ExecutionState, confirmation_present: bool):
                    plan_step = step_by_id[step_id]
                    return self.registry.get(plan_step.capability_id).policy_factory(
                        plan_step.arguments,
                        confirmation_present,
                    )

                return policy

            workflow_steps.append(
                WorkflowExecutableStep(
                    WorkflowStepDefinition(
                        step.step_id,
                        capability.descriptor.display_name(plan.language_code),
                        requires_confirmation=step.requires_confirmation,
                    ),
                    make_action(step.step_id, step.capability_id, step.arguments),
                    make_policy(step.step_id),
                )
            )
        return WorkflowRunner(
            workflow_id="general_multi_step_plan",
            steps=tuple(workflow_steps),
            execution_coordinator=self.execution_coordinator,
            policy_boundary=self.policy_boundary,
        )

    def _from_workflow(self, plan, workflow, state: _ExecutionState) -> PlanExecutionResult:
        status = {
            "running": PlanStatus.RUNNING,
            "awaiting_confirmation": PlanStatus.AWAITING_CONFIRMATION,
            "succeeded": PlanStatus.SUCCEEDED,
            "failed": PlanStatus.FAILED,
            "cancelled": PlanStatus.CANCELLED,
            "denied": PlanStatus.BLOCKED,
        }.get(workflow.status.value, PlanStatus.RUNNING)
        for step in plan.steps:
            if step.step_id in workflow.completed_step_ids:
                state.step_statuses[step.step_id] = PlanStepStatus.SUCCEEDED
            elif workflow.current_step_id == step.step_id and workflow.awaiting_confirmation:
                state.step_statuses[step.step_id] = PlanStepStatus.AWAITING_CONFIRMATION
            elif status in {PlanStatus.FAILED, PlanStatus.BLOCKED} and state.step_statuses.get(step.step_id) is None:
                state.step_statuses[step.step_id] = PlanStepStatus.SKIPPED
            elif status == PlanStatus.CANCELLED and state.step_statuses.get(step.step_id) is None:
                state.step_statuses[step.step_id] = PlanStepStatus.CANCELLED
        if status == PlanStatus.BLOCKED and workflow.current_step_id:
            state.step_statuses[workflow.current_step_id] = PlanStepStatus.BLOCKED
            state.step_errors[workflow.current_step_id] = "policy_denied"
        message = self._message(plan.language_code, status, workflow.current_step_index + 1, workflow.total_steps)
        snapshot = self._snapshot_from_state(
            plan,
            operation_id=workflow.operation_id,
            status=status,
            current_step_id=workflow.current_step_id,
            state=state,
            message=message,
        )
        return PlanExecutionResult(
            plan_id=plan.plan_id,
            operation_id=workflow.operation_id,
            status=status,
            completed_steps=snapshot.completed_steps,
            total_steps=snapshot.total_steps,
            progress_percent=snapshot.progress_percent,
            safe_message=message,
            safe_error_code="policy_denied" if status == PlanStatus.BLOCKED else None,
            snapshot=snapshot,
        )

    def _snapshot_from_state(self, plan, *, operation_id, status, current_step_id, state, message):
        from planner.multi_step_planner import _PlanState

        plan_state = _PlanState(
            plan_id=plan.plan_id,
            goal_summary=plan.goal_summary,
            language_code=plan.language_code,
            steps=tuple(
                PlanStepDefinition(
                    step_id=s.step_id,
                    position=s.position,
                    capability_id=s.capability_id,
                    arguments={},
                    safe_argument_summary="",
                    requires_confirmation=s.requires_confirmation,
                    risk_level="",
                )
                for s in plan.steps
            ),
            registry=self.registry,
            status=status,
        )
        plan_state.operation_id = operation_id
        plan_state.current_step_id = current_step_id
        plan_state.step_statuses.update(state.step_statuses)
        plan_state.step_messages.update(state.step_messages)
        plan_state.step_errors.update(state.step_errors)
        return plan_state.snapshot(message=message)

    def _result(self, plan, message, error):
        return PlanExecutionResult(
            plan_id=plan.plan_id,
            operation_id=plan.operation_id,
            status=plan.status,
            completed_steps=plan.completed_steps,
            total_steps=plan.total_steps,
            progress_percent=plan.progress_percent,
            safe_message=message,
            safe_error_code=error,
            snapshot=plan,
        )

    @staticmethod
    def _message(language_code: str, status: PlanStatus, index: int, total: int) -> str:
        if status == PlanStatus.AWAITING_CONFIRMATION:
            return "Confirmation required for the current plan step." if language_code == "en-US" else "Требуется подтверждение текущего этапа плана."
        if status == PlanStatus.SUCCEEDED:
            return "Plan completed." if language_code == "en-US" else "План завершён."
        if status == PlanStatus.CANCELLED:
            return "Plan cancelled." if language_code == "en-US" else "План отменён."
        if status in {PlanStatus.FAILED, PlanStatus.BLOCKED}:
            return "Plan stopped safely." if language_code == "en-US" else "План безопасно остановлен."
        return f"Running step {index} of {total}." if language_code == "en-US" else f"Выполняется этап {index} из {total}."
