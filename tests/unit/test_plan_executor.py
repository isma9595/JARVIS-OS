from dataclasses import dataclass

from core.execution_coordinator import ExecutionCoordinator
from core.policy_boundary import PolicyDecision, PolicyDecisionType, PolicyRequest
from planner import (
    MultiStepPlanner,
    PlanCapability,
    PlanCapabilityDescriptor,
    PlanExecutor,
    PlanSideEffect,
    PlanStatus,
    PlanStepStatus,
    PlannerCapabilityRegistry,
)


@dataclass(frozen=True)
class Result:
    safe_message: str


class Policy:
    def __init__(self, deny=()):
        self.requests = []
        self.deny = set(deny)

    def evaluate(self, request):
        self.requests.append((request.command_id, request.confirmation_present))
        if request.command_id in self.deny:
            return PolicyDecision(
                decision=PolicyDecisionType.DENY,
                reason_codes=("denied",),
                required_capabilities=request.required_capabilities,
                requires_confirmation=False,
                user_message="denied",
                safe_to_execute=False,
            )
        return PolicyDecision(
            decision=PolicyDecisionType.ALLOW,
            reason_codes=("allowed",),
            required_capabilities=request.required_capabilities,
            requires_confirmation=False,
            user_message="allowed",
            safe_to_execute=True,
        )


def build_registry(calls, *, fail=False, confirm=False):
    registry = PlannerCapabilityRegistry.empty()

    def add(capability_id, capability_calls):
        def execute(_args):
            calls.append(capability_id)
            if fail and capability_id == "memory.recall":
                raise RuntimeError("raw sk-test123456789")
            return Result(f"{capability_id} ok")

        descriptor = PlanCapabilityDescriptor(
            capability_id,
            capability_id,
            capability_id,
            "test",
            "confirmation_required" if confirm and capability_id == "memory.forget_all" else "read_only",
            PlanSideEffect.BOUNDED_LOCAL_STATE if capability_id.startswith("memory.") else PlanSideEffect.READ_ONLY,
            confirm and capability_id == "memory.forget_all",
            {},
            "safe",
        )
        return PlanCapability(
            descriptor,
            execute,
            lambda args, confirmed, cid=capability_id: PolicyRequest(
                source="test",
                command_id=cid,
                risk="confirmation_required" if descriptor.requires_confirmation else "read_only",
                required_capabilities=("file_write",) if descriptor.requires_confirmation else ("read_system_state",),
                confirmation_present=confirmed or not descriptor.requires_confirmation,
            ),
        )

    for cid in ("system.status", "language.get", "memory.recall", "memory.forget_all"):
        registry = registry.register(add(cid, calls))
    return registry


def make_plan(registry, text="составь план: статус системы; текущий язык"):
    planner = MultiStepPlanner(registry)
    return planner, planner.create_from_text(text, language_code="ru-RU").snapshot


def test_steps_execute_in_order_one_operation_and_progress_100():
    calls = []
    registry = build_registry(calls)
    planner, plan = make_plan(registry)
    executor = PlanExecutor(registry=registry, execution_coordinator=ExecutionCoordinator(), policy_boundary=Policy())

    result = executor.start(plan, planner.steps(), source="test")

    assert calls == ["system.status", "language.get"]
    assert result.operation_id
    assert result.status == PlanStatus.SUCCEEDED
    assert result.progress_percent == 100


def test_policy_checked_before_each_step_and_denial_stops_later_steps():
    calls = []
    registry = build_registry(calls)
    planner, plan = make_plan(registry)
    policy = Policy(deny={"language.get"})
    executor = PlanExecutor(registry=registry, execution_coordinator=ExecutionCoordinator(), policy_boundary=policy)

    result = executor.start(plan, planner.steps(), source="test")

    assert calls == ["system.status"]
    assert ("system.status", True) in policy.requests
    assert ("language.get", True) in policy.requests
    assert result.status == PlanStatus.BLOCKED
    assert result.safe_error_code == "policy_denied"
    assert result.snapshot.steps[1].status == PlanStepStatus.BLOCKED
    assert result.snapshot.steps[1].safe_message == "blocked"
    assert result.snapshot.steps[1].safe_message != "Step is pending."


def test_failure_stops_later_steps_and_raw_exception_is_absent():
    calls = []
    registry = build_registry(calls, fail=True)
    planner, plan = make_plan(registry, "составь план: статус системы; что ты помнишь о test; текущий язык")
    executor = PlanExecutor(registry=registry, execution_coordinator=ExecutionCoordinator(), policy_boundary=Policy())

    result = executor.start(plan, planner.steps(), source="test")

    assert calls == ["system.status", "memory.recall"]
    assert result.status == PlanStatus.FAILED
    assert "sk-test" not in str(result.to_dict())
    assert result.snapshot.steps[2].status == PlanStepStatus.SKIPPED
    assert result.snapshot.steps[2].safe_message == "skipped"
    assert result.snapshot.steps[2].safe_message != "Step is pending."


def test_confirmation_pause_resume_cancel_and_duplicate_resume_do_not_repeat_side_effect():
    calls = []
    registry = build_registry(calls, confirm=True)
    planner, plan = make_plan(registry, "составь план: статус системы; забудь всё, что ты помнишь обо мне")
    executor = PlanExecutor(registry=registry, execution_coordinator=ExecutionCoordinator(), policy_boundary=Policy())

    first = executor.start(plan, planner.steps(), source="test")
    resumed = executor.resume(first.snapshot)
    duplicate = executor.resume(resumed.snapshot)

    assert first.status == PlanStatus.AWAITING_CONFIRMATION
    assert [step.is_current for step in first.snapshot.steps] == [False, True]
    assert calls == ["system.status", "memory.forget_all"]
    assert resumed.operation_id == first.operation_id
    assert duplicate.status == PlanStatus.SUCCEEDED
    assert [step.is_current for step in duplicate.snapshot.steps] == [False, False]
    assert calls.count("memory.forget_all") == 1


def test_start_rejects_awaiting_confirmation_snapshot_without_resume_or_capability_call():
    calls = []
    registry = build_registry(calls, confirm=True)
    planner, plan = make_plan(registry, "create plan: forget everything you remember about me")
    executor = PlanExecutor(registry=registry, execution_coordinator=ExecutionCoordinator(), policy_boundary=Policy())

    first = executor.start(plan, planner.steps(), source="test")
    repeated = executor.start(first.snapshot, planner.steps(), source="test")

    assert first.status == PlanStatus.AWAITING_CONFIRMATION
    assert first.operation_id
    assert calls == []
    assert repeated.status == PlanStatus.AWAITING_CONFIRMATION
    assert repeated.safe_error_code == "explicit_confirmation_required"
    assert repeated.operation_id == first.operation_id
    assert repeated.snapshot.operation_id == first.operation_id
    assert repeated.snapshot.awaiting_confirmation is True
    assert repeated.snapshot.steps[0].status == PlanStepStatus.AWAITING_CONFIRMATION
    assert calls == []


def test_cancelled_executor_step_without_execution_message_does_not_keep_pending_message():
    calls = []
    registry = build_registry(calls, confirm=True)
    planner, plan = make_plan(registry, "create plan: forget everything you remember about me")
    executor = PlanExecutor(registry=registry, execution_coordinator=ExecutionCoordinator(), policy_boundary=Policy())

    first = executor.start(plan, planner.steps(), source="test")
    cancelled = executor.cancel(first.snapshot)

    assert cancelled.status == PlanStatus.CANCELLED
    assert cancelled.snapshot.steps[0].status == PlanStepStatus.CANCELLED
    assert cancelled.snapshot.steps[0].safe_message == "cancelled"
    assert cancelled.snapshot.steps[0].safe_message != "Step is pending."


def test_idempotency_conflict_executes_nothing():
    calls = []
    registry = build_registry(calls)
    planner, plan = make_plan(registry)
    coordinator = ExecutionCoordinator()
    executor = PlanExecutor(registry=registry, execution_coordinator=coordinator, policy_boundary=Policy())

    first = executor.start(plan, planner.steps(), source="test", idempotency_key="same")
    other_planner, other_plan = make_plan(registry, "составь план: текущий язык")
    conflict = executor.start(other_plan, other_planner.steps(), source="test", idempotency_key="same")

    assert first.status == PlanStatus.SUCCEEDED
    assert conflict.safe_error_code == "idempotency_conflict"
    assert calls == ["system.status", "language.get"]
