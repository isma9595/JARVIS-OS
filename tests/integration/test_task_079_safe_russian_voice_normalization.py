from app import AppCommandSource, JarvisAppService
from ai.provider_contracts import AIProviderCapability
from core.command_processor import CommandProcessor
from voice.one_shot_vosk_real_recognition import OneShotVoskRealRecognitionResult


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


class FailingProviderRouter:
    def generate(self, request, capability=AIProviderCapability.CHAT):
        raise AssertionError("provider must not be called")

    def generate_with_provider(
        self,
        provider_name,
        request,
        capability=AIProviderCapability.CHAT,
    ):
        raise AssertionError("provider must not be called")


class FailingActionRouter:
    def route(self, command):
        raise AssertionError("ActionRouter must not be called for normalized status")


def test_task_079_normalized_status_system_reaches_existing_local_appservice_path():
    recognizer = DeterministicRecognition("статус система")
    processor = CommandProcessor(ai_provider_router=FailingProviderRouter())
    processor.action_router = FailingActionRouter()
    service = SpyAppService(
        command_processor=processor,
        one_shot_voice_recognition=recognizer,
    )

    result = service.process_one_shot_voice_request(AppCommandSource.TEST)

    assert recognizer.calls == 1
    assert recognizer.closed is True
    assert service.execute_contract_calls == [("статус системы", AppCommandSource.TEST)]
    assert result.ok is True
    assert result.recognized_text == "статус система"
    assert result.normalized_text == "статус системы"
    assert result.normalization_applied is True
    assert "normalize_system_status_phrase" in result.normalization_rules
    assert result.text_result is not None
    assert result.text_result.command_id == "system.status"
    assert result.text_result.network_may_be_used is False
    assert "система работает" in result.text_result.output_text
    assert "статус система" in result.safe_text_ru()
    assert "статус системы" in result.safe_text_ru()


def test_task_079_risky_misspelling_is_not_repaired_or_dangerously_executed():
    recognizer = DeterministicRecognition("удали фал")
    processor = CommandProcessor(ai_provider_router=FailingProviderRouter())
    service = SpyAppService(
        command_processor=processor,
        one_shot_voice_recognition=recognizer,
    )

    result = service.process_one_shot_voice_request(AppCommandSource.TEST)

    assert service.execute_contract_calls == [("удали фал", AppCommandSource.TEST)]
    assert result.recognized_text == "удали фал"
    assert result.normalized_text == "удали фал"
    assert result.normalization_applied is False
    assert result.text_result is not None
    assert result.text_result.command_id is None
    assert result.text_result.input_text == "удали фал"
    assert result.text_result.network_may_be_used is False
    assert "статус системы" not in result.text_result.input_text


def test_task_079_exact_typed_command_behavior_remains_unchanged():
    processor = CommandProcessor(ai_provider_router=FailingProviderRouter())
    service = JarvisAppService(command_processor=processor)

    typed_result = service.execute_contract("статус система", AppCommandSource.TEST)

    assert typed_result.input_text == "статус система"
    assert typed_result.command_id is None
    assert typed_result.network_may_be_used is False


def test_task_079_confirmation_and_forbidden_behavior_remain_on_existing_path():
    processor = CommandProcessor(ai_provider_router=FailingProviderRouter())
    service = JarvisAppService(command_processor=processor)

    confirmation = service.execute_contract(
        "сбросить имя ассистента",
        AppCommandSource.TEST,
    )
    forbidden = service.execute_contract("удали system32", AppCommandSource.TEST)

    assert confirmation.requires_confirmation is True
    assert confirmation.executed is False
    assert forbidden.command_id is None
    assert forbidden.network_may_be_used is False
    assert forbidden.requires_confirmation is True
    assert "не могу выполнить" in forbidden.output_text.lower()


def test_task_079_voice_result_serialization_remains_backward_compatible():
    recognizer = DeterministicRecognition("статус система")
    service = SpyAppService(
        command_processor=CommandProcessor(ai_provider_router=FailingProviderRouter()),
        one_shot_voice_recognition=recognizer,
    )

    data = service.process_one_shot_voice_request(AppCommandSource.TEST).to_dict()

    assert data["recognized_text"] == "статус система"
    assert data["normalized_text"] == "статус системы"
    assert data["normalization_applied"] is True
    assert isinstance(data["normalization_rules"], tuple)
    assert data["raw_audio_included"] is False
    assert data["provider_objects_included"] is False
