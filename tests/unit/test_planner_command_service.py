import subprocess
import sys
from dataclasses import dataclass

from app.app_contracts import AppCommandSource
from app.services.planner_command_service import PlannerCommandService
from core.execution_coordinator import ExecutionCoordinator
from core.policy_boundary import PolicyCapability, PolicyDecisionBoundary, PolicyRequest
from memory import LocalMemoryManager
from planner import (
    MultiStepPlanner,
    PlanCapability,
    PlanCapabilityDescriptor,
    PlanExecutor,
    PlanSideEffect,
    PlannerCapabilityRegistry,
)


@dataclass(frozen=True)
class CapabilityResult:
    safe_message: str


class TrackingProcessor:
    def __init__(self):
        self.calls = []

    def process(self, text):
        self.calls.append(text)
        return {"response": f"processed: {text}"}


class TrackingMemoryManager(LocalMemoryManager):
    def __init__(self, path):
        super().__init__(path)
        self.forget_all_calls = 0

    def forget_all_user_facts(self):
        self.forget_all_calls += 1
        return super().forget_all_user_facts()


def localized_text(_ru: str, en: str) -> str:
    return en


def safe_text_preview(text: str) -> str:
    preview = str(text or "").strip()
    return preview[:120] if preview else "<empty>"


def policy_request(
    command_id: str,
    risk: str,
    capabilities: tuple[str, ...],
    normalized: str,
    confirmation_present: bool,
) -> PolicyRequest:
    return PolicyRequest(
        source="planner",
        command_id=command_id,
        action_id=command_id,
        intent_kind="local_command",
        risk=risk,
        required_capabilities=capabilities,
        confirmation_present=confirmation_present,
        metadata={"normalized_text": normalized},
    )


def descriptor(
    capability_id: str,
    display_name: str,
    risk: str,
    side_effect: PlanSideEffect,
    requires_confirmation: bool,
    schema: dict[str, object] | None = None,
) -> PlanCapabilityDescriptor:
    return PlanCapabilityDescriptor(
        capability_id=capability_id,
        display_name_ru=display_name,
        display_name_en=display_name,
        category=capability_id.split(".", 1)[0],
        risk_level=risk,
        side_effect=side_effect,
        requires_confirmation=requires_confirmation,
        argument_schema=schema or {},
        safe_description=capability_id,
    )


def build_registry(processor: TrackingProcessor, memory: TrackingMemoryManager):
    registry = PlannerCapabilityRegistry.empty()

    def app_status(_args):
        result = processor.process("system status")
        return CapabilityResult(str(result.get("response", result)))

    def memory_remember(args):
        memory.remember_user_fact(args.get("key"), args.get("value"))
        return CapabilityResult("Memory saved.")

    def memory_forget_all(_args):
        memory.forget_all_user_facts()
        return CapabilityResult("Memory cleared.")

    capabilities = (
        PlanCapability(
            descriptor(
                "system.status",
                "System status",
                "read_only",
                PlanSideEffect.READ_ONLY,
                False,
            ),
            app_status,
            lambda args, confirmed: policy_request(
                "system.status",
                "read_only",
                (PolicyCapability.READ_SYSTEM_STATE.value,),
                "system status",
                True,
            ),
        ),
        PlanCapability(
            descriptor(
                "memory.remember",
                "Remember fact",
                "local_write",
                PlanSideEffect.BOUNDED_LOCAL_STATE,
                False,
                {"key": "string", "value": "string"},
            ),
            memory_remember,
            lambda args, confirmed: policy_request(
                "memory.remember",
                "read_only",
                (PolicyCapability.READ_SYSTEM_STATE.value,),
                "memory remember",
                True,
            ),
        ),
        PlanCapability(
            descriptor(
                "memory.forget_all",
                "Forget all memory",
                "confirmation_required",
                PlanSideEffect.BOUNDED_LOCAL_STATE,
                True,
            ),
            memory_forget_all,
            lambda args, confirmed: policy_request(
                "memory.forget_all",
                "confirmation_required",
                (PolicyCapability.FILE_WRITE.value,),
                "forget everything you remember about me",
                confirmed,
            ),
        ),
    )
    for capability in capabilities:
        registry = registry.register(capability)
    return registry


def make_planner_service(tmp_path, *, tracking_memory=False):
    memory_cls = TrackingMemoryManager if tracking_memory else LocalMemoryManager
    memory = memory_cls(tmp_path / "planner_command_service_memory.json")
    processor = TrackingProcessor()
    registry = build_registry(processor, memory)
    planner = MultiStepPlanner(registry)
    executor = PlanExecutor(
        registry=registry,
        execution_coordinator=ExecutionCoordinator(),
        policy_boundary=PolicyDecisionBoundary(),
    )
    service = PlannerCommandService(
        multi_step_planner=planner,
        plan_executor=executor,
        language_code=lambda: "en-US",
        localized_text=localized_text,
        safe_text_preview=safe_text_preview,
    )
    return service, planner, processor, memory


def test_planner_command_service_import_does_not_load_app_service():
    script = (
        "import sys;"
        "import app.services.planner_command_service;"
        "print('app.app_service' in sys.modules)"
    )

    result = subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.strip() == "False"


def test_direct_read_only_execute_preview_projects_without_execution_or_mutation(tmp_path):
    planner_service, planner, processor, _memory = make_planner_service(tmp_path)

    created = planner_service.handle_command(
        "create plan: system status",
        AppCommandSource.TEST,
        idempotency_key=None,
    )
    before = planner.snapshot()
    preview = planner_service.preview_command("execute plan", "execute plan")
    after = planner.snapshot()

    assert created.plan_status == "proposed"
    assert preview.risk_level == "read_only"
    assert preview.requires_confirmation is False
    assert preview.operation_id is None
    assert preview.active_step_capability_id == "system.status"
    assert processor.calls == []
    assert after.to_dict() == before.to_dict()


def test_direct_local_write_execute_preview_projects_without_memory_mutation(tmp_path):
    planner_service, planner, _processor, memory = make_planner_service(tmp_path)

    planner_service.handle_command(
        "create plan: remember test word north",
        AppCommandSource.TEST,
        idempotency_key=None,
    )
    before = planner.snapshot()
    preview = planner_service.preview_command("execute plan", "execute plan")
    after = planner.snapshot()

    assert preview.risk_level == "local_write"
    assert preview.requires_confirmation is False
    assert preview.operation_id is None
    assert preview.active_step_capability_id == "memory.remember"
    assert memory.recall_user_fact("test word").found is False
    assert after.to_dict() == before.to_dict()


def test_create_preview_projects_russian_forget_all_without_persisting_or_mutating(tmp_path):
    planner_service, planner, processor, memory = make_planner_service(
        tmp_path,
        tracking_memory=True,
    )
    memory.remember_user_fact("marker", "survives")

    preview = planner_service.preview_command(
        "составь план: забудь всё, что ты обо мне помнишь",
        "составь план: забудь всё, что ты обо мне помнишь",
    )

    assert preview.known_command is True
    assert preview.registry_match_id == "planner.general_multi_step"
    assert preview.category == "planner"
    assert preview.risk_level == "confirmation_required"
    assert preview.read_only is False
    assert preview.requires_confirmation is True
    assert preview.active_plan_id is None
    assert preview.active_plan_status is None
    assert preview.active_step_id == "step-1"
    assert preview.active_step_capability_id == "memory.forget_all"
    assert preview.operation_id is None
    assert planner.snapshot() is None
    assert memory.recall_user_fact("marker").found is True
    assert memory.forget_all_calls == 0
    assert processor.calls == []


def test_create_execute_persists_same_russian_forget_all_step_without_execution(tmp_path):
    planner_service, planner, processor, memory = make_planner_service(
        tmp_path,
        tracking_memory=True,
    )
    memory.remember_user_fact("marker", "survives")

    result = planner_service.handle_command(
        "составь план: забудь всё, что ты обо мне помнишь",
        AppCommandSource.TEST,
        idempotency_key=None,
    )
    snapshot = planner.snapshot()

    assert result.plan_status == "proposed"
    assert result.executed is False
    assert result.requires_confirmation is False
    assert result.operation_id is None
    assert snapshot is not None
    assert [step.capability_id for step in snapshot.steps] == ["memory.forget_all"]
    assert planner.steps()[0].arguments == {}
    assert planner.steps()[0].requires_confirmation is True
    assert memory.recall_user_fact("marker").found is True
    assert memory.forget_all_calls == 0
    assert processor.calls == []


def test_direct_first_execute_enters_awaiting_confirmation_without_destructive_execution(tmp_path):
    planner_service, planner, _processor, memory = make_planner_service(
        tmp_path,
        tracking_memory=True,
    )
    memory.remember_user_fact("marker", "survives")
    planner_service.handle_command(
        "create plan: forget everything you remember about me",
        AppCommandSource.TEST,
        idempotency_key=None,
    )

    result = planner_service.handle_command(
        "execute plan",
        AppCommandSource.TEST,
        idempotency_key=None,
    )
    snapshot = planner.snapshot()

    assert result.plan_status == "awaiting_confirmation"
    assert result.awaiting_confirmation is True
    assert result.operation_id
    assert result.progress_percent == 0
    assert snapshot.operation_id == result.operation_id
    assert memory.recall_user_fact("marker").found is True
    assert memory.forget_all_calls == 0


def test_direct_repeated_execute_requires_explicit_confirmation_and_preserves_operation(tmp_path):
    planner_service, planner, _processor, memory = make_planner_service(
        tmp_path,
        tracking_memory=True,
    )
    memory.remember_user_fact("marker", "survives")
    planner_service.handle_command(
        "create plan: forget everything you remember about me",
        AppCommandSource.TEST,
        idempotency_key=None,
    )
    first = planner_service.handle_command(
        "execute plan",
        AppCommandSource.TEST,
        idempotency_key=None,
    )

    repeated = planner_service.handle_command(
        "execute plan",
        AppCommandSource.TEST,
        idempotency_key=None,
    )
    snapshot = planner.snapshot()

    assert repeated.error == "explicit_confirmation_required"
    assert repeated.operation_id == first.operation_id
    assert repeated.executed is False
    assert repeated.awaiting_confirmation is True
    assert repeated.progress_percent == first.progress_percent
    assert snapshot.operation_id == first.operation_id
    assert memory.recall_user_fact("marker").found is True
    assert memory.forget_all_calls == 0


def test_direct_cancel_preserves_marker_and_cancelled_plan_cannot_resume(tmp_path):
    planner_service, planner, _processor, memory = make_planner_service(
        tmp_path,
        tracking_memory=True,
    )
    memory.remember_user_fact("marker", "survives")
    planner_service.handle_command(
        "create plan: forget everything you remember about me",
        AppCommandSource.TEST,
        idempotency_key=None,
    )
    first = planner_service.handle_command(
        "execute plan",
        AppCommandSource.TEST,
        idempotency_key=None,
    )

    cancelled = planner_service.handle_command(
        "cancel plan",
        AppCommandSource.TEST,
        idempotency_key=None,
    )
    cancelled_execute = planner_service.handle_command(
        "execute plan",
        AppCommandSource.TEST,
        idempotency_key=None,
    )
    snapshot = planner.snapshot()

    assert cancelled.plan_status == "cancelled"
    assert cancelled.operation_id == first.operation_id
    assert cancelled.awaiting_confirmation is False
    assert cancelled_execute.error == "terminal_plan_not_reexecuted"
    assert cancelled_execute.operation_id == first.operation_id
    assert snapshot.status.value == "cancelled"
    assert memory.recall_user_fact("marker").found is True
    assert memory.forget_all_calls == 0


def test_direct_read_only_plan_execution_completes_once_and_reaches_100_percent(tmp_path):
    planner_service, planner, processor, _memory = make_planner_service(tmp_path)
    planner_service.handle_command(
        "create plan: system status",
        AppCommandSource.TEST,
        idempotency_key=None,
    )

    result = planner_service.handle_command(
        "execute plan",
        AppCommandSource.TEST,
        idempotency_key=None,
    )
    snapshot = planner.snapshot()

    assert result.ok is True
    assert result.plan_status == "succeeded"
    assert result.awaiting_confirmation is False
    assert result.progress_percent == 100
    assert snapshot.progress_percent == 100
    assert snapshot.steps[0].status.value == "succeeded"
    assert processor.calls == ["system status"]
