from dataclasses import asdict, dataclass

import pytest

from core.execution_coordinator import ExecutionCoordinator
from core.policy_boundary import PolicyDecision, PolicyDecisionType, PolicyRequest
from workflows.contracts import WorkflowStepDefinition, WorkflowStepResult, WorkflowStepStatus
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
