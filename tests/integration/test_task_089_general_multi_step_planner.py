from pathlib import Path

from app import AppCommandSource, JarvisAppService
from language.language_manager import ApplicationLanguageManager
from memory import LocalMemoryManager
from planner import PlanCapability, PlanCapabilityDescriptor, PlanSideEffect
from core.policy_boundary import PolicyRequest
from users.user_profile import UserProfileManager


CREATE_READ_ONLY = "составь план: статус системы; текущий язык"
EXECUTE = "выполни план"
YES = "да"
CANCEL = "отмена"


class TrackingProcessor:
    def __init__(self):
        self.calls = []
        self.user_profile = None
        self.memory_manager = None

    def process(self, text):
        self.calls.append(text)
        if text == "статус системы":
            return {"response": "system status ok"}
        return {"response": f"processed: {text}"}


def make_service(tmp_path: Path):
    memory = LocalMemoryManager(tmp_path / "task089_memory.json")
    profile = UserProfileManager(tmp_path / "task089_profile.json")
    language = ApplicationLanguageManager.from_profile_manager(profile)
    processor = TrackingProcessor()
    return JarvisAppService(
        command_processor=processor,
        memory_manager=memory,
        language_manager=language,
    ), processor, memory


def test_read_only_plan_vertical_path_and_lazy_components(tmp_path):
    service, processor, memory = make_service(tmp_path)

    assert service.multi_step_planner.snapshot() is None
    before = service.get_startup_profile()
    created = service.execute_contract(CREATE_READ_ONLY, AppCommandSource.TEST)

    assert created.plan_status == "proposed"
    assert created.plan_step_count == 2
    assert created.progress_percent == 0
    assert processor.calls == []
    assert memory.memory_file_exists() is False

    executed = service.execute_contract(EXECUTE, AppCommandSource.TEST)
    after = service.get_startup_profile()

    assert executed.plan_id == created.plan_id
    assert executed.operation_id
    assert executed.plan_status == "succeeded"
    assert executed.progress_percent == 100
    assert processor.calls == ["статус системы"]
    assert after.deferred_components == before.deferred_components


def test_local_state_memory_plan_writes_once_then_recalls(tmp_path):
    service, _processor, memory = make_service(tmp_path)

    created = service.execute_contract(
        "составь план: запомни тестовое слово север; покажи тестовое слово",
        AppCommandSource.TEST,
    )

    assert created.plan_status == "proposed"
    assert memory.list_user_facts().entries == ()

    executed = service.execute_contract(EXECUTE, AppCommandSource.TEST)
    duplicate = service.execute_contract(EXECUTE, AppCommandSource.TEST)

    entries = memory.list_user_facts().entries
    assert executed.plan_status == "succeeded"
    assert "север" in executed.output_text
    assert len(entries) == 1
    assert entries[0].value == "север"
    assert duplicate.error == "terminal_plan_not_reexecuted"
    assert len(memory.list_user_facts().entries) == 1


def test_confirmation_cancel_preserves_memory_and_yes_deletes_once(tmp_path):
    service, _processor, memory = make_service(tmp_path)
    memory.remember_user_fact("one", "1")
    memory.remember_user_fact("two", "2")

    service.execute_contract(
        "составь план: покажи память; забудь всё, что ты помнишь обо мне",
        AppCommandSource.TEST,
    )
    waiting = service.execute_contract(EXECUTE, AppCommandSource.TEST)

    assert waiting.plan_status == "awaiting_confirmation"
    assert len(memory.list_user_facts().entries) == 2

    cancelled = service.execute_contract(CANCEL, AppCommandSource.TEST)
    assert cancelled.plan_status == "cancelled"
    assert len(memory.list_user_facts().entries) == 2

    service.execute_contract(
        "составь план: покажи память; забудь всё, что ты помнишь обо мне",
        AppCommandSource.TEST,
    )
    waiting_again = service.execute_contract(EXECUTE, AppCommandSource.TEST)
    deleted = service.execute_contract(YES, AppCommandSource.TEST)
    duplicate_yes = service.execute_contract(YES, AppCommandSource.TEST)

    assert deleted.operation_id == waiting_again.operation_id
    assert deleted.plan_status == "succeeded"
    assert len(memory.list_user_facts().entries) == 0
    assert duplicate_yes.operation_id != deleted.operation_id
    assert len(memory.list_user_facts().entries) == 0


def test_capability_failure_stops_later_steps_and_appservice_remains_usable(tmp_path):
    service, processor, _memory = make_service(tmp_path)

    def failing(_args):
        raise RuntimeError("raw secret sk-test123456789")

    service.planner_registry = service.planner_registry.register(
        PlanCapability(
            PlanCapabilityDescriptor(
                "test.fail",
                "Сбой",
                "Failure",
                "test",
                "read_only",
                PlanSideEffect.READ_ONLY,
                False,
                {},
                "safe failing test capability",
            ),
            failing,
            lambda args, confirmed: PolicyRequest(
                source="planner",
                command_id="test.fail",
                risk="read_only",
                required_capabilities=("read_system_state",),
                confirmation_present=True,
            ),
        )
    )
    # Build the plan directly so the production parser still rejects arbitrary user steps.
    parsed = service.multi_step_planner.create_from_text(
        "составь план: статус системы; текущий язык",
        language_code="ru-RU",
    )
    steps = list(service.multi_step_planner.steps())
    steps[1] = type(steps[1])(
        step_id=steps[1].step_id,
        position=steps[1].position,
        capability_id="test.fail",
        arguments={},
        safe_argument_summary="safe",
        requires_confirmation=False,
        risk_level="read_only",
    )
    service.plan_executor.registry = service.planner_registry
    service.multi_step_planner.registry = service.planner_registry
    service.multi_step_planner.replace_with_snapshot(parsed.snapshot, tuple(steps))

    failed = service.execute_contract(EXECUTE, AppCommandSource.TEST)
    status = service.execute_contract("статус системы", AppCommandSource.TEST)

    assert failed.plan_status == "failed"
    assert "sk-test" not in failed.safe_text_ru()
    assert processor.calls == ["статус системы", "статус системы"]
    assert status.ok is True


def test_invalid_step_rejects_full_plan_without_execution(tmp_path):
    service, processor, _memory = make_service(tmp_path)

    result = service.execute_contract(
        "составь план: статус системы; запусти неизвестную функцию; текущий язык",
        AppCommandSource.TEST,
    )

    assert result.ok is False
    assert result.error == "planner_step_unrecognized"
    assert processor.calls == []
    assert service.multi_step_planner.snapshot() is None


def test_english_plan_after_language_switch_is_english(tmp_path):
    service, processor, _memory = make_service(tmp_path)
    service.set_language_preference("en-US")

    created = service.execute_contract("create plan: system status; current language", AppCommandSource.TEST)
    executed = service.execute_contract("execute plan", AppCommandSource.TEST)

    assert "Plan created." in created.output_text
    assert "Plan completed." in executed.output_text
    assert executed.plan_status == "succeeded"
    assert processor.calls == ["статус системы"]
