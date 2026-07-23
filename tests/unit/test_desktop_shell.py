from dataclasses import dataclass

from app.app_contracts import AppExecutionHistoryEntry, AppExecutionHistoryResult
from app.app_service import AppCommandSource, JarvisAppService
from app import desktop_shell
from app.desktop_shell import DesktopShellViewModel, JarvisDesktopShell
from core.command_processor import CommandProcessor
from memory import LocalMemoryManager
from voice.one_shot_vosk_real_recognition import OneShotVoskRealRecognitionResult
from voice.speech_synthesis_backend import SpeechSynthesisResult
from voice.voice_output_manager import VoiceOutputManager


LOCAL_TTS_STATUS_COMMAND = (
    "\u0434\u0438\u0430\u0433\u043d\u043e\u0441\u0442\u0438\u043a\u0430 "
    "\u043b\u043e\u043a\u0430\u043b\u044c\u043d\u043e\u0433\u043e "
    "\u0433\u043e\u043b\u043e\u0441\u0430"
)
LOCAL_TTS_ENABLE_COMMAND = (
    "\u0432\u043a\u043b\u044e\u0447\u0438\u0442\u044c "
    "\u043b\u043e\u043a\u0430\u043b\u044c\u043d\u044b\u0439 "
    "\u0433\u043e\u043b\u043e\u0441"
)
LOCAL_TTS_TEST_COMMAND = (
    "\u0442\u0435\u0441\u0442 "
    "\u043b\u043e\u043a\u0430\u043b\u044c\u043d\u043e\u0433\u043e "
    "\u0433\u043e\u043b\u043e\u0441\u0430"
)
RAW_MICROPHONE_ERROR = "Error querying device -1: PaErrorCode -9999; MME error 1"
RAW_HISTORY_ERROR = "Traceback RuntimeError backend failed at C:/Users/User/raw.log"


def history_entry(
    entry_id,
    *,
    timestamp="2026-07-22T10:00:00+00:00",
    status="succeeded",
    command_id="ai.status",
    action_id=None,
    operation_type=None,
    preview=False,
    request_summary="status ai",
    user_message="processed safely",
    safe_error_summary=None,
):
    success = (
        True
        if status == "succeeded"
        else False
        if status in {"failed", "denied", "cancelled"}
        else None
    )
    return AppExecutionHistoryEntry(
        entry_id=entry_id,
        timestamp=timestamp,
        updated_at=timestamp,
        source="desktop_ui",
        command_id=command_id,
        action_id=action_id,
        operation_type=operation_type or command_id or action_id or "operation",
        status=status,
        succeeded=success,
        preview=preview,
        awaiting_confirmation=status == "awaiting_confirmation",
        cancellable=status == "awaiting_confirmation",
        duplicate_suppressed=False,
        request_summary=request_summary,
        user_message=user_message,
        safe_error_summary=safe_error_summary,
        metadata=(("risk_level", "read_only"),),
    )


class FakeLocalTtsBackend:
    def __init__(self, *, available=True):
        self.available = available
        self.diagnostics_calls = 0
        self.synthesis_calls = []

    def get_name(self):
        return "windows_local_tts"

    def availability_diagnostics(self):
        self.diagnostics_calls += 1
        return {
            "available": self.available,
            "reason": "fake available" if self.available else "fake unavailable",
            "backend_name": self.get_name(),
            "network_used": False,
            "audio_file_saved": False,
        }

    def synthesize(self, text, mode="WINDOWS_LOCAL"):
        self.synthesis_calls.append((text, mode))
        return SpeechSynthesisResult(
            success=True,
            spoken_text=text,
            backend_name=self.get_name(),
            mode=mode,
            played_audio=False,
            backend_available=True,
        )


def make_local_tts_desktop_view_model(*, available=True):
    backend = FakeLocalTtsBackend(available=available)
    voice_output = VoiceOutputManager(windows_local_backend=backend)
    processor = CommandProcessor(voice_output_manager=voice_output)
    service = JarvisAppService(command_processor=processor)
    return DesktopShellViewModel(service), backend, processor


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
        self.history_calls = []
        self.history_entries = (
            history_entry(
                "op-new",
                timestamp="2026-07-22T10:02:00+00:00",
                status="failed",
                command_id="voice.test",
                request_summary="voice test",
                safe_error_summary="voice.output.local_test.failed",
            ),
            history_entry(
                "op-old",
                timestamp="2026-07-22T10:01:00+00:00",
                status="succeeded",
                command_id="ai.status",
                request_summary="status ai",
            ),
        )
        self.history_error = None

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

    def execution_history(self, limit=None):
        self.history_calls.append(limit)
        if self.history_error is not None:
            return AppExecutionHistoryResult(
                ok=False,
                entries=(),
                limit=50,
                max_limit=100,
                empty=True,
                error=self.history_error,
            )
        return AppExecutionHistoryResult(
            ok=True,
            entries=tuple(self.history_entries),
            limit=50 if limit is None else int(limit),
            max_limit=100,
            empty=not self.history_entries,
            error=None,
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


class FakeOneShotRecognition:
    def __init__(self, result):
        self.result = result
        self.calls = 0

    def run_once(self, explicit_one_shot_requested=False):
        self.calls += 1
        assert explicit_one_shot_requested is True
        return self.result


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
    assert "Execution history:" in state.history_list_text
    assert "op-new" in state.selected_history_details_text
    assert state.selected_history_id == "op-new"


def test_view_model_displays_history_entries_newest_first():
    service = FakeAppService()
    view_model = DesktopShellViewModel(service)

    text = view_model.refresh_execution_history()

    assert service.history_calls[-1] is None
    assert "1. 2026-07-22T10:02:00+00:00 | failed | voice.test" in text
    assert "2. 2026-07-22T10:01:00+00:00 | succeeded | ai.status" in text
    assert view_model.state.history_entries[0].entry_id == "op-new"
    assert view_model.state.history_entries[1].entry_id == "op-old"
    assert view_model.state.loaded_history_entries == view_model.state.history_entries
    assert view_model.state.history_result_count_text == "2 entries"


def test_view_model_refreshes_history_without_duplicates():
    service = FakeAppService()
    view_model = DesktopShellViewModel(service)
    service.history_entries = (history_entry("op-third", command_id="memory.remember"),)

    first = view_model.refresh_execution_history()
    second = view_model.refresh_execution_history()

    assert first.count("op-third") <= 1
    assert second.count("op-third") <= 1
    assert len(view_model.state.history_entries) == 1
    assert view_model.state.selected_history_id == "op-third"


def test_view_model_displays_empty_history_state():
    service = FakeAppService()
    service.history_entries = ()
    view_model = DesktopShellViewModel(service)

    assert "No execution history is available." in view_model.state.history_list_text
    assert "no entry selected" in view_model.state.selected_history_details_text
    assert view_model.state.loaded_history_entries == ()
    assert view_model.state.history_entries == ()


def test_view_model_displays_safe_history_loading_error():
    service = FakeAppService()
    service.history_error = RAW_HISTORY_ERROR
    view_model = DesktopShellViewModel(service)

    text = view_model.refresh_execution_history()

    assert "execution_history_unavailable" in text
    assert "Traceback" not in text
    assert "RuntimeError" not in text
    assert "C:/Users/User" not in text
    assert view_model.state.last_error == text


def test_view_model_updates_selected_history_details():
    view_model = DesktopShellViewModel(FakeAppService())

    details = view_model.select_history_entry(1)

    assert "op-old" in details
    assert "- command id: ai.status" in details
    assert view_model.state.selected_history_id == "op-old"


def test_view_model_history_copy_uses_safe_projected_content():
    service = FakeAppService()
    service.history_entries = (
        history_entry(
            "op-copy",
            status="failed",
            command_id="voice.test",
            request_summary="api key sk-test-1234567890secret",
            user_message="RuntimeError backend C:/Users/User/raw.log",
            safe_error_summary="PaErrorCode -9999 MME error 1",
        ),
    )
    view_model = DesktopShellViewModel(service)

    copied = view_model.selected_history_copy_text()

    assert "op-copy" in copied
    assert "sk-test-1234567890secret" not in copied
    assert "RuntimeError" not in copied
    assert "C:/Users/User" not in copied
    assert "PaErrorCode" not in copied
    assert "MME error" not in copied


def test_shell_history_copy_action_uses_selected_safe_text():
    root = FakeRoot()
    shell = fake_shell(root)

    shell._on_history_copy()

    assert root.clipboard
    assert "Execution history entry:" in root.clipboard
    assert "op-new" in root.clipboard
    assert "sk-test" not in root.clipboard


def test_view_model_malformed_history_entry_does_not_crash_rendering():
    class MalformedEntry:
        entry_id = "op-malformed"
        timestamp = "2026-07-22T10:03:00+00:00"
        status = "cancelled"
        command_id = None
        user_message = None
        safe_error_summary = None

    service = FakeAppService()
    service.history_entries = (MalformedEntry(),)
    view_model = DesktopShellViewModel(service)

    assert "op-malformed" in view_model.state.selected_history_details_text
    assert "cancelled" in view_model.state.history_list_text


def test_history_search_is_case_insensitive_and_matches_command_summary():
    service = FakeAppService()
    service.history_entries = (
        history_entry("op-doc", command_id="document.open", request_summary="Open Document"),
        history_entry("op-ai", command_id="ai.status", request_summary="status ai"),
    )
    view_model = DesktopShellViewModel(service)

    text = view_model.update_history_search(" document ")

    assert [entry.entry_id for entry in view_model.state.history_entries] == ["op-doc"]
    assert view_model.state.loaded_history_entries[1].entry_id == "op-ai"
    assert view_model.state.history_search_query == "document"
    assert view_model.state.history_result_count_text == "1 of 2 entries"
    assert "op-ai" not in text


def test_history_search_matches_operation_action_message_and_error_fields():
    service = FakeAppService()
    service.history_entries = (
        history_entry(
            "op-action",
            command_id=None,
            action_id="workflow.review",
            operation_type="document_review",
            request_summary="review request",
        ),
        history_entry("op-message", user_message="Local microphone check failed"),
        history_entry(
            "op-error",
            status="failed",
            safe_error_summary="voice.output.local_test.failed",
        ),
    )
    view_model = DesktopShellViewModel(service)

    view_model.update_history_search("DOCUMENT_REVIEW")
    assert [entry.entry_id for entry in view_model.state.history_entries] == ["op-action"]

    view_model.update_history_search("microphone")
    assert [entry.entry_id for entry in view_model.state.history_entries] == ["op-message"]

    view_model.update_history_search("LOCAL_TEST")
    assert [entry.entry_id for entry in view_model.state.history_entries] == ["op-error"]


def test_history_search_whitespace_only_behaves_as_no_filter():
    view_model = DesktopShellViewModel(FakeAppService())

    view_model.update_history_search("   ")

    assert len(view_model.state.history_entries) == 2
    assert view_model.state.history_search_query == ""
    assert view_model.state.history_result_count_text == "2 entries"


def test_history_search_missing_optional_fields_and_unsafe_details_are_safe():
    class MinimalEntry:
        entry_id = "op-minimal"
        status = None
        preview = False

    service = FakeAppService()
    service.history_entries = (
        MinimalEntry(),
        history_entry(
            "op-safe",
            status="failed",
            command_id="voice.test",
            request_summary="microphone unavailable",
            user_message="Safe execution detail unavailable.",
            safe_error_summary="Safe execution detail unavailable.",
        ),
    )
    view_model = DesktopShellViewModel(service)

    view_model.update_history_search("RuntimeError")
    assert view_model.state.history_entries == ()

    view_model.update_history_search("microphone")
    assert [entry.entry_id for entry in view_model.state.history_entries] == ["op-safe"]


def test_history_status_filter_all_and_each_supported_status():
    service = FakeAppService()
    service.history_entries = (
        history_entry("op-success", status="succeeded"),
        history_entry("op-failed", status="FAILED"),
        history_entry("op-denied", status="denied"),
        history_entry("op-cancelled", status="cancelled"),
        history_entry("op-preview", status="succeeded", preview=True),
        history_entry("op-unknown", status="mystery"),
    )
    view_model = DesktopShellViewModel(service)

    view_model.update_history_status_filter("All")
    assert [entry.entry_id for entry in view_model.state.history_entries] == [
        "op-success",
        "op-failed",
        "op-denied",
        "op-cancelled",
        "op-preview",
        "op-unknown",
    ]

    view_model.update_history_status_filter("successful")
    assert [entry.entry_id for entry in view_model.state.history_entries] == [
        "op-success",
        "op-preview",
    ]

    view_model.update_history_status_filter("Failed")
    assert [entry.entry_id for entry in view_model.state.history_entries] == ["op-failed"]

    view_model.update_history_status_filter("Denied")
    assert [entry.entry_id for entry in view_model.state.history_entries] == ["op-denied"]

    view_model.update_history_status_filter("Cancelled")
    assert [entry.entry_id for entry in view_model.state.history_entries] == [
        "op-cancelled"
    ]

    view_model.update_history_status_filter("Preview")
    assert [entry.entry_id for entry in view_model.state.history_entries] == ["op-preview"]

    view_model.update_history_status_filter("unsupported")
    assert len(view_model.state.history_entries) == 6


def test_history_status_filter_does_not_mutate_dtos():
    service = FakeAppService()
    original_entries = service.history_entries
    view_model = DesktopShellViewModel(service)

    view_model.update_history_status_filter("Failed")

    assert service.history_entries == original_entries
    assert view_model.state.loaded_history_entries == original_entries
    assert view_model.state.loaded_history_entries is not view_model.state.history_entries


def test_history_combined_search_and_status_filter_use_and_semantics():
    service = FakeAppService()
    service.history_entries = (
        history_entry("op-success-mic", status="succeeded", request_summary="microphone status"),
        history_entry("op-failed-mic", status="failed", request_summary="microphone blocked"),
        history_entry("op-failed-doc", status="failed", request_summary="document failed"),
        history_entry("op-preview-mic", status="succeeded", preview=True, request_summary="microphone preview"),
    )
    view_model = DesktopShellViewModel(service)

    view_model.update_history_status_filter("Failed")
    view_model.update_history_search("microphone")

    assert [entry.entry_id for entry in view_model.state.history_entries] == [
        "op-failed-mic"
    ]
    assert view_model.state.selected_history_id == "op-failed-mic"
    assert view_model.state.history_result_count_text == "1 of 4 entries"


def test_history_no_matches_clear_filters_and_copy_state():
    view_model = DesktopShellViewModel(FakeAppService())
    view_model.select_history_entry(1)

    text = view_model.update_history_search("value-that-does-not-exist")

    assert view_model.state.history_entries == ()
    assert view_model.state.selected_history_id is None
    assert view_model.state.history_copy_text == ""
    assert view_model.selected_history_copy_text() == ""
    assert "No history entries match the current filters." in text
    assert "No execution history is available." not in text

    view_model.clear_history_filters()

    assert view_model.state.history_search_query == ""
    assert view_model.state.history_status_filter == "All"
    assert len(view_model.state.history_entries) == 2
    assert view_model.state.selected_history_id == "op-new"
    assert view_model.state.history_result_count_text == "2 entries"


def test_history_refresh_reapplies_filters_without_duplicates_and_preserves_selection():
    service = FakeAppService()
    service.history_entries = (
        history_entry("op-keep", status="failed", request_summary="microphone failed"),
        history_entry("op-drop", status="failed", request_summary="document failed"),
    )
    view_model = DesktopShellViewModel(service)
    view_model.update_history_status_filter("Failed")
    view_model.update_history_search("microphone")
    view_model.select_history_entry(0)
    service.history_entries = (
        history_entry("op-new", status="failed", request_summary="microphone failed again"),
        history_entry("op-keep", status="failed", request_summary="microphone failed"),
        history_entry("op-success", status="succeeded", request_summary="microphone ok"),
    )

    first = view_model.refresh_execution_history()
    second = view_model.refresh_execution_history()

    assert [entry.entry_id for entry in view_model.state.history_entries] == [
        "op-new",
        "op-keep",
    ]
    assert first.count("op-keep") <= 1
    assert second.count("op-keep") <= 1
    assert view_model.state.selected_history_id == "op-keep"


def test_history_refresh_selects_first_visible_when_previous_selection_no_longer_matches():
    service = FakeAppService()
    service.history_entries = (
        history_entry("op-old", status="failed", request_summary="microphone failed"),
    )
    view_model = DesktopShellViewModel(service)
    view_model.update_history_status_filter("Failed")
    view_model.update_history_search("microphone")
    service.history_entries = (
        history_entry("op-new", status="failed", request_summary="microphone failed"),
    )

    view_model.refresh_execution_history()

    assert [entry.entry_id for entry in view_model.state.history_entries] == ["op-new"]
    assert view_model.state.selected_history_id == "op-new"


def test_history_loading_failure_remains_distinct_from_filtering_state():
    service = FakeAppService()
    service.history_error = RAW_HISTORY_ERROR
    view_model = DesktopShellViewModel(service)

    view_model.update_history_search("microphone")
    view_model.clear_history_filters()

    assert "execution_history_unavailable" in view_model.state.history_list_text
    assert view_model.state.history_load_error is not None
    assert view_model.state.history_entries == ()


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


def test_desktop_shell_projects_russian_create_plan_forget_all_confirmation(tmp_path):
    service = JarvisAppService(
        memory_manager=LocalMemoryManager(tmp_path / "desktop_russian_forget_all_memory.json")
    )
    service.memory_manager.remember_user_fact("marker", "survives")
    view_model = DesktopShellViewModel(service)

    preview_text = view_model.preview_command(
        "составь план: забудь всё, что ты обо мне помнишь"
    )
    create_text = view_model.execute_command(
        "составь план: забудь всё, что ты обо мне помнишь"
    )
    execute_text = view_model.execute_command("execute plan")
    cancel_text = view_model.execute_command("cancel plan")

    assert "- command id: planner.general_multi_step" in preview_text
    assert "- active step id: step-1" in preview_text
    assert "- active step capability: memory.forget_all" in preview_text
    assert "- operation id: none" in preview_text
    assert "- risk: confirmation_required" in preview_text
    assert "- requires_confirmation: yes" in preview_text
    assert "plan status: proposed" in create_text.lower()
    assert "- operation id: none" in create_text
    assert "- plan status: awaiting_confirmation" in execute_text
    assert "- awaiting confirmation: yes" in execute_text
    assert "- operation status: awaiting_confirmation" in execute_text
    assert "- plan status: cancelled" in cancel_text
    assert "- awaiting confirmation: yes" not in cancel_text
    assert "Memory cleared" not in preview_text
    assert "Memory cleared" not in create_text
    assert "Memory cleared" not in execute_text
    assert "Memory cleared" not in cancel_text
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


def test_desktop_shell_renders_local_tts_diagnostics_without_confirmation():
    view_model, backend, _processor = make_local_tts_desktop_view_model(available=True)

    text = view_model.execute_command(LOCAL_TTS_STATUS_COMMAND)

    assert "- ok: yes" in text
    assert "- command id: voice.output.local.status" in text
    assert "- category: voice" in text
    assert "- risk: read_only" in text
    assert "- requires confirmation: no" in text
    assert "- operation status: succeeded" in text
    assert "- awaiting confirmation: yes" not in text
    assert "- network may be used: no" in text
    assert "confirmation_required" not in text
    assert backend.diagnostics_calls == 1
    assert backend.synthesis_calls == []


def test_desktop_shell_renders_local_tts_enable_failure_as_failed_not_pending():
    view_model, backend, processor = make_local_tts_desktop_view_model(available=False)

    text = view_model.execute_command(LOCAL_TTS_ENABLE_COMMAND)

    assert "- ok: no" in text
    assert "- command id: voice.output.windows_local.enable" in text
    assert "- category: voice" in text
    assert "- risk: local_runtime" in text
    assert "- requires confirmation: no" in text
    assert "- operation status: failed" in text
    assert "- error: voice.output.windows_local.unavailable" in text
    assert "- awaiting confirmation: yes" not in text
    assert "confirmation_required" not in text
    assert processor.voice_output_manager.mode == "OFF"
    assert backend.diagnostics_calls == 1
    assert backend.synthesis_calls == []


def test_desktop_shell_renders_local_tts_test_success_without_raw_audio_text_metadata():
    view_model, backend, _processor = make_local_tts_desktop_view_model(available=True)
    view_model.execute_command(LOCAL_TTS_ENABLE_COMMAND)

    text = view_model.execute_command(LOCAL_TTS_TEST_COMMAND)

    assert "- ok: yes" in text
    assert "- command id: voice.output.spoken" in text
    assert "- category: voice" in text
    assert "- risk: local_runtime" in text
    assert "- requires confirmation: no" in text
    assert "- operation status: succeeded" in text
    assert "- awaiting confirmation: yes" not in text
    assert len(backend.synthesis_calls) == 1
    spoken_text, _mode = backend.synthesis_calls[0]
    metadata_lines = [
        line
        for line in text.splitlines()
        if line.startswith(("- command id:", "- category:", "- risk:", "- operation"))
    ]
    assert spoken_text not in "\n".join(metadata_lines)


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


def test_process_one_shot_voice_request_renders_sanitized_microphone_failure():
    recognizer = FakeOneShotRecognition(
        OneShotVoskRealRecognitionResult(
            allowed=False,
            completed=False,
            blocked=True,
            recognized_text=None,
            capture_seconds=0,
            reasons=[RAW_MICROPHONE_ERROR],
            next_steps=["Проверьте микрофон."],
        )
    )
    service = JarvisAppService(one_shot_voice_recognition=recognizer)
    view_model = DesktopShellViewModel(service)

    text = view_model.process_one_shot_voice_request()

    assert "- result type: voice_recognition_blocked" in text
    assert "- требуется подтверждение: нет" in text
    assert "Не удалось получить доступ к микрофону." in text
    assert "PaErrorCode" not in text
    assert "MME error" not in text
    assert "Error querying device" not in text
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
