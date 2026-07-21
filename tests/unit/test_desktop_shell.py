from dataclasses import dataclass

from app.app_service import AppCommandSource, JarvisAppService
from app import desktop_shell
from app.desktop_shell import DesktopShellViewModel, JarvisDesktopShell
from memory import LocalMemoryManager


@dataclass
class FakeExecutionResult:
    ok: bool = True
    output_text: str = "processed safely"
    registry_match_id: str | None = "ai.status"
    category: str | None = "ai"
    risk_level: str | None = "read_only"
    requires_confirmation: bool = False
    network_may_be_used: bool = False
    operation_id: str | None = None
    operation_status: str | None = None
    awaiting_confirmation: bool = False
    error: str | None = None
    requires_clarification: bool = False
    clarification_question: str | None = None
    clarification_options: tuple = ()


@dataclass
class FakeVoiceResult:
    ok: bool = True
    voice_capture_succeeded: bool = True
    recognition_succeeded: bool = True
    recognized_text: str | None = "СЃС‚Р°С‚СѓСЃ ai"
    text_processing_succeeded: bool = True
    result_type: str = "text_processed"
    category: str | None = "ai"
    requires_confirmation: bool = False
    error_code: str | None = None
    user_message: str = "processed through text path"
    text_result: FakeExecutionResult | None = None
    normalized_text: str | None = None
    normalization_applied: bool = False
    normalization_rules: tuple[str, ...] = ()


class FakeAppService:
    def __init__(self):
        self.preview_calls = []
        self.execute_calls = []
        self.voice_calls = []
        self.list_calls = []

    def status_text_ru(self):
        return "\n".join(
            [
                "App service status:",
                "- enabled yes",
                "- network default: no",
                "- no secrets",
            ]
        )

    def contract_status_text_ru(self):
        return "\n".join(
            [
                "AppService contracts status:",
                "- schema name: jarvis.app_service.contracts",
                "- contract version: 0.1",
                "- network default: no",
                "- secrets included: no",
            ]
        )

    def categories_text_ru(self):
        return "Command registry categories:\n- app: 8 command(s)\n- ai: 10 command(s)\n- voice: 12 command(s)"

    def list_commands(self, category=None):
        self.list_calls.append(category)
        category_text = category or "all"
        return f"Command registry: {category_text}\n- app_service.status\n- desktop_shell.status"

    def preview_text_ru(self, text):
        self.preview_calls.append(text)
        if "groq" in text:
            return "\n".join(
                [
                    "App command preview:",
                    "- does not execute command",
                    "- command id: ai_provider.groq.real_request",
                    "- risk: network_explicit",
                    "- requires_network: yes",
                    "- requires_privacy_check: yes",
                    "- no secrets",
                ]
            )
        return "\n".join(
            [
                "App command preview:",
                "- does not execute command",
                "- command id: ai.status",
                "- risk: read_only",
                "- requires_network: no",
                "- no secrets",
            ]
        )

    def execute_command(self, text, source):
        self.execute_calls.append((text, source))
        return FakeExecutionResult(output_text=f"processed: {text}")

    def process_one_shot_voice_request(self, source):
        self.voice_calls.append(source)
        return getattr(self, "voice_result", None) or FakeVoiceResult(
            text_result=FakeExecutionResult(output_text="processed voice command")
        )


class FakeAppServiceCommandProcessor:
    def __init__(self):
        self.calls = []
        self.action_router = self.FailingActionRouter()

    class FailingActionRouter:
        def route(self, command):
            raise AssertionError("Desktop AppService test must not call ActionRouter")

    def process(self, text):
        self.calls.append(text)
        if text == "\u0441\u0442\u0430\u0442\u0443\u0441 \u043c\u0438\u043a\u0440\u043e\u0444\u043e\u043d\u0430":
            return {
                "intent": "microphone.mode.status",
                "response": "\u041c\u0438\u043a\u0440\u043e\u0444\u043e\u043d \u0432\u044b\u043a\u043b\u044e\u0447\u0435\u043d.",
            }
        if text == "task096 \u043d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u0430\u044f \u0431\u0435\u0437\u043e\u043f\u0430\u0441\u043d\u0430\u044f \u043a\u043e\u043c\u0430\u043d\u0434\u0430":
            return {
                "intent": "unknown",
                "requires_confirmation": False,
                "response": "\u041f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044c, \u044f \u043f\u043e\u043a\u0430 \u043d\u0435 \u0443\u043c\u0435\u044e \u0432\u044b\u043f\u043e\u043b\u043d\u044f\u0442\u044c \u044d\u0442\u0443 \u043a\u043e\u043c\u0430\u043d\u0434\u0443, \u043d\u043e \u043c\u043e\u0433\u0443 \u0441\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c \u0435\u0451 \u043a\u0430\u043a \u0438\u0434\u0435\u044e \u0434\u043b\u044f \u0431\u0443\u0434\u0443\u0449\u0435\u0433\u043e.",
            }
        return {"intent": "fake.intent", "response": f"processed: {text}"}


class FakeRoot:
    def __init__(self):
        self.clipboard = ""
        self.clear_calls = 0
        self.append_calls = []
        self.raise_on_get = False
        self.raise_on_set = False

    def clipboard_clear(self):
        if self.raise_on_set:
            raise RuntimeError("raw clipboard failure")
        self.clear_calls += 1
        self.clipboard = ""

    def clipboard_append(self, text):
        if self.raise_on_set:
            raise RuntimeError("raw clipboard failure")
        self.append_calls.append(text)
        self.clipboard += text

    def clipboard_get(self):
        if self.raise_on_get:
            raise RuntimeError("raw clipboard failure")
        return self.clipboard


class FakeMenu:
    def __init__(self, _parent, tearoff=0):
        self.labels = []
        self.commands = {}
        self.popup_calls = []
        self.released = False

    def add_command(self, label, command):
        self.labels.append(label)
        self.commands[label] = command

    def add_separator(self):
        self.labels.append("---")

    def tk_popup(self, x_root, y_root):
        self.popup_calls.append((x_root, y_root))

    def grab_release(self):
        self.released = True


class FakeTk:
    Menu = FakeMenu


class FakeEntry:
    def __init__(self, text=""):
        self.text = text
        self.cursor = len(text)
        self.selection = None
        self.bindings = {}

    def bind(self, sequence, callback):
        self.bindings[sequence] = callback

    def selection_get(self):
        if self.selection is None:
            raise RuntimeError("no selection")
        start, end = self.selection
        return self.text[start:end]

    def selection_range(self, start, end):
        start = 0 if start == 0 else int(start)
        end = len(self.text) if end == "end" else int(end)
        self.selection = (start, end)

    def icursor(self, index):
        self.cursor = len(self.text) if index in {"end", "insert"} else int(index)

    def delete(self, start, end=None):
        if start == "sel.first" and end == "sel.last":
            if self.selection is None:
                raise RuntimeError("no selection")
            start, end = self.selection
            self.text = self.text[:start] + self.text[end:]
            self.cursor = start
            self.selection = None
            return
        if start == 0 and end == "end":
            self.text = ""
            self.cursor = 0

    def insert(self, index, text):
        if index == "insert":
            index = self.cursor
        self.text = self.text[:index] + text + self.text[index:]
        self.cursor = index + len(text)


class FakeText:
    def __init__(self, text=""):
        self.text = text
        self.bindings = {}
        self.tags = {}
        self.state = "disabled"
        self.deleted = False
        self.inserted = []

    def bind(self, sequence, callback):
        self.bindings[sequence] = callback

    def get(self, start, end):
        if start == "sel.first" and end == "sel.last":
            selection = self.tags.get("sel")
            if selection is None:
                raise RuntimeError("no selection")
            return self.text
        return self.text

    def tag_add(self, tag, start, end):
        self.tags[tag] = (start, end)

    def mark_set(self, *_args):
        return None

    def see(self, *_args):
        return None

    def configure(self, **kwargs):
        if "state" in kwargs:
            self.state = kwargs["state"]

    def delete(self, *_args):
        self.deleted = True

    def insert(self, *_args):
        self.inserted.append(_args)


def fake_shell(root=None):
    shell = JarvisDesktopShell.__new__(JarvisDesktopShell)
    shell.root = root or FakeRoot()
    shell.tk = FakeTk
    shell.view_model = DesktopShellViewModel(FakeAppService())
    return shell


def test_view_model_builds_initial_state_safely():
    view_model = DesktopShellViewModel(FakeAppService())

    state = view_model.state

    assert state.app_title == "JARVIS OS"
    assert state.ui_ready is True
    assert state.safe_mode is True
    assert "No command has been executed" in state.output_text
    assert "desktop_shell.status" in state.command_list_text


def test_status_text_mentions_app_service_and_no_network_default():
    view_model = DesktopShellViewModel(FakeAppService())

    text = view_model.safe_status_text_ru()

    assert "app service used: yes" in text
    assert "command registry used: yes" in text
    assert "network default: no" in text
    assert "no secrets" in text
    assert "AppService contracts status:" in text


def test_list_categories_uses_app_service_registry_text():
    view_model = DesktopShellViewModel(FakeAppService())

    text = view_model.list_categories()

    assert "Command registry categories" in text
    assert "app:" in text
    assert "ai:" in text
    assert "voice:" in text


def test_list_commands_works_for_app_ai_and_voice():
    service = FakeAppService()
    view_model = DesktopShellViewModel(service)

    assert "Command registry: app" in view_model.list_commands("app")
    assert "Command registry: ai" in view_model.list_commands("ai")
    assert "Command registry: voice" in view_model.list_commands("voice")
    assert service.list_calls[-3:] == ["app", "ai", "voice"]


def test_preview_command_does_not_execute_command():
    service = FakeAppService()
    view_model = DesktopShellViewModel(service)

    text = view_model.preview_command("статус ai")

    assert "- does not execute command" in text
    assert service.preview_calls == ["статус ai"]
    assert service.execute_calls == []


def test_command_input_ctrl_v_pastes_cyrillic_and_windows_path_without_appservice_calls():
    root = FakeRoot()
    command = "\u043f\u0440\u043e\u0432\u0435\u0440\u0438\u0442\u044c \u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442 C:\\JARVIS-OS\\task084-sample.txt"
    root.clipboard = command
    shell = fake_shell(root)
    entry = FakeEntry()
    shell._bind_command_clipboard(entry)

    result = entry.bindings["<Control-v>"](None)

    assert result == "break"
    assert entry.text == command
    assert shell.view_model.app_service.preview_calls == []
    assert shell.view_model.app_service.execute_calls == []


def test_command_input_ctrl_a_selects_all_and_copy_cut_work_on_selection():
    root = FakeRoot()
    shell = fake_shell(root)
    entry = FakeEntry("\u0441\u0442\u0430\u0442\u0443\u0441 C:\\JARVIS-OS\\file.txt")
    shell._bind_command_clipboard(entry)

    assert entry.bindings["<Control-a>"](None) == "break"
    assert entry.selection == (0, len(entry.text))

    assert entry.bindings["<Control-c>"](None) == "break"
    assert root.clipboard == "\u0441\u0442\u0430\u0442\u0443\u0441 C:\\JARVIS-OS\\file.txt"
    assert entry.text == "\u0441\u0442\u0430\u0442\u0443\u0441 C:\\JARVIS-OS\\file.txt"

    assert entry.bindings["<Control-x>"](None) == "break"
    assert root.clipboard == "\u0441\u0442\u0430\u0442\u0443\u0441 C:\\JARVIS-OS\\file.txt"
    assert entry.text == ""


def test_command_input_right_click_menu_actions_are_safely_wired():
    shell = fake_shell()
    entry = FakeEntry("abc")
    shell._bind_command_clipboard(entry)
    menu = shell.command_entry_context_menu

    assert menu.labels == ["\u0412\u044b\u0440\u0435\u0437\u0430\u0442\u044c", "\u041a\u043e\u043f\u0438\u0440\u043e\u0432\u0430\u0442\u044c", "\u0412\u0441\u0442\u0430\u0432\u0438\u0442\u044c", "---", "\u0412\u044b\u0434\u0435\u043b\u0438\u0442\u044c \u0432\u0441\u0451"]
    for label in (
        "\u0412\u044b\u0440\u0435\u0437\u0430\u0442\u044c",
        "\u041a\u043e\u043f\u0438\u0440\u043e\u0432\u0430\u0442\u044c",
        "\u0412\u0441\u0442\u0430\u0432\u0438\u0442\u044c",
        "\u0412\u044b\u0434\u0435\u043b\u0438\u0442\u044c \u0432\u0441\u0451",
    ):
        assert callable(menu.commands[label])


def test_output_text_stays_read_only_but_can_select_and_copy():
    root = FakeRoot()
    shell = fake_shell(root)
    output = FakeText("\u0413\u043e\u0442\u043e\u0432\u043e\nC:\\JARVIS-OS\\task084-sample.txt")
    shell._bind_readonly_text_copy(output)

    assert output.state == "disabled"
    assert output.bindings["<Control-a>"](None) == "break"
    assert output.tags["sel"] == ("1.0", "end-1c")
    assert output.bindings["<Control-c>"](None) == "break"
    assert root.clipboard == "\u0413\u043e\u0442\u043e\u0432\u043e\nC:\\JARVIS-OS\\task084-sample.txt"
    assert output.bindings["<Key>"](None) == "break"
    assert output.state == "disabled"


def test_clipboard_errors_are_handled_without_raw_exception_or_appservice_calls():
    root = FakeRoot()
    root.raise_on_get = True
    shell = fake_shell(root)
    entry = FakeEntry()
    shell._bind_command_clipboard(entry)

    assert entry.bindings["<Control-v>"](None) == "break"
    assert entry.text == ""
    assert shell.view_model.state.last_error is None
    assert shell.view_model.app_service.preview_calls == []
    assert shell.view_model.app_service.execute_calls == []

    root.raise_on_get = False
    root.raise_on_set = True
    entry.text = "abc"
    entry.selection = (0, 3)
    assert entry.bindings["<Control-c>"](None) == "break"
    assert "raw clipboard failure" not in shell.view_model.state.output_text


def test_preview_of_status_ai_known_read_only_with_real_service():
    view_model = DesktopShellViewModel(JarvisAppService())

    text = view_model.preview_command("статус ai")

    assert "- known command: yes" in text
    assert "- command id: ai.status" in text
    assert "- risk: read_only" in text
    assert "- requires_network: no" in text


def assert_desktop_memory_preview_fields(text, *, command_id, risk):
    assert "- known command: yes" in text
    assert f"- command id: {command_id}" in text
    assert "- category: memory" in text
    assert f"- risk: {risk}" in text
    assert "- requires_network: no" in text
    assert "- requires_confirmation: no" in text
    assert "- operation id: none" in text
    assert "- executed through AppService: yes" in text


def test_desktop_shell_projects_memory_remember_preview_with_real_service(tmp_path):
    service = JarvisAppService(
        memory_manager=LocalMemoryManager(tmp_path / "desktop_preview_remember_memory.json")
    )
    view_model = DesktopShellViewModel(service)

    text = view_model.preview_command("remember that audit091key is north")

    assert_desktop_memory_preview_fields(
        text,
        command_id="memory.remember",
        risk="local_write",
    )
    assert service.memory_manager.recall_user_fact("audit091key").found is False
    assert service.recent_execution_operations(None) == ()


def test_desktop_shell_projects_memory_recall_preview_with_real_service(tmp_path):
    service = JarvisAppService(
        memory_manager=LocalMemoryManager(tmp_path / "desktop_preview_recall_memory.json")
    )
    service.memory_manager.remember_user_fact("audit091key", "north")
    view_model = DesktopShellViewModel(service)

    text = view_model.preview_command("what do you remember about audit091key")

    assert_desktop_memory_preview_fields(
        text,
        command_id="memory.recall",
        risk="read_only",
    )
    assert service.memory_manager.recall_user_fact("audit091key").value == "north"
    assert service.recent_execution_operations(None) == ()


def test_desktop_shell_projects_memory_forget_preview_with_real_service(tmp_path):
    service = JarvisAppService(
        memory_manager=LocalMemoryManager(tmp_path / "desktop_preview_forget_memory.json")
    )
    service.memory_manager.remember_user_fact("audit091key", "north")
    view_model = DesktopShellViewModel(service)

    text = view_model.preview_command("forget audit091key")

    assert_desktop_memory_preview_fields(
        text,
        command_id="memory.forget",
        risk="local_write",
    )
    assert service.memory_manager.recall_user_fact("audit091key").value == "north"
    assert service.recent_execution_operations(None) == ()


def test_desktop_shell_displays_planner_preview_with_real_service():
    view_model = DesktopShellViewModel(JarvisAppService())

    text = view_model.preview_command(
        "\u0441\u043e\u0441\u0442\u0430\u0432\u044c \u043f\u043b\u0430\u043d: \u0441\u0442\u0430\u0442\u0443\u0441 \u0441\u0438\u0441\u0442\u0435\u043c\u044b; \u0442\u0435\u043a\u0443\u0449\u0438\u0439 \u044f\u0437\u044b\u043a"
    )

    assert "- known command: yes" in text
    assert "- command id: planner.general_multi_step" in text
    assert "- category: planner" in text
    assert "- app_ready: yes" in text
    assert "- requires_network: no" in text
    assert "- requires_confirmation: no" in text


def test_desktop_shell_projects_execute_plan_confirmation_with_real_service(tmp_path):
    service = JarvisAppService(
        memory_manager=LocalMemoryManager(tmp_path / "desktop_planner_memory.json")
    )
    service.memory_manager.remember_user_fact("marker", "survives")
    view_model = DesktopShellViewModel(service)

    create_text = view_model.execute_command("create plan: forget everything you remember about me")
    preview_text = view_model.preview_command("execute plan")

    assert "plan status: proposed" in create_text.lower()
    assert "- command id: planner.general_multi_step" in preview_text
    assert "- active plan id: plan-" in preview_text
    assert "- active plan status: proposed" in preview_text
    assert "- active step id: step-1" in preview_text
    assert "- active step capability: memory.forget_all" in preview_text
    assert "- operation id: none" in preview_text
    assert "- risk: confirmation_required" in preview_text
    assert "- requires_confirmation: yes" in preview_text
    assert "- executed through AppService: yes" in preview_text
    assert "- requires_network: no" in preview_text
    assert len(service.memory_manager.list_user_facts().entries) == 1
    assert service.memory_manager.recall_user_fact("marker").found is True


def test_desktop_shell_awaiting_confirmation_plan_text_does_not_show_pending_step(tmp_path):
    service = JarvisAppService(
        memory_manager=LocalMemoryManager(tmp_path / "desktop_awaiting_message_memory.json")
    )
    service.set_language_preference("english")
    service.memory_manager.remember_user_fact("marker", "survives")
    view_model = DesktopShellViewModel(service)

    view_model.execute_command("create plan: forget everything you remember about me")
    text = view_model.execute_command("execute plan")

    assert "- plan status: awaiting_confirmation" in text
    assert "- awaiting confirmation: yes" in text
    assert "awaiting_confirmation: awaiting_confirmation" in text
    assert "awaiting_confirmation: Step is pending." not in text
    assert service.memory_manager.recall_user_fact("marker").found is True


def test_desktop_shell_projects_local_write_execute_plan_with_real_service(tmp_path):
    service = JarvisAppService(
        memory_manager=LocalMemoryManager(tmp_path / "desktop_planner_local_write_memory.json")
    )
    service.set_language_preference("english")
    view_model = DesktopShellViewModel(service)

    view_model.execute_command("create plan: remember test word north")
    preview_text = view_model.preview_command("execute plan")

    assert "- command id: planner.general_multi_step" in preview_text
    assert "- active plan id: plan-" in preview_text
    assert "- active plan status: proposed" in preview_text
    assert "- active step id: step-1" in preview_text
    assert "- active step capability: memory.remember" in preview_text
    assert "- active step name: Remember fact" in preview_text
    assert "- operation id: none" in preview_text
    assert "- risk: local_write" in preview_text
    assert "- requires_confirmation: no" in preview_text
    assert "- executed through AppService: yes" in preview_text
    assert service.memory_manager.recall_user_fact("test word").found is False


def test_desktop_shell_projects_state_changing_execution_confirmation_and_operation(tmp_path):
    service = JarvisAppService(
        memory_manager=LocalMemoryManager(tmp_path / "desktop_task096_memory.json")
    )
    view_model = DesktopShellViewModel(service)

    text = view_model.execute_command("remember that task096marker is west")

    assert "- command id: memory.remember" in text
    assert "- category: memory" in text
    assert "- risk: local_write" in text
    assert "- requires confirmation: no" in text
    assert "- operation id: op-" in text
    assert "- operation status: succeeded" in text
    assert service.memory_manager.recall_user_fact("task096marker").value == "west"


def test_desktop_shell_projects_microphone_status_confirmation_from_app_service(tmp_path):
    service = JarvisAppService(
        command_processor=FakeAppServiceCommandProcessor(),
        memory_manager=LocalMemoryManager(tmp_path / "desktop_microphone_status_memory.json"),
    )
    view_model = DesktopShellViewModel(service)

    text = view_model.execute_command(
        "\u0441\u0442\u0430\u0442\u0443\u0441 \u043c\u0438\u043a\u0440\u043e\u0444\u043e\u043d\u0430"
    )

    assert "- command id: none" in text
    assert "- category: unknown" in text
    assert "- risk: unknown" in text
    assert "- requires confirmation: no" in text
    assert "- operation status: succeeded" in text
    assert "- awaiting confirmation: yes" not in text
    assert service.memory_manager.recall_user_fact("task096marker").found is False


def test_desktop_shell_projects_unknown_fallback_confirmation_from_app_service(tmp_path):
    service = JarvisAppService(
        command_processor=FakeAppServiceCommandProcessor(),
        memory_manager=LocalMemoryManager(tmp_path / "desktop_unknown_fallback_memory.json"),
    )
    view_model = DesktopShellViewModel(service)

    text = view_model.execute_command(
        "task096 \u043d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u0430\u044f \u0431\u0435\u0437\u043e\u043f\u0430\u0441\u043d\u0430\u044f \u043a\u043e\u043c\u0430\u043d\u0434\u0430"
    )

    assert "- command id: none" in text
    assert "- category: unknown" in text
    assert "- risk: unknown" in text
    assert "- requires confirmation: no" in text
    assert "- operation status: succeeded" in text
    assert "- awaiting confirmation: yes" not in text
    assert service.memory_manager.recall_user_fact("task096marker").found is False


def test_desktop_shell_renders_positive_awaiting_confirmation_result_without_execution():
    class AwaitingConfirmationService(FakeAppService):
        def execute_command(self, text, source):
            self.execute_calls.append((text, source))
            return FakeExecutionResult(
                output_text="confirmation required",
                registry_match_id="memory.forget_all",
                category="memory",
                risk_level="confirmation_required",
                requires_confirmation=True,
                operation_id="op-awaiting",
                operation_status="awaiting_confirmation",
                awaiting_confirmation=True,
            )

    service = AwaitingConfirmationService()
    view_model = DesktopShellViewModel(service)

    text = view_model.execute_command("forget all memory")

    assert "- command id: memory.forget_all" in text
    assert "- risk: confirmation_required" in text
    assert "- requires confirmation: yes" in text
    assert "- operation id: op-awaiting" in text
    assert "- operation status: awaiting_confirmation" in text
    assert "- executed through AppService: yes" in text
    assert service.execute_calls == [("forget all memory", AppCommandSource.DESKTOP_UI)]


def test_preview_of_groq_real_request_marks_network_risk_privacy_without_execution():
    service = FakeAppService()
    view_model = DesktopShellViewModel(service)

    text = view_model.preview_command("groq реальный запрос: test")

    assert "- command id: ai_provider.groq.real_request" in text
    assert "- risk: network_explicit" in text
    assert "- requires_network: yes" in text
    assert "- requires_privacy_check: yes" in text
    assert service.execute_calls == []


def test_execute_command_calls_app_service_execute_only():
    service = FakeAppService()
    view_model = DesktopShellViewModel(service)

    text = view_model.execute_command("статус ai")

    assert service.execute_calls == [("статус ai", AppCommandSource.DESKTOP_UI)]
    assert "Desktop shell execution:" in text
    assert "- requires confirmation: no" in text
    assert "- executed through AppService: yes" in text
    assert "processed: статус ai" in text


def test_execute_command_displays_clarification_options():
    @dataclass(frozen=True)
    class Option:
        label_ru: str

    class ClarifyingService(FakeAppService):
        def execute_command(self, text, source):
            self.execute_calls.append((text, source))
            return FakeExecutionResult(
                ok=True,
                output_text="Требуется уточнение:\nКакой статус проверить?",
                registry_match_id=None,
                category="clarification",
                risk_level="read_only",
                requires_clarification=True,
                clarification_question="Какой статус проверить?",
                clarification_options=(Option("системы"), Option("AI")),
            )

    service = ClarifyingService()
    view_model = DesktopShellViewModel(service)

    text = view_model.execute_command("покажи статус")

    assert "Требуется уточнение:" in text
    assert "Какой статус проверить?" in text
    assert "- системы" in text
    assert "- AI" in text


def test_execute_command_wraps_output_safely():
    service = FakeAppService()
    view_model = DesktopShellViewModel(service)

    text = view_model.execute_command("api key sk-test-1234567890secret")

    assert "sk-test-1234567890secret" not in text
    assert "[REDACTED]" in text
    assert "- no secrets" in text


def test_process_one_shot_voice_request_uses_app_service_only():
    service = FakeAppService()
    view_model = DesktopShellViewModel(service)

    text = view_model.process_one_shot_voice_request()

    assert service.voice_calls == [AppCommandSource.DESKTOP_UI]
    assert service.execute_calls == []
    assert "Голосовой запрос Desktop Shell:" in text
    assert "- распознавание: да" in text
    assert "- распознано:" in text
    assert "processed voice command" in text
    assert "- сырое аудио отправлено наружу: нет" in text


def test_process_one_shot_voice_request_wraps_failure_safely():
    class FailingVoiceService(FakeAppService):
        def process_one_shot_voice_request(self, source):
            self.voice_calls.append(source)
            return FakeVoiceResult(
                ok=False,
                voice_capture_succeeded=False,
                recognition_succeeded=False,
                recognized_text=None,
                text_processing_succeeded=False,
                result_type="voice_recognition_failed",
                category=None,
                error_code="vosk_runtime_unavailable",
                user_message="api key sk-test-1234567890secret failed",
                text_result=None,
            )

    view_model = DesktopShellViewModel(FailingVoiceService())

    text = view_model.process_one_shot_voice_request()

    assert "vosk_runtime_unavailable" in text
    assert "sk-test-1234567890secret" not in text
    assert "[REDACTED]" in text
    assert view_model.state.last_error == text


def test_process_one_shot_voice_request_formats_cyrillic_recognition():
    service = FakeAppService()
    service.voice_result = FakeVoiceResult(
        recognized_text="статус app service",
        text_result=FakeExecutionResult(output_text="Статус готов."),
    )
    view_model = DesktopShellViewModel(service)

    text = view_model.process_one_shot_voice_request()

    assert "- распознано: статус app service" in text
    assert "Статус готов." in text
    assert "Recognized text" not in text


def test_process_one_shot_voice_request_displays_safe_normalization():
    service = FakeAppService()
    service.voice_result = FakeVoiceResult(
        recognized_text="статус система",
        normalized_text="статус системы",
        normalization_applied=True,
        normalization_rules=("normalize_system_status_phrase",),
        text_result=FakeExecutionResult(output_text="JARVIS status: ready"),
    )
    view_model = DesktopShellViewModel(service)

    text = view_model.process_one_shot_voice_request()

    assert "Распознано: статус система" in view_model.state.preview_text
    assert "Нормализовано: статус системы" in view_model.state.preview_text
    assert "Нормализовано: статус системы" in text


def test_execute_dialog_greeting_with_real_service_is_safe():
    view_model = DesktopShellViewModel(JarvisAppService())

    text = view_model.execute_command("диалог: привет")

    assert "Desktop shell execution:" in text
    assert "Привет, Исмаил" in text
    assert "providers called: no" in text
    assert "network used: no" in text
    assert "command executed: no" in text
    assert "microphone/TTS started: no" in text


def test_clear_output_works_without_execution():
    service = FakeAppService()
    view_model = DesktopShellViewModel(service)

    text = view_model.clear_output()

    assert "Output cleared" in text
    assert view_model.state.preview_text == "Command preview cleared."
    assert service.execute_calls == []


def test_launch_function_handles_unavailable_tkinter_gracefully(monkeypatch):
    def unavailable_shell(_view_model):
        raise ImportError("tkinter unavailable")

    monkeypatch.setattr(desktop_shell, "JarvisDesktopShell", unavailable_shell)

    assert desktop_shell.launch_desktop_shell() is False


def test_no_secrets_in_view_model_outputs():
    service = FakeAppService()
    view_model = DesktopShellViewModel(service)
    secret = "sk-test-1234567890secret"

    preview = view_model.preview_command(f"статус ai api_key={secret}")
    execute = view_model.execute_command(f"статус ai token={secret}")

    assert secret not in preview
    assert secret not in execute


def test_status_and_capabilities_mention_secure_key_storage_safely():
    view_model = DesktopShellViewModel(JarvisAppService())
    secret = "dummy-test-key-for-storage-only"

    status = view_model.safe_status_text_ru()
    capabilities = view_model.ui_capabilities_text_ru()

    assert "secure key storage foundation: available" in status
    assert "secure key storage foundation available" in capabilities
    assert "future secure key input UI planned" in capabilities
    assert secret not in status
    assert secret not in capabilities
