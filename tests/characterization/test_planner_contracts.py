from pathlib import Path

from app import AppCommandSource, JarvisAppService
from language.language_manager import ApplicationLanguageManager
from memory import LocalMemoryManager
from users.user_profile import UserProfileManager


RU_PLAN_FORGET_ALL_NATURAL = (
    "\u0441\u043e\u0441\u0442\u0430\u0432\u044c \u043f\u043b\u0430\u043d: "
    "\u0437\u0430\u0431\u0443\u0434\u044c \u0432\u0441\u0451, \u0447\u0442\u043e "
    "\u0442\u044b \u043e\u0431\u043e \u043c\u043d\u0435 \u043f\u043e\u043c\u043d\u0438\u0448\u044c"
)
EN_PLAN_FORGET_ALL = "create plan: forget everything you remember about me"
EXECUTE_PLAN = "execute plan"
CANCEL_PLAN = "cancel plan"
SHOW_PLAN = "show plan"


class TrackingProcessor:
    def __init__(self):
        self.calls = []
        self.user_profile = None
        self.memory_manager = None
        self.language_manager = None

    def process(self, text):
        self.calls.append(text)
        return {"response": f"processed: {text}"}


def make_service(tmp_path: Path):
    memory = LocalMemoryManager(tmp_path / "task091_memory.json")
    profile = UserProfileManager(tmp_path / "task091_profile.json")
    language = ApplicationLanguageManager.from_profile_manager(profile)
    processor = TrackingProcessor()
    return (
        JarvisAppService(
            command_processor=processor,
            memory_manager=memory,
            language_manager=language,
        ),
        processor,
        memory,
    )


def test_characterizes_current_russian_forget_all_plan_misclassification(tmp_path):
    service, processor, memory = make_service(tmp_path)
    memory.remember_user_fact("one", "1")

    created = service.execute_command(RU_PLAN_FORGET_ALL_NATURAL, AppCommandSource.TEST)
    snapshot = service.multi_step_planner.snapshot()
    steps = service.multi_step_planner.steps()

    # CHARACTERIZATION OF CURRENT BEHAVIOR: this natural Russian phrase creates
    # a bounded single-key memory.forget step instead of memory.forget_all.
    assert created.registry_match_id == "planner.general_multi_step"
    assert created.category == "planner"
    assert created.risk_level == "read_only"
    assert created.executed is False
    assert created.plan_status == "proposed"
    assert created.plan_step_count == 1
    assert snapshot is not None
    assert [step.capability_id for step in snapshot.steps] == ["memory.forget"]
    assert steps[0].arguments == {
        "key": "\u0432\u0441\u0451, \u0447\u0442\u043e \u0442\u044b \u043e\u0431\u043e \u043c\u043d\u0435 \u043f\u043e\u043c\u043d\u0438\u0448\u044c"
    }
    assert steps[0].requires_confirmation is False
    assert len(memory.list_user_facts().entries) == 1
    assert processor.calls == []


def test_characterizes_current_english_forget_all_plan_control(tmp_path):
    service, processor, memory = make_service(tmp_path)
    memory.remember_user_fact("one", "1")

    created = service.execute_command(EN_PLAN_FORGET_ALL, AppCommandSource.TEST)
    snapshot = service.multi_step_planner.snapshot()
    steps = service.multi_step_planner.steps()

    assert created.registry_match_id == "planner.general_multi_step"
    assert created.plan_status == "proposed"
    assert snapshot is not None
    assert [step.capability_id for step in snapshot.steps] == ["memory.forget_all"]
    assert steps[0].arguments == {}
    assert steps[0].requires_confirmation is True
    assert len(memory.list_user_facts().entries) == 1
    assert processor.calls == []


def test_characterizes_execute_plan_preview_confirmation_projection(tmp_path):
    service, processor, memory = make_service(tmp_path)
    memory.remember_user_fact("one", "1")
    memory.remember_user_fact("two", "2")

    created = service.execute_command(EN_PLAN_FORGET_ALL, AppCommandSource.TEST)
    preview = service.preview_command(EXECUTE_PLAN)
    preview_snapshot = service.multi_step_planner.snapshot()
    entries_after_preview = memory.list_user_facts().entries
    execution = service.execute_command(EXECUTE_PLAN, AppCommandSource.TEST)
    awaiting_snapshot = service.multi_step_planner.snapshot()
    cancelled = service.execute_command(CANCEL_PLAN, AppCommandSource.TEST)
    cancelled_snapshot = service.multi_step_planner.snapshot()
    cancelled_execute = service.execute_command(EXECUTE_PLAN, AppCommandSource.TEST)
    post_cancel_status = service.execute_command(SHOW_PLAN, AppCommandSource.TEST)
    post_cancel_snapshot = service.multi_step_planner.snapshot()

    # AUD-012 remediation: preview remains read-only but projects the next
    # effective plan step policy before execution.
    assert created.plan_status == "proposed"
    assert preview.known_command is True
    assert preview.registry_match_id == "planner.general_multi_step"
    assert preview.category == "planner"
    assert preview.risk_level == "confirmation_required"
    assert preview.read_only is False
    assert preview.requires_confirmation is True
    assert preview.requires_network is False
    assert preview.active_plan_id == created.plan_id
    assert preview.active_plan_status == "proposed"
    assert preview.active_step_id == "step-1"
    assert preview.active_step_capability_id == "memory.forget_all"
    assert preview.active_step_name is not None
    assert preview.operation_id is None
    assert preview_snapshot is not None
    assert preview_snapshot.status.value == "proposed"
    assert preview_snapshot.steps[0].capability_id == "memory.forget_all"
    assert preview_snapshot.steps[0].safe_argument_summary == EN_PLAN_FORGET_ALL.removeprefix("create plan:").strip()
    assert preview_snapshot.steps[0].risk_level == "confirmation_required"
    assert preview_snapshot.steps[0].side_effect == "bounded_local_state"
    assert len(entries_after_preview) == 2

    assert execution.registry_match_id == "planner.general_multi_step"
    assert execution.category == "planner"
    assert execution.risk_level == "planner_controlled"
    assert execution.executed is True
    assert execution.requires_confirmation is True
    assert execution.awaiting_confirmation is True
    assert execution.operation_id
    assert execution.operation_status == "awaiting_confirmation"
    assert execution.plan_status == "awaiting_confirmation"
    assert len(memory.list_user_facts().entries) == 2
    assert awaiting_snapshot is not None
    assert awaiting_snapshot.operation_id == execution.operation_id
    assert awaiting_snapshot.status.value == "awaiting_confirmation"
    assert awaiting_snapshot.awaiting_confirmation is True

    assert cancelled.operation_id == execution.operation_id
    assert cancelled.operation_status == "cancelled"
    assert cancelled.plan_status == "cancelled"
    assert cancelled.awaiting_confirmation is False
    assert cancelled_snapshot is not None
    assert cancelled_snapshot.operation_id == execution.operation_id
    assert cancelled_snapshot.status.value == "cancelled"
    assert cancelled_snapshot.awaiting_confirmation is False
    assert len(memory.list_user_facts().entries) == 2

    assert cancelled_execute.operation_id == execution.operation_id
    assert cancelled_execute.operation_status == "cancelled"
    assert cancelled_execute.plan_status == "cancelled"
    assert cancelled_execute.error == "terminal_plan_not_reexecuted"
    assert cancelled_execute.awaiting_confirmation is False
    assert len(memory.list_user_facts().entries) == 2

    assert post_cancel_status.registry_match_id == "planner.general_multi_step"
    assert post_cancel_status.operation_id == execution.operation_id
    assert post_cancel_status.operation_status == "cancelled"
    assert post_cancel_status.plan_status == "cancelled"
    assert post_cancel_status.awaiting_confirmation is False
    assert post_cancel_snapshot is not None
    assert post_cancel_snapshot.operation_id == execution.operation_id
    assert post_cancel_snapshot.status.value == "cancelled"
    assert post_cancel_snapshot.awaiting_confirmation is False
    assert len(memory.list_user_facts().entries) == 2
    assert processor.calls == []
