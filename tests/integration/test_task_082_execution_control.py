from dataclasses import dataclass

from app import AppCommandSource, JarvisAppService
from app.desktop_shell import DesktopShellViewModel


STATUS_SYSTEM = "\u0441\u0442\u0430\u0442\u0443\u0441 \u0441\u0438\u0441\u0442\u0435\u043c\u044b"
SHOW_STATUS = "\u043f\u043e\u043a\u0430\u0436\u0438 \u0441\u0442\u0430\u0442\u0443\u0441"
SYSTEM_OPTION = "\u0441\u0438\u0441\u0442\u0435\u043c\u044b"
NO = "\u043d\u0435\u0442"
CANCEL = "\u043e\u0442\u043c\u0435\u043d\u0430"
DELETE_FILE = "\u0443\u0434\u0430\u043b\u0438 \u0444\u0430\u0439\u043b safe-test.txt"
DELETE_SYSTEM32 = "\u0443\u0434\u0430\u043b\u0438 System32"
PROVIDER_REQUEST = (
    "groq "
    "\u0440\u0435\u0430\u043b\u044c\u043d\u044b\u0439 "
    "\u0437\u0430\u043f\u0440\u043e\u0441: "
    "\u043f\u0440\u0438\u0432\u0435\u0442"
)
STATUS_APP_SERVICE = "\u0441\u0442\u0430\u0442\u0443\u0441 app service"


class TrackingProcessor:
    def __init__(self):
        self.calls = []
        self.action_router = CountingActionRouter()
        self.user_profile = None

    def process(self, text):
        self.calls.append(text)
        return {"intent": "test.intent", "response": f"local result: {text}"}


class CountingActionRouter:
    def __init__(self):
        self.calls = []

    def route(self, command_text, intent=None):
        self.calls.append(command_text)
        return {
            "category": "safe_action",
            "risk_level": "low",
            "allowed": True,
            "requires_confirmation": False,
            "reason": "test",
            "response": "router called",
        }


@dataclass(frozen=True)
class FakeRecognition:
    recognized_text: str
    completed: bool = True
    blocked: bool = False
    allowed: bool = True
    reasons: tuple[str, ...] = ()
    calls: int = 0

    def run_once(self, explicit_one_shot_requested=False):
        object.__setattr__(self, "calls", self.calls + 1)
        assert explicit_one_shot_requested is True
        return self

    def close(self):
        return None


def test_preview_creates_no_operation():
    service = JarvisAppService(command_processor=TrackingProcessor())

    service.preview_contract("app contracts status")

    assert service.recent_execution_operations() == ()


def test_safe_command_created_running_succeeded_and_duplicate_executes_once():
    processor = TrackingProcessor()
    service = JarvisAppService(command_processor=processor)

    first = service.execute_contract(
        "app contracts status",
        AppCommandSource.TEST,
        idempotency_key="task-082-safe",
    )
    duplicate = service.execute_contract(
        "app contracts status",
        AppCommandSource.TEST,
        idempotency_key="task-082-safe",
    )

    assert first.operation_id == duplicate.operation_id
    assert first.operation_status == "succeeded"
    assert duplicate.duplicate_suppressed is True
    assert processor.calls == ["app contracts status"]


def test_same_key_different_fingerprint_is_denied_and_executes_nothing():
    processor = TrackingProcessor()
    service = JarvisAppService(command_processor=processor)

    first = service.execute_contract(
        "app contracts status",
        AppCommandSource.TEST,
        idempotency_key="task-082-conflict",
    )
    conflict = service.execute_contract(
        STATUS_APP_SERVICE,
        AppCommandSource.TEST,
        idempotency_key="task-082-conflict",
    )

    assert first.executed is True
    assert conflict.operation_status == "denied"
    assert conflict.error == "idempotency_conflict"
    assert processor.calls == ["app contracts status"]


def test_clarification_answer_continues_same_operation():
    processor = TrackingProcessor()
    service = JarvisAppService(command_processor=processor)

    first = service.execute_contract(SHOW_STATUS, AppCommandSource.TEST)
    second = service.execute_contract(SYSTEM_OPTION, AppCommandSource.TEST)

    assert first.requires_clarification is True
    assert first.operation_status == "awaiting_clarification"
    assert second.operation_id == first.operation_id
    assert second.operation_status == "succeeded"
    assert processor.calls == [STATUS_SYSTEM]


def test_cancellation_clears_clarification_and_executes_nothing():
    processor = TrackingProcessor()
    service = JarvisAppService(command_processor=processor)

    first = service.execute_contract(SHOW_STATUS, AppCommandSource.TEST)
    cancelled = service.execute_contract(NO, AppCommandSource.TEST)

    assert cancelled.operation_id == first.operation_id
    assert cancelled.operation_status == "cancelled"
    assert processor.calls == []


def test_confirmation_then_cancel_executes_zero_action_router_calls():
    processor = TrackingProcessor()
    service = JarvisAppService(command_processor=processor)

    first = service.execute_contract(DELETE_FILE, AppCommandSource.TEST)
    cancelled = service.execute_contract(CANCEL, AppCommandSource.TEST)

    assert first.operation_status == "awaiting_confirmation"
    assert cancelled.operation_id == first.operation_id
    assert cancelled.operation_status == "cancelled"
    assert processor.calls == []
    assert processor.action_router.calls == []


def test_policy_denial_becomes_denied_journal_status():
    processor = TrackingProcessor()
    service = JarvisAppService(command_processor=processor)

    result = service.execute_contract(DELETE_SYSTEM32, AppCommandSource.TEST)
    snapshot = service.recent_execution_operations(1)[0]

    assert result.operation_status == "denied"
    assert snapshot["status"] == "denied"
    assert processor.calls == []


def test_provider_path_is_idempotency_protected_and_not_reexecuted():
    processor = TrackingProcessor()
    service = JarvisAppService(command_processor=processor)

    first = service.execute_contract(
        PROVIDER_REQUEST,
        AppCommandSource.TEST,
        idempotency_key="task-082-provider",
    )
    duplicate = service.execute_contract(
        PROVIDER_REQUEST,
        AppCommandSource.TEST,
        idempotency_key="task-082-provider",
    )

    assert first.requires_confirmation is True
    assert duplicate.duplicate_suppressed is True
    assert processor.calls == []


def test_desktop_shell_and_voice_receive_operation_metadata():
    processor = TrackingProcessor()
    service = JarvisAppService(command_processor=processor)
    shell = DesktopShellViewModel(service)

    text = shell.execute_command("app contracts status")

    assert "operation id:" not in text
    assert "operation id:" in shell.state.diagnostics_text
    assert processor.calls == ["app contracts status"]

    voice_processor = TrackingProcessor()
    voice_service = JarvisAppService(
        command_processor=voice_processor,
        one_shot_voice_recognition=FakeRecognition("app contracts status"),
    )
    voice = voice_service.process_one_shot_voice_request(AppCommandSource.TEST)

    assert voice.operation_id == voice.text_result.operation_id
    assert voice.operation_status == "succeeded"
    assert voice_processor.calls == ["app contracts status"]
