from app import AppCommandSource, JarvisAppService
from app.desktop_shell import DesktopShellViewModel
from ai.provider_contracts import AIProviderCapability
from core.command_processor import CommandProcessor
from voice.one_shot_vosk_real_recognition import OneShotVoskRealRecognitionResult


class TrackingProcessor:
    def __init__(self):
        self.calls = []

    def process(self, text):
        self.calls.append(text)
        return {"intent": "test.local", "response": f"локальный результат: {text}"}


class TrackingCommandProcessor(CommandProcessor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.calls = []

    def process(self, text):
        self.calls.append(text)
        return super().process(text)


class FailingProviderRouter:
    def __init__(self):
        self.calls = []

    def generate(self, request, capability=AIProviderCapability.CHAT):
        self.calls.append(("generate", request, capability))
        raise AssertionError("provider must not be called")

    def generate_with_provider(
        self,
        provider_name,
        request,
        capability=AIProviderCapability.CHAT,
    ):
        self.calls.append(("generate_with_provider", provider_name, request, capability))
        raise AssertionError("provider must not be called")


class DeterministicRecognition:
    def __init__(self, text):
        self.text = text
        self.calls = 0
        self.closed = False

    def run_once(self, explicit_one_shot_requested=False):
        self.calls += 1
        assert explicit_one_shot_requested is True
        return OneShotVoskRealRecognitionResult(
            allowed=True,
            completed=True,
            blocked=False,
            recognized_text=self.text,
            capture_seconds=1,
        )

    def close(self):
        self.closed = True


class SpyAppService(JarvisAppService):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.execute_contract_calls = []

    def execute_contract(self, text, source=AppCommandSource.DESKTOP_UI):
        self.execute_contract_calls.append((text, source))
        return super().execute_contract(text, source)


def test_status_clarification_then_system_option_executes_once_without_provider():
    processor = TrackingProcessor()
    service = JarvisAppService(command_processor=processor)

    first = service.execute_contract("покажи статус", AppCommandSource.TEST)

    assert first.requires_clarification is True
    assert first.executed is False
    assert processor.calls == []
    assert "Какой статус проверить" in first.clarification_question

    second = service.execute_contract("системы", AppCommandSource.TEST)

    assert second.requires_clarification is False
    assert second.executed is True
    assert second.command_id == "system.status"
    assert processor.calls == ["статус системы"]
    assert "локальный результат: статус системы" in second.output_text


def test_desktop_shell_preview_execute_preview_execute_clarification_flow():
    provider = FailingProviderRouter()
    processor = TrackingCommandProcessor(ai_provider_router=provider)
    service = JarvisAppService(command_processor=processor)
    view_model = DesktopShellViewModel(service)

    first_preview = view_model.preview_command("покажи статус")
    first_execute = view_model.execute_command("покажи статус")
    state_after_execute = service._pending_clarification
    second_preview = view_model.preview_command("системы")
    state_after_preview = service._pending_clarification
    second_preview_repeat = view_model.preview_command("системы")
    state_after_repeat_preview = service._pending_clarification

    assert "does not execute command" in first_preview
    assert first_execute.count("Требуется уточнение:") == 1
    assert first_execute.count("Какой статус проверить: системы, AI, микрофона или AppService?") == 1
    for option in ("системы", "AI", "микрофона", "AppService"):
        assert first_execute.count(f"- {option}") == 1
    assert state_after_execute is not None
    assert second_preview.count("Требуется уточнение:") == 0
    assert state_after_preview == state_after_execute
    assert state_after_repeat_preview == state_after_execute
    assert second_preview_repeat == second_preview
    assert processor.calls == []
    second_execute = view_model.execute_command("системы")
    assert "система работает" in second_execute
    assert processor.calls == ["статус системы"]
    assert provider.calls == []
    assert service._pending_clarification is None


def test_desktop_shell_direct_execute_clarification_flow_without_preview():
    provider = FailingProviderRouter()
    processor = TrackingCommandProcessor(ai_provider_router=provider)
    service = JarvisAppService(command_processor=processor)
    view_model = DesktopShellViewModel(service)

    first = view_model.execute_command("покажи статус")
    second = view_model.execute_command("системы")

    assert first.count("Требуется уточнение:") == 1
    assert "система работает" in second
    assert processor.calls == ["статус системы"]
    assert provider.calls == []
    assert service._pending_clarification is None


def test_desktop_shell_cancellation_after_preview_clears_clarification():
    processor = TrackingCommandProcessor()
    service = JarvisAppService(command_processor=processor)
    view_model = DesktopShellViewModel(service)

    view_model.execute_command("покажи статус")
    view_model.preview_command("не надо")
    result = view_model.execute_command("не надо")

    assert "Уточнение отменено" in result
    assert processor.calls == []
    assert service._pending_clarification is None


def test_desktop_shell_dangerous_confirmation_state_stays_separate():
    processor = TrackingCommandProcessor()
    service = JarvisAppService(command_processor=processor)
    view_model = DesktopShellViewModel(service)

    view_model.execute_command("покажи статус")
    result = view_model.execute_command("сбросить имя ассистента")

    assert "Требуется подтверждение" in result
    assert "Требуется уточнение:" not in result
    assert service._pending_clarification is None
    assert processor.calls == []


def test_clarification_state_is_single_use_and_unrelated_text_does_not_select_option():
    processor = TrackingProcessor()
    service = JarvisAppService(command_processor=processor)

    service.execute_contract("покажи статус", AppCommandSource.TEST)
    unrelated = service.execute_contract("привет", AppCommandSource.TEST)
    after = service.execute_contract("системы", AppCommandSource.TEST)

    assert unrelated.executed is False
    assert unrelated.category == "conversation"
    assert after.executed is False
    assert after.category == "unsupported"
    assert processor.calls == []


def test_clarification_cancellation_clears_state_without_execution():
    processor = TrackingProcessor()
    service = JarvisAppService(command_processor=processor)

    service.execute_contract("какой статус", AppCommandSource.TEST)
    cancelled = service.execute_contract("не надо", AppCommandSource.TEST)

    assert cancelled.executed is False
    assert cancelled.requires_clarification is False
    assert "Уточнение отменено" in cancelled.output_text
    assert processor.calls == []


def test_clarification_confirmation_word_does_not_select_option():
    processor = TrackingProcessor()
    service = JarvisAppService(command_processor=processor)

    service.execute_contract("покажи статус", AppCommandSource.TEST)
    result = service.execute_contract("подтверждаю", AppCommandSource.TEST)

    assert result.command_id is None
    assert processor.calls == ["подтверждаю"]
    assert "статус системы" not in processor.calls


def test_vague_risky_delete_is_not_executed():
    processor = TrackingProcessor()
    service = JarvisAppService(command_processor=processor)

    result = service.execute_contract("удали это", AppCommandSource.TEST)

    assert result.executed is False
    assert result.category == "unsupported"
    assert processor.calls == []


def test_question_about_delete_is_conversation_and_creates_no_confirmation():
    processor = TrackingProcessor()
    service = JarvisAppService(command_processor=processor)

    result = service.execute_contract("можно ли удалить файл", AppCommandSource.TEST)

    assert result.executed is False
    assert result.category == "conversation"
    assert result.requires_confirmation is False
    assert service._pending_clarification is None
    assert processor.calls == []


def test_exact_risky_command_retains_existing_confirmation_path():
    service = JarvisAppService(
        command_processor=CommandProcessor(ai_provider_router=FailingProviderRouter())
    )

    result = service.execute_contract("удали файл test.txt", AppCommandSource.TEST)

    assert result.requires_confirmation is True
    assert result.network_may_be_used is False
    assert "подтверж" in result.output_text.lower()


def test_risky_misspelling_is_not_repaired_or_executed():
    processor = TrackingProcessor()
    service = JarvisAppService(command_processor=processor)

    result = service.execute_contract("удали фал", AppCommandSource.TEST)

    assert result.executed is False
    assert result.category == "unsupported"
    assert processor.calls == []


def test_provider_prompt_remains_unchanged_and_not_reexecuted_as_command():
    processor = TrackingProcessor()
    service = JarvisAppService(command_processor=processor)
    prompt = "groq реальный запрос: ответь про https://example.test user@example.test"

    result = service.execute_contract(prompt, AppCommandSource.TEST)

    assert result.input_text == prompt
    assert result.command_id == "ai_provider.groq.real_request"
    assert result.requires_confirmation is True
    assert result.executed is False
    assert result.response_executed_as_command is False
    assert processor.calls == []


def test_voice_path_uses_appservice_and_task_079_normalization_remains_compatible():
    processor = TrackingProcessor()
    recognizer = DeterministicRecognition("статус система")
    service = SpyAppService(
        command_processor=processor,
        one_shot_voice_recognition=recognizer,
    )

    result = service.process_one_shot_voice_request(AppCommandSource.TEST)

    assert service.execute_contract_calls == [("статус системы", AppCommandSource.TEST)]
    assert processor.calls == ["статус системы"]
    assert result.normalization_applied is True
    assert result.text_result.command_id == "system.status"
    assert result.raw_audio_included is False


def test_ambiguous_request_performs_zero_execution_and_serializes_cyrillic():
    processor = TrackingProcessor()
    service = JarvisAppService(command_processor=processor)

    result = service.execute_contract("покажи статус", AppCommandSource.TEST)
    data = result.to_dict()

    assert result.executed is False
    assert result.requires_clarification is True
    assert data["clarification_options"][0]["label_ru"] == "системы"
    assert processor.calls == []
