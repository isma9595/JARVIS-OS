"""Small in-memory linear workflow runner.

The runner owns ordered step progression only. Operation registration,
idempotency, policy decisions, and journal persistence stay in the existing
core boundaries passed to the runner.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from hashlib import sha256
from threading import RLock
from typing import Any, Generic, TypeVar

from core.execution_coordinator import CancellationToken, ExecutionCoordinator, OperationCancelled
from core.execution_journal import (
    ExecutionOperation,
    ExecutionStatus,
    TERMINAL_EXECUTION_STATUSES,
    utc_now_iso,
)
from core.policy_boundary import PolicyDecisionBoundary, PolicyDecisionType, PolicyRequest
from workflows.contracts import (
    TERMINAL_WORKFLOW_STATUSES,
    WorkflowRunHistory,
    WorkflowRunHistoryState,
    WorkflowRunSnapshot,
    WorkflowRunStatus,
    WorkflowResumeEligibility,
    WorkflowResumeRejectionReason,
    WorkflowResumeResult,
    WorkflowResumeStatus,
    WorkflowStepHistory,
    WorkflowStepHistoryState,
    WorkflowStepDefinition,
    WorkflowStepResult,
    WorkflowStepStatus,
    safe_workflow_metadata,
    safe_workflow_text,
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
    created_at: str = ""
    started_at: str | None = None
    completed_at: str | None = None
    step_started_at: dict[str, str] = field(default_factory=dict)
    step_completed_at: dict[str, str] = field(default_factory=dict)


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
        self._resume_attempts: dict[str, str] = {}
        self._resuming_sources: set[str] = set()
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
                safe_metadata=self._run_metadata(safe_metadata),
                created_at=operation.created_at or utc_now_iso(),
            )
            self._runs[operation.operation_id] = run
            return self._advance(run, confirmation_present=False)

    def resume_eligibility(self, operation_id: str) -> WorkflowResumeEligibility:
        with self._lock:
            try:
                run = self._get_run(operation_id)
            except KeyError:
                return _resume_eligibility(
                    False,
                    operation_id,
                    reason=WorkflowResumeRejectionReason.NOT_FOUND,
                    message="Workflow run was not found.",
                )
            return self._resume_eligibility_for_run(run)

    def resume_from_run(
        self,
        *,
        source_operation_id: str,
        operation: ExecutionOperation,
        token: CancellationToken,
    ) -> WorkflowResumeResult:
        with self._lock:
            try:
                source = self._get_run(source_operation_id)
            except KeyError:
                return _resume_result(
                    False,
                    WorkflowResumeStatus.REJECTED,
                    source_operation_id,
                    reason=WorkflowResumeRejectionReason.NOT_FOUND,
                    message="Workflow run was not found.",
                )
            if source.operation_id in self._resuming_sources:
                return _resume_result(
                    False,
                    WorkflowResumeStatus.CONFLICT,
                    source.operation_id,
                    reason=WorkflowResumeRejectionReason.ALREADY_RESUMING,
                    message="Workflow run is already being resumed.",
                )
            if source.operation_id in self._resume_attempts:
                return _resume_result(
                    False,
                    WorkflowResumeStatus.CONFLICT,
                    source.operation_id,
                    resumed_run_id=self._resume_attempts[source.operation_id],
                    reason=WorkflowResumeRejectionReason.ALREADY_RESUMED,
                    message="Workflow run already has a resumed attempt.",
                )
            eligibility = self._resume_eligibility_for_run(source)
            if not eligibility.eligible:
                return _resume_result(
                    False,
                    WorkflowResumeStatus.REJECTED,
                    source.operation_id,
                    reason=eligibility.reason,
                    message=eligibility.safe_message,
                )
            if operation.operation_id in self._runs:
                return _resume_result(
                    False,
                    WorkflowResumeStatus.CONFLICT,
                    source.operation_id,
                    resumed_run_id=operation.operation_id,
                    reason=WorkflowResumeRejectionReason.CONCURRENT_RESUME_CONFLICT,
                    message="Resume attempt already exists.",
                )

            self._resuming_sources.add(source.operation_id)
            self._resume_attempts[source.operation_id] = operation.operation_id
            try:
                resumed = _WorkflowRun(
                    workflow_id=self.workflow_id,
                    operation_id=operation.operation_id,
                    state=source.state,
                    steps=self.steps,
                    token=token,
                    current_index=eligibility.resume_step_index or 0,
                    completed_step_ids=list(source.completed_step_ids),
                    results=dict(source.results),
                    step_statuses=dict(source.step_statuses),
                    step_started_at=dict(source.step_started_at),
                    step_completed_at=dict(source.step_completed_at),
                    safe_metadata=self._resume_metadata(source, eligibility, operation),
                    created_at=operation.created_at or utc_now_iso(),
                )
                self._runs[operation.operation_id] = resumed
                self._record_resume_metadata(
                    source_run_id=source.operation_id,
                    resumed_run_id=operation.operation_id,
                    resume_step_id=eligibility.resume_step_id,
                    resume_step_index=eligibility.resume_step_index,
                    status=WorkflowResumeStatus.STARTED,
                    reason=WorkflowResumeRejectionReason.NONE,
                )
                self._advance(resumed, confirmation_present=True)
                return _resume_result(
                    True,
                    WorkflowResumeStatus.STARTED,
                    source.operation_id,
                    resumed_run_id=operation.operation_id,
                    resume_step_id=eligibility.resume_step_id,
                    resume_step_index=eligibility.resume_step_index,
                    execution_started=True,
                    message="Workflow resume started.",
                )
            except Exception:
                self._runs.pop(operation.operation_id, None)
                self._resume_attempts.pop(source.operation_id, None)
                self._record_resume_metadata(
                    source_run_id=source.operation_id,
                    resumed_run_id=operation.operation_id,
                    resume_step_id=eligibility.resume_step_id,
                    resume_step_index=eligibility.resume_step_index,
                    status=WorkflowResumeStatus.FAILED,
                    reason=WorkflowResumeRejectionReason.LAUNCH_FAILED,
                )
                self.execution_coordinator.mark_failed(
                    operation.operation_id,
                    error_code="workflow_resume_launch_failed",
                )
                return _resume_result(
                    False,
                    WorkflowResumeStatus.FAILED,
                    source.operation_id,
                    resumed_run_id=operation.operation_id,
                    resume_step_id=eligibility.resume_step_id,
                    resume_step_index=eligibility.resume_step_index,
                    reason=WorkflowResumeRejectionReason.LAUNCH_FAILED,
                    message="Workflow resume could not be started safely.",
                )
            finally:
                self._resuming_sources.discard(source.operation_id)

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
                run.step_started_at.setdefault(step_id, utc_now_iso())
                run.step_completed_at[step_id] = utc_now_iso()
            run.status = WorkflowRunStatus.CANCELLED
            run.completed_at = run.completed_at or utc_now_iso()
            self.execution_coordinator.cancel(operation_id, reason=reason)
            return self._snapshot_and_record(run)

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

    def run_history(self, operation_id: str) -> WorkflowRunHistory:
        with self._lock:
            return self._history(self._get_run(operation_id))

    def recent_run_histories(self, limit: int | None = 25) -> tuple[WorkflowRunHistory, ...]:
        with self._lock:
            runs = tuple(reversed(tuple(self._runs.values())))
            if limit is not None:
                runs = runs[: max(0, int(limit))]
            return tuple(self._history(run) for run in runs)

    def _advance(
        self,
        run: _WorkflowRun[StateT],
        *,
        confirmation_present: bool,
    ) -> WorkflowRunSnapshot:
        operation = self.execution_coordinator.journal.get(run.operation_id)
        if operation is not None and operation.status in TERMINAL_EXECUTION_STATUSES:
            run.status = _workflow_status_from_execution(operation.status)
            run.completed_at = run.completed_at or operation.updated_at or utc_now_iso()
            return self._snapshot(run)

        run.started_at = run.started_at or utc_now_iso()
        run.status = WorkflowRunStatus.RUNNING
        self.execution_coordinator.mark_running(run.operation_id)
        while run.current_index < len(run.steps):
            if run.token.cancelled:
                if run.current_index < len(run.steps):
                    step_id = run.steps[run.current_index].definition.step_id
                    run.step_statuses[step_id] = WorkflowStepStatus.CANCELLED
                    run.step_started_at.setdefault(step_id, utc_now_iso())
                    run.step_completed_at[step_id] = utc_now_iso()
                run.status = WorkflowRunStatus.CANCELLED
                run.completed_at = run.completed_at or utc_now_iso()
                self.execution_coordinator.cancel(run.operation_id)
                return self._snapshot_and_record(run)

            step = run.steps[run.current_index]
            step_id = step.definition.step_id
            if step_id in run.completed_step_ids:
                run.current_index += 1
                continue
            run.step_started_at.setdefault(step_id, utc_now_iso())
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
                    run.step_completed_at[step_id] = utc_now_iso()
                    run.status = WorkflowRunStatus.DENIED
                    run.completed_at = run.completed_at or utc_now_iso()
                    self.execution_coordinator.mark_denied(
                        run.operation_id,
                        policy_decision=decision.to_dict(),
                        error_code="workflow_policy_denied",
                    )
                    return self._snapshot_and_record(run)

            if step.definition.requires_confirmation and not confirmation_present:
                run.step_statuses[step_id] = WorkflowStepStatus.AWAITING_CONFIRMATION
                run.status = WorkflowRunStatus.AWAITING_CONFIRMATION
                self.execution_coordinator.mark_awaiting_confirmation(run.operation_id)
                return self._snapshot_and_record(run)

            run.step_statuses[step_id] = WorkflowStepStatus.RUNNING
            try:
                result = step.action(run.state, run.token)
            except OperationCancelled:
                run.step_statuses[step_id] = WorkflowStepStatus.CANCELLED
                run.status = WorkflowRunStatus.CANCELLED
                run.step_completed_at[step_id] = utc_now_iso()
                run.completed_at = run.completed_at or utc_now_iso()
                self.execution_coordinator.cancel(run.operation_id)
                return self._snapshot_and_record(run)
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
            if result.status in {
                WorkflowStepStatus.SUCCEEDED,
                WorkflowStepStatus.FAILED,
                WorkflowStepStatus.CANCELLED,
                WorkflowStepStatus.SKIPPED,
            }:
                run.step_completed_at[step_id] = utc_now_iso()
            if result.status != WorkflowStepStatus.SUCCEEDED:
                run.status = WorkflowRunStatus.CANCELLED if result.status == WorkflowStepStatus.CANCELLED else WorkflowRunStatus.FAILED
                run.completed_at = run.completed_at or utc_now_iso()
                if run.status == WorkflowRunStatus.CANCELLED:
                    self.execution_coordinator.cancel(run.operation_id)
                else:
                    self.execution_coordinator.mark_failed(
                        run.operation_id,
                        error_code=result.error_code or "workflow_step_failed",
                    )
                return self._snapshot_and_record(run)
            run.completed_step_ids.append(step_id)
            run.current_index += 1
            confirmation_present = False

        run.status = WorkflowRunStatus.SUCCEEDED
        run.completed_at = run.completed_at or utc_now_iso()
        self.execution_coordinator.mark_succeeded(run.operation_id, summary="workflow_succeeded")
        return self._snapshot_and_record(run)

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

    def _history(self, run: _WorkflowRun[StateT]) -> WorkflowRunHistory:
        steps = tuple(
            self._step_history(run, step, index)
            for index, step in enumerate(run.steps)
        )
        active = run.steps[run.current_index].definition if run.current_index < len(run.steps) else None
        failed = self._latest_non_success_result(run)
        safe_result = self._latest_success_message(run)
        eligibility = self._resume_eligibility_for_run(run)
        return WorkflowRunHistory(
            run_id=run.operation_id,
            operation_id=run.operation_id,
            workflow_id=run.workflow_id,
            workflow_name=safe_workflow_text(run.safe_metadata.get("workflow_name")),
            objective_summary=self._objective_summary(run),
            state=_run_history_state(run.status),
            created_at=run.created_at or "unknown",
            started_at=run.started_at,
            completed_at=run.completed_at,
            total_step_count=len(run.steps),
            completed_step_count=len(run.completed_step_ids),
            active_step_id=active.step_id if active else None,
            active_step_name=active.display_name_ru if active else None,
            safe_result_summary=safe_result,
            safe_failure_summary=(
                failed.safe_message if failed is not None else None
            ),
            cancelled=run.status == WorkflowRunStatus.CANCELLED,
            waiting_for_confirmation=run.status == WorkflowRunStatus.AWAITING_CONFIRMATION,
            steps=steps,
            metadata=run.safe_metadata,
            resume_eligible=eligibility.eligible,
            resume_rejection_reason=eligibility.reason,
            resume_step_id=eligibility.resume_step_id,
            resume_step_index=eligibility.resume_step_index,
            resumed_from_run_id=(
                str(run.safe_metadata.get("resume_source_run_id"))
                if run.safe_metadata.get("resume_source_run_id")
                else None
            ),
        )

    def _step_history(
        self,
        run: _WorkflowRun[StateT],
        step: WorkflowExecutableStep[StateT],
        index: int,
    ) -> WorkflowStepHistory:
        definition = step.definition
        result = run.results.get(definition.step_id)
        status = run.step_statuses.get(definition.step_id, WorkflowStepStatus.PENDING)
        safe_error = None
        safe_result = None
        if result is not None:
            if result.status == WorkflowStepStatus.SUCCEEDED:
                safe_result = result.safe_message
            else:
                safe_error = result.safe_message
        metadata: dict[str, object] = dict(definition.safe_metadata or {})
        if result is not None:
            metadata.update(dict(result.safe_output_metadata or {}))
        operation_type = metadata.get("operation_type") or metadata.get("action_id") or definition.step_id
        return WorkflowStepHistory(
            step_id=definition.step_id,
            step_index=index,
            display_name=definition.display_name_ru,
            operation_type=str(operation_type) if operation_type is not None else None,
            state=_step_history_state(status, result),
            started_at=run.step_started_at.get(definition.step_id),
            completed_at=run.step_completed_at.get(definition.step_id),
            safe_result_summary=safe_result,
            safe_error_summary=safe_error,
            requires_confirmation=definition.requires_confirmation or bool(
                result.requires_confirmation if result is not None else False
            ),
            preview=bool(metadata.get("preview") or metadata.get("dry_run")),
            metadata=metadata,
        )

    def _snapshot_and_record(self, run: _WorkflowRun[StateT]) -> WorkflowRunSnapshot:
        self._record_journal_workflow_metadata(run)
        return self._snapshot(run)

    def _record_journal_workflow_metadata(self, run: _WorkflowRun[StateT]) -> None:
        operation = self.execution_coordinator.journal.get(run.operation_id)
        if operation is None:
            return
        metadata = dict(operation.metadata or {})
        active = run.steps[run.current_index].definition if run.current_index < len(run.steps) else None
        metadata.update(
            {
                "workflow_run_id": run.operation_id,
                "workflow_id": run.workflow_id,
                "workflow_state": _run_history_state(run.status).value,
                "workflow_current_step_id": active.step_id if active else None,
                "workflow_total_steps": len(run.steps),
                "workflow_completed_steps": len(run.completed_step_ids),
            }
        )
        for key in (
            "resume_source_run_id",
            "resume_start_step_id",
            "resume_start_step_index",
            "resume_attempt",
        ):
            if key in run.safe_metadata:
                metadata[key] = run.safe_metadata[key]
        self.execution_coordinator.journal.update(run.operation_id, metadata=metadata)

    def _run_metadata(self, metadata: dict[str, object] | None) -> dict[str, object]:
        safe = dict(safe_workflow_metadata(metadata))
        safe["workflow_definition_fingerprint"] = self._definition_fingerprint()
        return safe

    def _resume_metadata(
        self,
        source: _WorkflowRun[StateT],
        eligibility: WorkflowResumeEligibility,
        operation: ExecutionOperation,
    ) -> dict[str, object]:
        metadata = dict(source.safe_metadata)
        metadata.update(
            {
                "resume_attempt": True,
                "resume_source_run_id": source.operation_id,
                "resume_start_step_id": eligibility.resume_step_id or "",
                "resume_start_step_index": eligibility.resume_step_index
                if eligibility.resume_step_index is not None
                else "",
                "resumed_run_id": operation.operation_id,
                "workflow_definition_fingerprint": self._definition_fingerprint(),
            }
        )
        return dict(safe_workflow_metadata(metadata))

    def _definition_fingerprint(self) -> str:
        payload = "|".join(
            (
                self.workflow_id,
                *(
                    ":".join(
                        (
                            step.definition.step_id,
                            "confirm" if step.definition.requires_confirmation else "no_confirm",
                            "resumable" if step.definition.resumable else "non_resumable",
                        )
                    )
                    for step in self.steps
                ),
            )
        )
        return "sha256:" + sha256(payload.encode("utf-8")).hexdigest()

    def _resume_eligibility_for_run(
        self,
        run: _WorkflowRun[StateT],
    ) -> WorkflowResumeEligibility:
        if run.operation_id in self._resuming_sources:
            return _resume_eligibility(
                False,
                run.operation_id,
                reason=WorkflowResumeRejectionReason.ALREADY_RESUMING,
                message="Workflow run is already being resumed.",
            )
        if run.operation_id in self._resume_attempts:
            return _resume_eligibility(
                False,
                run.operation_id,
                reason=WorkflowResumeRejectionReason.ALREADY_RESUMED,
                message="Workflow run already has a resumed attempt.",
            )
        if not isinstance(run.status, WorkflowRunStatus):
            return _resume_eligibility(
                False,
                run.operation_id,
                reason=WorkflowResumeRejectionReason.MALFORMED_STATE,
                message="Workflow run state is not resumable.",
            )
        if run.status == WorkflowRunStatus.SUCCEEDED:
            return _resume_eligibility(
                False,
                run.operation_id,
                reason=WorkflowResumeRejectionReason.ALREADY_COMPLETED,
                message="Completed workflow runs cannot be resumed.",
            )
        if run.status in {
            WorkflowRunStatus.CREATED,
            WorkflowRunStatus.RUNNING,
            WorkflowRunStatus.AWAITING_CONFIRMATION,
        }:
            return _resume_eligibility(
                False,
                run.operation_id,
                reason=WorkflowResumeRejectionReason.ACTIVE_RUN,
                message="Active workflow runs cannot be resumed.",
            )
        if run.status != WorkflowRunStatus.FAILED:
            return _resume_eligibility(
                False,
                run.operation_id,
                reason=WorkflowResumeRejectionReason.CONTINUATION_STATE_UNAVAILABLE,
                message="Workflow run does not have a safe continuation state.",
            )
        if not run.steps:
            return _resume_eligibility(
                False,
                run.operation_id,
                reason=WorkflowResumeRejectionReason.WORKFLOW_DEFINITION_MISSING,
                message="Workflow definition is unavailable.",
            )
        if run.safe_metadata.get("workflow_definition_fingerprint") != self._definition_fingerprint():
            return _resume_eligibility(
                False,
                run.operation_id,
                reason=WorkflowResumeRejectionReason.WORKFLOW_DEFINITION_INCOMPATIBLE,
                message="Workflow definition is not compatible with the recorded run.",
            )
        resume_index = self._first_unfinished_step_index(run)
        if resume_index is None:
            return _resume_eligibility(
                False,
                run.operation_id,
                reason=WorkflowResumeRejectionReason.NO_UNFINISHED_STEPS,
                message="Workflow run has no unfinished steps.",
            )
        step = run.steps[resume_index]
        step_id = step.definition.step_id
        status = run.step_statuses.get(step_id, WorkflowStepStatus.PENDING)
        if not isinstance(status, WorkflowStepStatus):
            return _resume_eligibility(
                False,
                run.operation_id,
                reason=WorkflowResumeRejectionReason.UNKNOWN_STEP_STATE,
                message="Workflow step state is not resumable.",
            )
        if status not in {WorkflowStepStatus.FAILED, WorkflowStepStatus.PENDING}:
            return _resume_eligibility(
                False,
                run.operation_id,
                reason=WorkflowResumeRejectionReason.CONTINUATION_STATE_UNAVAILABLE,
                message="Workflow step does not have a safe continuation state.",
            )
        if not step.definition.resumable:
            return _resume_eligibility(
                False,
                run.operation_id,
                reason=WorkflowResumeRejectionReason.NON_RESUMABLE_STEP,
                message="Workflow step is not resumable.",
            )
        return _resume_eligibility(
            True,
            run.operation_id,
            resume_step_id=step_id,
            resume_step_index=resume_index,
            message="Workflow run can be resumed from the first unfinished step.",
        )

    def _first_unfinished_step_index(self, run: _WorkflowRun[StateT]) -> int | None:
        completed = set(run.completed_step_ids)
        for index, step in enumerate(run.steps):
            if step.definition.step_id not in completed:
                return index
        return None

    def _record_resume_metadata(
        self,
        *,
        source_run_id: str,
        resumed_run_id: str | None,
        resume_step_id: str | None,
        resume_step_index: int | None,
        status: WorkflowResumeStatus,
        reason: WorkflowResumeRejectionReason,
    ) -> None:
        operation = self.execution_coordinator.journal.get(resumed_run_id or "")
        if operation is None:
            return
        metadata = dict(operation.metadata or {})
        metadata.update(
            {
                "workflow_resume_source_run_id": source_run_id,
                "workflow_resume_run_id": resumed_run_id or "",
                "workflow_resume_start_step_id": resume_step_id or "",
                "workflow_resume_start_step_index": (
                    resume_step_index if resume_step_index is not None else ""
                ),
                "workflow_resume_status": status.value,
                "workflow_resume_rejection_reason": reason.value,
            }
        )
        self.execution_coordinator.journal.update(operation.operation_id, metadata=metadata)

    def _objective_summary(self, run: _WorkflowRun[StateT]) -> str:
        for key in ("objective_summary", "objective", "input_preview", "request_summary"):
            value = run.safe_metadata.get(key)
            if value:
                return safe_workflow_text(value, max_length=220)
        return run.workflow_id

    def _latest_non_success_result(self, run: _WorkflowRun[StateT]) -> WorkflowStepResult | None:
        for result in reversed(tuple(run.results.values())):
            if result.status != WorkflowStepStatus.SUCCEEDED:
                return result
        return None

    def _latest_success_message(self, run: _WorkflowRun[StateT]) -> str | None:
        if run.status != WorkflowRunStatus.SUCCEEDED:
            return None
        for result in reversed(tuple(run.results.values())):
            if result.status == WorkflowStepStatus.SUCCEEDED:
                return result.safe_message
        return "workflow_succeeded"


def _workflow_status_from_execution(status: ExecutionStatus) -> WorkflowRunStatus:
    if status == ExecutionStatus.SUCCEEDED:
        return WorkflowRunStatus.SUCCEEDED
    if status == ExecutionStatus.CANCELLED:
        return WorkflowRunStatus.CANCELLED
    if status == ExecutionStatus.DENIED:
        return WorkflowRunStatus.DENIED
    return WorkflowRunStatus.FAILED


def _run_history_state(status: WorkflowRunStatus) -> WorkflowRunHistoryState:
    states = {
        WorkflowRunStatus.CREATED: WorkflowRunHistoryState.PENDING,
        WorkflowRunStatus.RUNNING: WorkflowRunHistoryState.RUNNING,
        WorkflowRunStatus.AWAITING_CONFIRMATION: WorkflowRunHistoryState.WAITING_FOR_CONFIRMATION,
        WorkflowRunStatus.SUCCEEDED: WorkflowRunHistoryState.COMPLETED,
        WorkflowRunStatus.FAILED: WorkflowRunHistoryState.FAILED,
        WorkflowRunStatus.CANCELLED: WorkflowRunHistoryState.CANCELLED,
        WorkflowRunStatus.DENIED: WorkflowRunHistoryState.BLOCKED,
    }
    try:
        return states.get(status, WorkflowRunHistoryState.UNKNOWN)
    except TypeError:
        return WorkflowRunHistoryState.UNKNOWN


def _step_history_state(
    status: WorkflowStepStatus,
    result: WorkflowStepResult | None,
) -> WorkflowStepHistoryState:
    if result is not None and result.error_code == "policy_denied":
        return WorkflowStepHistoryState.BLOCKED
    states = {
        WorkflowStepStatus.PENDING: WorkflowStepHistoryState.PENDING,
        WorkflowStepStatus.RUNNING: WorkflowStepHistoryState.RUNNING,
        WorkflowStepStatus.AWAITING_CONFIRMATION: WorkflowStepHistoryState.WAITING_FOR_CONFIRMATION,
        WorkflowStepStatus.SUCCEEDED: WorkflowStepHistoryState.COMPLETED,
        WorkflowStepStatus.FAILED: WorkflowStepHistoryState.FAILED,
        WorkflowStepStatus.CANCELLED: WorkflowStepHistoryState.CANCELLED,
        WorkflowStepStatus.SKIPPED: WorkflowStepHistoryState.SKIPPED,
    }
    try:
        return states.get(status, WorkflowStepHistoryState.UNKNOWN)
    except TypeError:
        return WorkflowStepHistoryState.UNKNOWN


def _resume_eligibility(
    eligible: bool,
    source_run_id: str,
    *,
    resume_step_id: str | None = None,
    resume_step_index: int | None = None,
    reason: WorkflowResumeRejectionReason = WorkflowResumeRejectionReason.NONE,
    message: str,
) -> WorkflowResumeEligibility:
    return WorkflowResumeEligibility(
        eligible=eligible,
        source_run_id=source_run_id,
        resume_step_id=resume_step_id,
        resume_step_index=resume_step_index,
        reason=reason if not eligible else WorkflowResumeRejectionReason.NONE,
        safe_message=message,
    )


def _resume_result(
    ok: bool,
    status: WorkflowResumeStatus,
    source_run_id: str,
    *,
    resumed_run_id: str | None = None,
    resume_step_id: str | None = None,
    resume_step_index: int | None = None,
    execution_started: bool = False,
    reason: WorkflowResumeRejectionReason = WorkflowResumeRejectionReason.NONE,
    message: str,
) -> WorkflowResumeResult:
    return WorkflowResumeResult(
        ok=ok,
        status=status,
        source_run_id=source_run_id,
        resumed_run_id=resumed_run_id,
        resume_step_id=resume_step_id,
        resume_step_index=resume_step_index,
        execution_started=execution_started,
        rejection_reason=reason if not ok else WorkflowResumeRejectionReason.NONE,
        safe_message=message,
    )
