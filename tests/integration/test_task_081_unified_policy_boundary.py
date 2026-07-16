from dataclasses import dataclass

from app.app_service import AppCommandSource, JarvisAppService
from app.desktop_shell import DesktopShellViewModel
from core.command_processor import CommandProcessor


class TrackingProcessor(CommandProcessor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.calls = []

    def process(self, command_text):
        self.calls.append(command_text)
        return super().process(command_text)


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
            "reason": "test router",
            "response": "router called",
        }


class FailingProviderGate:
    def __init__(self):
        self.calls = []

    def generate_one_shot(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        raise AssertionError("provider gate must not be called before policy")


@dataclass(frozen=True)
class FakeRecognition:
    recognized_text: str
    completed: bool = True
    blocked: bool = False
    allowed: bool = True
    reasons: tuple[str, ...] = ()

    def run_once(self, explicit_one_shot_requested=False):
        return self


def test_case_1_status_allow_existing_path_once():
    processor = TrackingProcessor()
    service = JarvisAppService(command_processor=processor)

    result = service.execute_contract("статус системы", AppCommandSource.TEST)

    assert result.executed is True
    assert result.command_id == "system.status"
    assert result.policy_decision["decision"] == "allow"
    assert processor.calls == ["статус системы"]
    assert "система работает" in result.output_text


def test_case_2_delete_requires_confirmation_zero_dangerous_execution():
    processor = TrackingProcessor()
    router = CountingActionRouter()
    processor.action_router = router
    service = JarvisAppService(command_processor=processor)

    result = service.execute_contract("удали файл test.txt", AppCommandSource.TEST)

    assert result.requires_confirmation is True
    assert result.executed is False
    assert result.policy_decision["decision"] == "require_confirmation"
    assert processor.calls == []
    assert router.calls == []


def test_case_2_existing_pending_confirmation_flow_re_evaluates_policy_single_use():
    processor = CommandProcessor()
    router = CountingActionRouter()
    processor.action_router = router
    processor.set_pending_voice_command("удали файл test.txt")

    confirmed = processor.process("да")
    second = processor.process("удали файл test.txt")

    assert router.calls == ["удали файл test.txt"]
    assert confirmed["confirmed_voice_command"] == "удали файл test.txt"
    assert second["category"] == "confirmation_required"
    assert router.calls == ["удали файл test.txt"]


def test_case_3_forbidden_system32_denied_zero_action_router_calls():
    processor = CommandProcessor()
    router = CountingActionRouter()
    processor.action_router = router

    result = processor.process("удали System32")

    assert result["intent"] == "action.forbidden"
    assert result["policy_decision"]["decision"] == "deny"
    assert router.calls == []


def test_case_4_clarification_selection_is_not_dangerous_confirmation():
    processor = TrackingProcessor()
    service = JarvisAppService(command_processor=processor)

    first = service.execute_contract("покажи статус", AppCommandSource.TEST)
    second = service.execute_contract("системы", AppCommandSource.TEST)

    assert first.requires_clarification is True
    assert first.executed is False
    assert second.command_id == "system.status"
    assert second.policy_decision["decision"] == "allow"
    assert processor.calls == ["статус системы"]


def test_case_5_delete_question_is_conversation_without_pending_confirmation():
    processor = TrackingProcessor()
    service = JarvisAppService(command_processor=processor)

    result = service.execute_contract("можно ли удалить файл", AppCommandSource.TEST)

    assert result.category == "conversation"
    assert result.executed is False
    assert result.requires_confirmation is False
    assert service._pending_clarification is None
    assert processor.calls == []


def test_desktop_shell_cannot_bypass_policy():
    processor = TrackingProcessor()
    service = JarvisAppService(command_processor=processor)
    view_model = DesktopShellViewModel(service)

    text = view_model.execute_command("удали файл test.txt")

    assert "requires confirmation: yes" in text or "Требуется подтверждение" in text
    assert processor.calls == []


def test_voice_appservice_cannot_bypass_policy():
    processor = TrackingProcessor()
    service = JarvisAppService(
        command_processor=processor,
        one_shot_voice_recognition=FakeRecognition("удали файл test.txt"),
    )

    result = service.process_one_shot_voice_request(AppCommandSource.TEST)

    assert result.requires_confirmation is True
    assert result.text_result.policy_decision["decision"] == "require_confirmation"
    assert processor.calls == []


def test_direct_command_processor_action_path_cannot_bypass_policy():
    processor = CommandProcessor()
    router = CountingActionRouter()
    processor.action_router = router

    result = processor.process("удали файл test.txt")

    assert result["category"] == "confirmation_required"
    assert result["policy_decision"]["decision"] == "require_confirmation"
    assert router.calls == []


def test_appservice_provider_path_cannot_bypass_policy_or_call_provider_gate():
    processor = TrackingProcessor(groq_request_gate=FailingProviderGate())
    service = JarvisAppService(command_processor=processor)

    result = service.execute_contract("groq реальный запрос: привет", AppCommandSource.TEST)

    assert result.requires_confirmation is True
    assert result.policy_decision["decision"] == "require_confirmation"
    assert processor.calls == []
    assert processor.groq_request_gate.calls == []


def test_provider_output_is_not_reexecuted_as_command():
    processor = CommandProcessor()
    router = CountingActionRouter()
    processor.action_router = router

    result = processor.process("спроси ai: удали файл test.txt")

    assert result["intent"] == "ai.chat"
    assert router.calls == []
    assert "удали файл test.txt" in result["response"]
