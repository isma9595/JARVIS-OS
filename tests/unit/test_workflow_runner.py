from dataclasses import asdict, dataclass

import pytest

from core.execution_coordinator import ExecutionCoordinator
from core.policy_boundary import PolicyDecision, PolicyDecisionType, PolicyRequest
from workflows.contracts import (
    WorkflowRunHistory,
    WorkflowRunHistoryState,
    WorkflowResumeRejectionReason,
    WorkflowResumeStatus,
    WorkflowStepDefinition,
    WorkflowStepHistoryState,
    WorkflowStepResult,
    WorkflowStepStatus,
)
from workflows.runner import WorkflowDefinitionError, WorkflowExecutableStep, WorkflowRunner


@dataclass
class RunnerState:
    calls: list[str]
    writes: int = 0


class AllowPolicy:
    def evaluate(self, request):
        return PolicyDecision(
            decision=PolicyDecisionType.ALLOW,
            reason_codes=("test_allow",),
            required_capabilities=request.required_capabilities,
            requires_confirmation=False,
            user_message="allowed",
            safe_to_execute=True,
        )


class DenyPolicy:
    def evaluate(self, request):
        return PolicyDecision(
            decision=PolicyDecisionType.DENY,
            reason_codes=("test_deny",),
            required_capabilities=request.required_capabilities,
            requires_confirmation=False,
            user_message="denied safely",
            safe_to_execute=False,
        )


def operation(coordinator: ExecutionCoordinator):
    registration = coordinator.register(
        source="test",
        idempotency_key=None,
        request_fingerprint="fingerprint",
        command_id="workflow.test",
    )
    return registration.operation, registration.token


def step(step_id, *, confirm=False, verify=False, fail=False, policy=False):
    def action(state: RunnerState, token):
        token.raise_if_cancelled()
        state.calls.append(step_id)
        if step_id == "write":
            state.writes += 1
        if fail:
            raise RuntimeError("api key sk-test-1234567890secret")
        return WorkflowStepResult(
            step_id=step_id,
            status=WorkflowStepStatus.SUCCEEDED,
            safe_message="ok",
            safe_output_metadata={
                "step": step_id,
                "document_contents": "secret full document text",
                "token": "sk-test-1234567890secret",
            },
        )

    def policy_request(state: RunnerState, confirmation_present: bool):
        return PolicyRequest(
            source="test",
            command_id="workflow.test",
            action_id=step_id,
            risk="confirmation_required" if confirm else "read_only",
            required_capabilities=("file_write",) if step_id == "write" else ("file_read",),
            confirmation_present=confirmation_present,
        )

    return WorkflowExecutableStep(
        WorkflowStepDefinition(
            step_id,
            f"Шаг {step_id}",
            requires_confirmation=confirm,
            verification_step=verify,
            safe_metadata={"api_key": "sk-test-1234567890secret"},
        ),
        action,
        policy_request if policy else None,
    )


def build_runner(coordinator, policy, steps):
    return WorkflowRunner(
        workflow_id="test_workflow",
        steps=tuple(steps),
        execution_coordinator=coordinator,
        policy_boundary=policy,
    )


def test_steps_run_in_order_and_success_finishes_at_100():
    coordinator = ExecutionCoordinator()
    op, token = operation(coordinator)
    state = RunnerState(calls=[])
    runner = build_runner(
        coordinator,
        AllowPolicy(),
        [step("one"), step("two"), step("verify", verify=True)],
    )

    snapshot = runner.start(operation=op, state=state, token=token)

    assert state.calls == ["one", "two", "verify"]
    assert snapshot.status.value == "succeeded"
    assert snapshot.progress_percent == 100
    assert snapshot.verified is True
    assert snapshot.completed_step_ids == ("one", "two", "verify")


def test_empty_and_duplicate_step_ids_are_rejected():
    coordinator = ExecutionCoordinator()
    with pytest.raises(WorkflowDefinitionError):
        build_runner(coordinator, AllowPolicy(), [])
    with pytest.raises(WorkflowDefinitionError):
        build_runner(coordinator, AllowPolicy(), [step("same"), step("same")])


def test_progress_bounds_and_pause_before_confirmation_without_completion():
    coordinator = ExecutionCoordinator()
    op, token = operation(coordinator)
    state = RunnerState(calls=[])
    runner = build_runner(coordinator, AllowPolicy(), [step("read"), step("write", confirm=True)])

    snapshot = runner.start(operation=op, state=state, token=token)

    assert snapshot.status.value == "awaiting_confirmation"
    assert snapshot.awaiting_confirmation is True
    assert snapshot.current_step_id == "write"
    assert snapshot.completed_step_ids == ("read",)
    assert "write" not in snapshot.completed_step_ids
    assert 0 <= snapshot.progress_percent < 100
    assert state.calls == ["read"]


def test_resume_uses_same_operation_and_executes_paused_step_once():
    coordinator = ExecutionCoordinator()
    op, token = operation(coordinator)
    state = RunnerState(calls=[])
    runner = build_runner(coordinator, AllowPolicy(), [step("read"), step("write", confirm=True)])
    first = runner.start(operation=op, state=state, token=token)

    resumed = runner.resume(first.operation_id)
    duplicate = runner.resume(first.operation_id)

    assert resumed.operation_id == first.operation_id
    assert resumed.status.value == "succeeded"
    assert duplicate.status.value == "succeeded"
    assert state.calls == ["read", "write"]
    assert state.writes == 1


def test_cancellation_is_scoped_and_terminal_cancel_is_noop():
    coordinator = ExecutionCoordinator()
    op1, token1 = operation(coordinator)
    op2 = coordinator.register(
        source="test",
        idempotency_key="other",
        request_fingerprint="other",
        command_id="workflow.test",
    )
    runner = build_runner(coordinator, AllowPolicy(), [step("read"), step("write", confirm=True)])
    first_state = RunnerState(calls=[])
    second_state = RunnerState(calls=[])
    runner.start(operation=op1, state=first_state, token=token1)
    runner.start(operation=op2.operation, state=second_state, token=op2.token)

    cancelled = runner.cancel(op1.operation_id)
    cancelled_again = runner.cancel(op1.operation_id)
    other = runner.snapshot(op2.operation.operation_id)

    assert cancelled.status.value == "cancelled"
    assert cancelled_again.status.value == "cancelled"
    assert other.status.value == "awaiting_confirmation"
    assert first_state.calls == ["read"]
    assert second_state.calls == ["read"]


def test_failed_step_denied_step_and_verification_order():
    coordinator = ExecutionCoordinator()
    op, token = operation(coordinator)
    failed_state = RunnerState(calls=[])
    runner = build_runner(coordinator, AllowPolicy(), [step("read"), step("boom", fail=True), step("later")])

    failed = runner.start(operation=op, state=failed_state, token=token)

    assert failed.status.value == "failed"
    assert failed_state.calls == ["read", "boom"]
    assert "later" not in failed_state.calls
    assert "sk-test" not in str(failed.to_dict())

    coordinator2 = ExecutionCoordinator()
    op2, token2 = operation(coordinator2)
    denied_state = RunnerState(calls=[])
    denied_runner = build_runner(
        coordinator2,
        DenyPolicy(),
        [step("read", policy=True), step("later")],
    )
    denied = denied_runner.start(operation=op2, state=denied_state, token=token2)

    assert denied.status.value == "denied"
    assert denied_state.calls == []

    coordinator3 = ExecutionCoordinator()
    op3, token3 = operation(coordinator3)
    verify_state = RunnerState(calls=[])
    verify_runner = build_runner(
        coordinator3,
        AllowPolicy(),
        [step("write"), step("verify", verify=True)],
    )
    verify_runner.start(operation=op3, state=verify_state, token=token3)
    assert verify_state.calls == ["write", "verify"]


def test_snapshots_are_serializable_immutable_and_redacted():
    coordinator = ExecutionCoordinator()
    op, token = operation(coordinator)
    state = RunnerState(calls=[])
    runner = build_runner(coordinator, AllowPolicy(), [step("read")])

    snapshot = runner.start(
        operation=op,
        state=state,
        token=token,
        safe_metadata={
            "document_contents": "complete document content",
            "credentials": "secret",
            "safe": "ok",
        },
    )
    data = snapshot.to_dict()

    assert data["status"] == "succeeded"
    assert data["safe_metadata"]["document_contents"] == "[REDACTED]"
    assert data["safe_metadata"]["credentials"] == "[REDACTED]"
    assert "complete document content" not in str(data)
    assert "secret" not in str(data)
    with pytest.raises(TypeError):
        snapshot.safe_metadata["new"] = "mutable"


def test_run_history_records_successful_steps_in_order_and_detached():
    coordinator = ExecutionCoordinator()
    op, token = operation(coordinator)
    state = RunnerState(calls=[])
    runner = build_runner(
        coordinator,
        AllowPolicy(),
        [step("one"), step("two"), step("verify", verify=True)],
    )

    snapshot = runner.start(
        operation=op,
        state=state,
        token=token,
        safe_metadata={
            "objective_summary": "Review report at C:/Users/User/private.txt",
            "workflow_name": "Safe workflow",
        },
    )
    history = runner.run_history(snapshot.operation_id)
    data = history.to_dict()

    assert history.run_id == op.operation_id
    assert history.state == WorkflowRunHistoryState.COMPLETED
    assert history.total_step_count == 3
    assert history.completed_step_count == 3
    assert history.progress_percent == 100
    assert history.started_at is not None
    assert history.completed_at is not None
    assert [item.step_id for item in history.steps] == ["one", "two", "verify"]
    assert [item.state for item in history.steps] == [
        WorkflowStepHistoryState.COMPLETED,
        WorkflowStepHistoryState.COMPLETED,
        WorkflowStepHistoryState.COMPLETED,
    ]
    assert "C:/Users/User" not in str(data)
    with pytest.raises(TypeError):
        history.metadata["new"] = "mutable"
    assert isinstance(history.steps, tuple)


def test_run_history_records_failed_step_safely_and_later_steps_pending():
    coordinator = ExecutionCoordinator()
    op, token = operation(coordinator)
    state = RunnerState(calls=[])
    runner = build_runner(
        coordinator,
        AllowPolicy(),
        [step("read"), step("boom", fail=True), step("later")],
    )

    runner.start(operation=op, state=state, token=token)
    history = runner.run_history(op.operation_id)
    text = str(history.to_dict())

    assert history.state == WorkflowRunHistoryState.FAILED
    assert [item.state for item in history.steps] == [
        WorkflowStepHistoryState.COMPLETED,
        WorkflowStepHistoryState.FAILED,
        WorkflowStepHistoryState.PENDING,
    ]
    assert history.safe_failure_summary is not None
    assert "sk-test" not in text
    assert "RuntimeError" not in text
    assert "traceback" not in text.lower()


def test_run_history_records_cancellation_without_completing_remaining_steps():
    coordinator = ExecutionCoordinator()
    op, token = operation(coordinator)
    state = RunnerState(calls=[])
    runner = build_runner(
        coordinator,
        AllowPolicy(),
        [step("read"), step("write", confirm=True), step("verify")],
    )

    runner.start(operation=op, state=state, token=token)
    runner.cancel(op.operation_id)
    history = runner.run_history(op.operation_id)

    assert history.state == WorkflowRunHistoryState.CANCELLED
    assert history.cancelled is True
    assert [item.state for item in history.steps] == [
        WorkflowStepHistoryState.COMPLETED,
        WorkflowStepHistoryState.CANCELLED,
        WorkflowStepHistoryState.PENDING,
    ]
    assert history.completed_step_count == 1


def test_run_history_records_waiting_for_confirmation_and_resume():
    coordinator = ExecutionCoordinator()
    op, token = operation(coordinator)
    state = RunnerState(calls=[])
    runner = build_runner(
        coordinator,
        AllowPolicy(),
        [step("read"), step("write", confirm=True), step("verify")],
    )

    runner.start(operation=op, state=state, token=token)
    waiting = runner.run_history(op.operation_id)

    assert waiting.state == WorkflowRunHistoryState.WAITING_FOR_CONFIRMATION
    assert waiting.waiting_for_confirmation is True
    assert waiting.active_step_id == "write"
    assert [item.state for item in waiting.steps] == [
        WorkflowStepHistoryState.COMPLETED,
        WorkflowStepHistoryState.WAITING_FOR_CONFIRMATION,
        WorkflowStepHistoryState.PENDING,
    ]

    runner.resume(op.operation_id)
    completed = runner.run_history(op.operation_id)

    assert completed.state == WorkflowRunHistoryState.COMPLETED
    assert [item.state for item in completed.steps] == [
        WorkflowStepHistoryState.COMPLETED,
        WorkflowStepHistoryState.COMPLETED,
        WorkflowStepHistoryState.COMPLETED,
    ]
    assert state.calls == ["read", "write", "verify"]


def test_recent_run_histories_are_newest_first_and_bounded():
    coordinator = ExecutionCoordinator()
    runner = build_runner(coordinator, AllowPolicy(), [step("read")])
    first, first_token = operation(coordinator)
    second = coordinator.register(
        source="test",
        idempotency_key="second",
        request_fingerprint="second",
        command_id="workflow.test",
    )

    runner.start(operation=first, state=RunnerState(calls=[]), token=first_token)
    runner.start(
        operation=second.operation,
        state=RunnerState(calls=[]),
        token=second.token,
    )

    histories = runner.recent_run_histories(limit=1)

    assert len(histories) == 1
    assert histories[0].operation_id == second.operation.operation_id


def test_run_history_model_handles_empty_steps_and_missing_fields_safely():
    history = WorkflowRunHistory(
        run_id="run-empty",
        operation_id="op-empty",
        workflow_id="wf-empty",
        workflow_name=None,
        objective_summary="",
        state=WorkflowRunHistoryState.PENDING,
        created_at="",
        started_at=None,
        completed_at=None,
        total_step_count=0,
        completed_step_count=0,
    )

    assert history.steps == ()
    assert history.progress_percent == 0
    assert history.objective_summary == "Workflow objective unavailable."


def test_workflow_state_is_mirrored_to_journal_metadata_without_breaking_journal():
    coordinator = ExecutionCoordinator()
    op, token = operation(coordinator)
    state = RunnerState(calls=[])
    runner = build_runner(coordinator, AllowPolicy(), [step("read")])

    runner.start(operation=op, state=state, token=token)
    operation_snapshot = coordinator.journal.get(op.operation_id)

    assert operation_snapshot is not None
    assert operation_snapshot.metadata["workflow_run_id"] == op.operation_id
    assert operation_snapshot.metadata["workflow_state"] == "completed"
    assert operation_snapshot.metadata["workflow_total_steps"] == "1"


def test_operation_is_marked_running_while_step_executes():
    coordinator = ExecutionCoordinator()
    op, token = operation(coordinator)
    observed_statuses = []

    def action(state: RunnerState, token):
        observed = coordinator.journal.get(op.operation_id)
        observed_statuses.append(observed.status.value if observed is not None else None)
        return WorkflowStepResult(
            step_id="read",
            status=WorkflowStepStatus.SUCCEEDED,
            safe_message="ok",
        )

    runner = build_runner(
        coordinator,
        AllowPolicy(),
        [
            WorkflowExecutableStep(
                WorkflowStepDefinition("read", "Read"),
                action,
            )
        ],
    )

    runner.start(operation=op, state=RunnerState(calls=[]), token=token)

    assert observed_statuses == ["running"]


def test_unknown_or_malformed_workflow_states_project_to_safe_fallbacks():
    coordinator = ExecutionCoordinator()
    op, token = operation(coordinator)
    state = RunnerState(calls=[])
    runner = build_runner(coordinator, AllowPolicy(), [step("read"), step("write")])
    runner.start(operation=op, state=state, token=token)

    internal = runner._runs[op.operation_id]
    raw_detail = "Traceback RuntimeError C:/Users/User/private.txt sk-test-1234567890secret"
    internal.status = [raw_detail]
    internal.step_statuses["read"] = [raw_detail]
    internal.step_statuses.pop("write", None)

    history = runner.run_history(op.operation_id)
    text = str(history.to_dict())

    assert history.state == WorkflowRunHistoryState.UNKNOWN
    assert [item.step_id for item in history.steps] == ["read", "write"]
    assert [item.state for item in history.steps] == [
        WorkflowStepHistoryState.UNKNOWN,
        WorkflowStepHistoryState.PENDING,
    ]
    assert history.total_step_count == 2
    assert "Traceback" not in text
    assert "RuntimeError" not in text
    assert "C:/Users/User" not in text
    assert "sk-test" not in text


def test_workflow_history_dto_is_detached_from_later_runtime_mutation():
    coordinator = ExecutionCoordinator()
    op, token = operation(coordinator)
    state = RunnerState(calls=[])
    runner = build_runner(coordinator, AllowPolicy(), [step("read"), step("write")])
    runner.start(operation=op, state=state, token=token)

    history = runner.run_history(op.operation_id)
    internal = runner._runs[op.operation_id]
    internal.completed_step_ids.clear()
    internal.step_statuses["read"] = WorkflowStepStatus.FAILED
    internal.results["read"] = WorkflowStepResult(
        step_id="read",
        status=WorkflowStepStatus.FAILED,
        safe_message="mutated after projection",
        safe_output_metadata={"token": "sk-test-1234567890secret"},
    )
    internal.safe_metadata["objective_summary"] = "mutated objective"

    assert history.completed_step_count == 2
    assert history.objective_summary == "test_workflow"
    assert [item.step_id for item in history.steps] == ["read", "write"]
    assert [item.state for item in history.steps] == [
        WorkflowStepHistoryState.COMPLETED,
        WorkflowStepHistoryState.COMPLETED,
    ]
    with pytest.raises(AttributeError):
        history.steps.append("new")
    with pytest.raises(TypeError):
        history.metadata["objective_summary"] = "changed"
    refreshed = runner.run_history(op.operation_id)
    assert refreshed.completed_step_count == 0
    assert [item.step_id for item in refreshed.steps] == ["read", "write"]


def test_failed_run_resumes_from_first_unfinished_step_without_replaying_completed():
    coordinator = ExecutionCoordinator()
    source_op, source_token = operation(coordinator)
    resume_registration = coordinator.register(
        source="test",
        idempotency_key="resume",
        request_fingerprint="resume",
        command_id="workflow.resume",
    )
    state = RunnerState(calls=[])
    attempts = {"three": 0}

    def fail_once(step_id):
        def action(state: RunnerState, token):
            token.raise_if_cancelled()
            state.calls.append(step_id)
            if step_id == "three":
                attempts["three"] += 1
                if attempts["three"] == 1:
                    return WorkflowStepResult(
                        step_id=step_id,
                        status=WorkflowStepStatus.FAILED,
                        safe_message="step failed safely",
                        error_code="step_failed",
                    )
            return WorkflowStepResult(
                step_id=step_id,
                status=WorkflowStepStatus.SUCCEEDED,
                safe_message="ok",
            )

        return WorkflowExecutableStep(WorkflowStepDefinition(step_id, step_id), action)

    runner = build_runner(
        coordinator,
        AllowPolicy(),
        [fail_once("one"), fail_once("two"), fail_once("three"), fail_once("four")],
    )
    runner.start(operation=source_op, state=state, token=source_token)
    original_before = runner.run_history(source_op.operation_id)

    result = runner.resume_from_run(
        source_operation_id=source_op.operation_id,
        operation=resume_registration.operation,
        token=resume_registration.token,
    )

    original_after = runner.run_history(source_op.operation_id)
    resumed = runner.run_history(resume_registration.operation.operation_id)
    assert result.ok is True
    assert result.status == WorkflowResumeStatus.STARTED
    assert result.resume_step_id == "three"
    assert result.resumed_run_id == resume_registration.operation.operation_id
    assert state.calls == ["one", "two", "three", "three", "four"]
    assert [step.to_dict() for step in original_after.steps] == [
        step.to_dict() for step in original_before.steps
    ]
    assert original_after.state == original_before.state
    assert original_after.resume_rejection_reason == WorkflowResumeRejectionReason.ALREADY_RESUMED
    assert [step.state for step in resumed.steps] == [
        WorkflowStepHistoryState.COMPLETED,
        WorkflowStepHistoryState.COMPLETED,
        WorkflowStepHistoryState.COMPLETED,
        WorkflowStepHistoryState.COMPLETED,
    ]
    assert resumed.resumed_from_run_id == source_op.operation_id


def test_resume_rejects_completed_malformed_unknown_and_incompatible_runs_safely():
    coordinator = ExecutionCoordinator()
    completed_op, completed_token = operation(coordinator)
    malformed_registration = coordinator.register(
        source="test",
        idempotency_key="malformed",
        request_fingerprint="malformed",
        command_id="workflow.test",
    )
    incompatible_registration = coordinator.register(
        source="test",
        idempotency_key="incompatible",
        request_fingerprint="incompatible",
        command_id="workflow.test",
    )
    completed_runner = build_runner(coordinator, AllowPolicy(), [step("done")])
    completed_runner.start(
        operation=completed_op,
        state=RunnerState(calls=[]),
        token=completed_token,
    )
    completed = completed_runner.resume_eligibility(completed_op.operation_id)

    runner = build_runner(coordinator, AllowPolicy(), [step("read"), step("boom", fail=True)])
    runner.start(
        operation=malformed_registration.operation,
        state=RunnerState(calls=[]),
        token=malformed_registration.token,
    )
    internal = runner._runs[malformed_registration.operation.operation_id]
    internal.status = ["Traceback C:/Users/User/raw.log sk-test-1234567890secret"]
    internal.step_statuses["boom"] = ["RuntimeError backend"]
    malformed = runner.resume_eligibility(malformed_registration.operation.operation_id)

    runner.start(
        operation=incompatible_registration.operation,
        state=RunnerState(calls=[]),
        token=incompatible_registration.token,
    )
    runner.steps = tuple(reversed(runner.steps))
    incompatible = runner.resume_eligibility(incompatible_registration.operation.operation_id)
    text = str((completed.to_dict(), malformed.to_dict(), incompatible.to_dict()))

    assert completed.reason == WorkflowResumeRejectionReason.ALREADY_COMPLETED
    assert malformed.reason == WorkflowResumeRejectionReason.MALFORMED_STATE
    assert incompatible.reason == WorkflowResumeRejectionReason.WORKFLOW_DEFINITION_INCOMPATIBLE
    assert "Traceback" not in text
    assert "RuntimeError" not in text
    assert "C:/Users/User" not in text
    assert "sk-test" not in text


def test_non_resumable_failed_step_is_rejected_before_execution():
    coordinator = ExecutionCoordinator()
    source_op, source_token = operation(coordinator)
    resume_registration = coordinator.register(
        source="test",
        idempotency_key="resume-non-resumable",
        request_fingerprint="resume-non-resumable",
        command_id="workflow.resume",
    )
    state = RunnerState(calls=[])
    runner = build_runner(
        coordinator,
        AllowPolicy(),
        [
            step("read"),
            WorkflowExecutableStep(
                WorkflowStepDefinition("boom", "boom", resumable=False),
                lambda state, token: WorkflowStepResult(
                    step_id="boom",
                    status=WorkflowStepStatus.FAILED,
                    safe_message="failed safely",
                    error_code="failed",
                ),
            ),
            step("later"),
        ],
    )
    runner.start(operation=source_op, state=state, token=source_token)

    result = runner.resume_from_run(
        source_operation_id=source_op.operation_id,
        operation=resume_registration.operation,
        token=resume_registration.token,
    )

    assert result.ok is False
    assert result.rejection_reason == WorkflowResumeRejectionReason.NON_RESUMABLE_STEP
    assert state.calls == ["read"]
    assert resume_registration.operation.operation_id not in runner._runs


def test_duplicate_resume_requests_create_at_most_one_resumed_attempt():
    coordinator = ExecutionCoordinator()
    source_op, source_token = operation(coordinator)
    first_resume = coordinator.register(
        source="test",
        idempotency_key="resume-one",
        request_fingerprint="resume-one",
        command_id="workflow.resume",
    )
    second_resume = coordinator.register(
        source="test",
        idempotency_key="resume-two",
        request_fingerprint="resume-two",
        command_id="workflow.resume",
    )
    state = RunnerState(calls=[])
    attempts = {"boom": 0}

    def action(step_id):
        def _run(state: RunnerState, token):
            state.calls.append(step_id)
            if step_id == "boom":
                attempts["boom"] += 1
                if attempts["boom"] == 1:
                    return WorkflowStepResult(
                        step_id=step_id,
                        status=WorkflowStepStatus.FAILED,
                        safe_message="failed safely",
                        error_code="failed",
                    )
            return WorkflowStepResult(
                step_id=step_id,
                status=WorkflowStepStatus.SUCCEEDED,
                safe_message="ok",
            )

        return WorkflowExecutableStep(WorkflowStepDefinition(step_id, step_id), _run)

    runner = build_runner(coordinator, AllowPolicy(), [action("read"), action("boom")])
    runner.start(operation=source_op, state=state, token=source_token)

    first = runner.resume_from_run(
        source_operation_id=source_op.operation_id,
        operation=first_resume.operation,
        token=first_resume.token,
    )
    second = runner.resume_from_run(
        source_operation_id=source_op.operation_id,
        operation=second_resume.operation,
        token=second_resume.token,
    )
    resume_started = [
        operation
        for operation in coordinator.recent_operations(None)
        if operation.metadata.get("workflow_resume_status") == "started"
    ]

    assert first.ok is True
    assert second.ok is False
    assert second.status == WorkflowResumeStatus.CONFLICT
    assert second.rejection_reason == WorkflowResumeRejectionReason.ALREADY_RESUMED
    assert len(resume_started) == 1
