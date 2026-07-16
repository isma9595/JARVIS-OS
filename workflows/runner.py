"""Small in-memory linear workflow runner.

The runner owns ordered step progression only. Operation registration,
idempotency, policy decisions, and journal persistence stay in the existing
core boundaries passed to the runner.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from threading import RLock
from typing import Any, Generic, TypeVar

from core.execution_coordinator import CancellationToken, ExecutionCoordinator, OperationCancelled
from core.execution_journal import ExecutionOperation, ExecutionStatus, TERMINAL_EXECUTION_STATUSES
from core.policy_boundary import PolicyDecisionBoundary, PolicyDecisionType, PolicyRequest
from workflows.contracts import (
    TERMINAL_WORKFLOW_STATUSES,
    WorkflowRunSnapshot,
    WorkflowRunStatus,
    WorkflowStepDefinition,
    WorkflowStepResult,
    WorkflowStepStatus,
    safe_workflow_metadata,
)


StateT = TypeVar("StateT")
StepAction = Callable[[StateT, CancellationToken], WorkflowStepResult | None]
PolicyFactory = Callable[[StateT, bool], PolicyRequest | None]


class WorkflowDefinitionError(ValueError):
    pass


@dataclass(frozen=True)
class WorkflowExecutableStep(Generic[StateT]):
    definition: WorkflowStepDefinition
    action: StepAction[StateT]
    policy_request: PolicyFactory[StateT] | None = None


@dataclass
class _WorkflowRun(Generic[StateT]):
    workflow_id: str
    operation_id: str
    state: StateT
    steps: tuple[WorkflowExecutableStep[StateT], ...]
    token: CancellationToken
    current_index: int = 0
    status: WorkflowRunStatus = WorkflowRunStatus.CREATED
    step_statuses: dict[str, WorkflowStepStatus] = field(default_factory=dict)
    completed_step_ids: list[str] = field(default_factory=list)
    results: dict[str, WorkflowStepResult] = field(default_factory=dict)
    safe_metadata: dict[str, object] = field(default_factory=dict)


class WorkflowRunner(Generic[StateT]):
    """Execute one declared linear sequence per operation id."""

    def __init__(
        self,
        *,
        workflow_id: str,
        steps: tuple[WorkflowExecutableStep[StateT], ...],
        execution_coordinator: ExecutionCoordinator,
        policy_boundary: PolicyDecisionBoundary,
    ):
        if not steps:
            raise WorkflowDefinitionError("workflow must declare at least one step")
        step_ids = [step.definition.step_id for step in steps]
        if any(not step_id for step_id in step_ids):
            raise WorkflowDefinitionError("workflow step ids must be non-empty")
        if len(set(step_ids)) != len(step_ids):
            raise WorkflowDefinitionError("workflow step ids must be unique")
        self.workflow_id = str(workflow_id)
        self.steps = tuple(steps)
        self.execution_coordinator = execution_coordinator
        self.policy_boundary = policy_boundary
        self._runs: dict[str, _WorkflowRun[StateT]] = {}
        self._lock = RLock()

    def start(
        self,
        *,
        operation: ExecutionOperation,
        state: StateT,
        token: CancellationToken,
        safe_metadata: dict[str, object] | None = None,
    ) -> WorkflowRunSnapshot:
        with self._lock:
            if operation.operation_id in self._runs:
                return self.snapshot(operation.operation_id)
            run = _WorkflowRun(
                workflow_id=self.workflow_id,
                operation_id=operation.operation_id,
                state=state,
                steps=self.steps,
                token=token,
                safe_metadata=dict(safe_workflow_metadata(safe_metadata)),
            )
            self._runs[operation.operation_id] = run
            return self._advance(run, confirmation_present=False)

    def resume(self, operation_id: str) -> WorkflowRunSnapshot:
        with self._lock:
            run = self._get_run(operation_id)
            if run.status in TERMINAL_WORKFLOW_STATUSES:
                return self._snapshot(run)
            if run.status != WorkflowRunStatus.AWAITING_CONFIRMATION:
                return self._snapshot(run)
            return self._advance(run, confirmation_present=True)

    def cancel(self, operation_id: str, *, reason: str = "workflow_cancelled") -> WorkflowRunSnapshot:
        with self._lock:
            run = self._get_run(operation_id)
            if run.status in TERMINAL_WORKFLOW_STATUSES:
                return self._snapshot(run)
            if run.current_index < len(run.steps):
                step_id = run.steps[run.current_index].definition.step_id
                run.step_statuses[step_id] = WorkflowStepStatus.CANCELLED
            run.status = WorkflowRunStatus.CANCELLED
            self.execution_coordinator.cancel(operation_id, reason=reason)
            return self._snapshot(run)

    def snapshot(self, operation_id: str) -> WorkflowRunSnapshot:
        with self._lock:
            return self._snapshot(self._get_run(operation_id))

    def latest_failed_result(self, operation_id: str) -> WorkflowStepResult | None:
        with self._lock:
            run = self._get_run(operation_id)
            for result in reversed(tuple(run.results.values())):
                if result.status == WorkflowStepStatus.FAILED:
                    return result
            return None

    def _advance(
        self,
        run: _WorkflowRun[StateT],
        *,
        confirmation_present: bool,
    ) -> WorkflowRunSnapshot:
        operation = self.execution_coordinator.journal.get(run.operation_id)
        if operation is not None and operation.status in TERMINAL_EXECUTION_STATUSES:
            run.status = _workflow_status_from_execution(operation.status)
            return self._snapshot(run)

        run.status = WorkflowRunStatus.RUNNING
        self.execution_coordinator.mark_running(run.operation_id)
        while run.current_index < len(run.steps):
            if run.token.cancelled:
                run.status = WorkflowRunStatus.CANCELLED
                self.execution_coordinator.cancel(run.operation_id)
                return self._snapshot(run)

            step = run.steps[run.current_index]
            step_id = step.definition.step_id
            if step_id in run.completed_step_ids:
                run.current_index += 1
                continue
            policy = (
                step.policy_request(run.state, confirmation_present)
                if step.policy_request is not None
                else None
            )
            if policy is not None:
                decision = self.policy_boundary.evaluate(policy)
                self.execution_coordinator.set_policy_decision(
                    run.operation_id,
                    decision.to_dict(),
                )
                if decision.decision == PolicyDecisionType.DENY:
                    result = WorkflowStepResult(
                        step_id=step_id,
                        status=WorkflowStepStatus.FAILED,
                        safe_message=decision.user_message,
                        error_code="policy_denied",
                    )
                    run.results[step_id] = result
                    run.step_statuses[step_id] = WorkflowStepStatus.FAILED
                    run.status = WorkflowRunStatus.DENIED
                    self.execution_coordinator.mark_denied(
                        run.operation_id,
                        policy_decision=decision.to_dict(),
                        error_code="workflow_policy_denied",
                    )
                    return self._snapshot(run)

            if step.definition.requires_confirmation and not confirmation_present:
                run.step_statuses[step_id] = WorkflowStepStatus.AWAITING_CONFIRMATION
                run.status = WorkflowRunStatus.AWAITING_CONFIRMATION
                self.execution_coordinator.mark_awaiting_confirmation(run.operation_id)
                return self._snapshot(run)

            run.step_statuses[step_id] = WorkflowStepStatus.RUNNING
            try:
                result = step.action(run.state, run.token)
            except OperationCancelled:
                run.step_statuses[step_id] = WorkflowStepStatus.CANCELLED
                run.status = WorkflowRunStatus.CANCELLED
                self.execution_coordinator.cancel(run.operation_id)
                return self._snapshot(run)
            except Exception:
                result = WorkflowStepResult(
                    step_id=step_id,
                    status=WorkflowStepStatus.FAILED,
                    safe_message="Шаг workflow безопасно завершился ошибкой.",
                    error_code="workflow_step_failed",
                )

            if result is None:
                result = WorkflowStepResult(
                    step_id=step_id,
                    status=WorkflowStepStatus.SUCCEEDED,
                    safe_message="Шаг workflow выполнен.",
                )
            run.results[step_id] = result
            run.step_statuses[step_id] = result.status
            if result.status != WorkflowStepStatus.SUCCEEDED:
                run.status = WorkflowRunStatus.CANCELLED if result.status == WorkflowStepStatus.CANCELLED else WorkflowRunStatus.FAILED
                if run.status == WorkflowRunStatus.CANCELLED:
                    self.execution_coordinator.cancel(run.operation_id)
                else:
                    self.execution_coordinator.mark_failed(
                        run.operation_id,
                        error_code=result.error_code or "workflow_step_failed",
                    )
                return self._snapshot(run)
            run.completed_step_ids.append(step_id)
            run.current_index += 1
            confirmation_present = False

        run.status = WorkflowRunStatus.SUCCEEDED
        self.execution_coordinator.mark_succeeded(run.operation_id, summary="workflow_succeeded")
        return self._snapshot(run)

    def _snapshot(self, run: _WorkflowRun[StateT]) -> WorkflowRunSnapshot:
        current = run.steps[run.current_index].definition if run.current_index < len(run.steps) else None
        verified = run.status == WorkflowRunStatus.SUCCEEDED and any(
            step.definition.verification_step and step.definition.step_id in run.completed_step_ids
            for step in run.steps
        )
        return WorkflowRunSnapshot(
            workflow_id=run.workflow_id,
            operation_id=run.operation_id,
            current_step_id=current.step_id if current else None,
            current_step_name=current.display_name_ru if current else None,
            current_step_index=min(run.current_index, len(run.steps)),
            total_steps=len(run.steps),
            completed_step_ids=tuple(run.completed_step_ids),
            status=run.status,
            progress_percent=self._progress_percent(run),
            awaiting_confirmation=run.status == WorkflowRunStatus.AWAITING_CONFIRMATION,
            cancellable=run.status not in TERMINAL_WORKFLOW_STATUSES,
            verified=verified,
            safe_metadata=run.safe_metadata,
        )

    def _progress_percent(self, run: _WorkflowRun[StateT]) -> int:
        if run.status == WorkflowRunStatus.SUCCEEDED:
            return 100
        return min(99, max(0, int((len(run.completed_step_ids) / len(run.steps)) * 100)))

    def _get_run(self, operation_id: str) -> _WorkflowRun[StateT]:
        try:
            return self._runs[operation_id]
        except KeyError as exc:
            raise KeyError(f"workflow operation not found: {operation_id}") from exc


def _workflow_status_from_execution(status: ExecutionStatus) -> WorkflowRunStatus:
    if status == ExecutionStatus.SUCCEEDED:
        return WorkflowRunStatus.SUCCEEDED
    if status == ExecutionStatus.CANCELLED:
        return WorkflowRunStatus.CANCELLED
    if status == ExecutionStatus.DENIED:
        return WorkflowRunStatus.DENIED
    return WorkflowRunStatus.FAILED
