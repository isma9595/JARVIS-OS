from app import AppCommandSource, JarvisAppService
from ai.provider_contracts import AIProviderCapability, AIProviderSafetyLevel
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
        self.desktop_turn_calls = []

    def handle_desktop_turn(
        self,
        text,
        source=AppCommandSource.DESKTOP_UI,
        *,
        session_id=None,
        idempotency_key=None,
    ):
        self.desktop_turn_calls.append((text, source, session_id))
        return super().handle_desktop_turn(
            text,
            source,
            session_id=session_id,
            idempotency_key=idempotency_key,
        )


class FakeRussianProviderRouter:
    def __init__(self):
        self.requests = []

    def generate(self, request, capability=AIProviderCapability.CHAT):
        self.requests.append((request, capability))
        return type(
            "Response",
            (),
            {
                "text": "Русский ответ от fake provider.",
                "provider_name": "fake",
                "model_name": "fake-russian-model",
                "capability": capability.value,
                "safety_level": AIProviderSafetyLevel.OFFLINE_DETERMINISTIC.value,
                "is_error": False,
                "error_message": None,
            },
        )()

    def generate_with_provider(
        self,
        provider_name,
        request,
        capability=AIProviderCapability.CHAT,
    ):
        return self.generate(request, capability=capability)


def test_one_shot_voice_vertical_russian_local_command_reaches_normal_text_path():
    recognizer = DeterministicRecognition("статус app service")
    service = SpyAppService(
        command_processor=CommandProcessor(),
        one_shot_voice_recognition=recognizer,
    )

    result = service.process_one_shot_voice_request(AppCommandSource.TEST)

    assert result.ok is True
    assert result.recognition_succeeded is True
    assert result.recognized_text == "статус app service"
    assert service.desktop_turn_calls == [
        ("статус app service", AppCommandSource.TEST, None)
    ]
    assert result.text_result is not None
    assert result.text_result.command_id == "app_service.status"
    assert result.text_result.network_may_be_used is False
    assert "App service status:" in result.text_result.output_text
    assert recognizer.closed is True
    assert service.audio_lifecycle_status().one_shot_active is False


def test_one_shot_voice_vertical_russian_provider_question_uses_fake_transport():
    recognizer = DeterministicRecognition("спроси ai: какая сегодня задача?")
    fake_router = FakeRussianProviderRouter()
    processor = CommandProcessor(ai_provider_router=fake_router)
    service = SpyAppService(
        command_processor=processor,
        one_shot_voice_recognition=recognizer,
    )

    result = service.process_one_shot_voice_request(AppCommandSource.TEST)

    assert result.ok is True
    assert result.recognized_text == "спроси ai: какая сегодня задача?"
    assert service.desktop_turn_calls == [
        ("спроси ai: какая сегодня задача?", AppCommandSource.TEST, None)
    ]
    assert result.text_result is not None
    assert result.text_result.output_text == "Русский ответ от fake provider."
    assert fake_router.requests
    request, capability = fake_router.requests[0]
    assert request.prompt == "какая сегодня задача?"
    assert request.language == "ru"
    assert capability == AIProviderCapability.CHAT
    assert recognizer.closed is True


def test_one_shot_voice_vertical_russian_dry_run_preserves_cyrillic():
    recognizer = DeterministicRecognition("спроси ai: привет")
    service = SpyAppService(
        command_processor=CommandProcessor(),
        one_shot_voice_recognition=recognizer,
    )

    result = service.process_one_shot_voice_request(AppCommandSource.TEST)

    assert result.ok is True
    assert result.recognized_text == "спроси ai: привет"
    assert service.desktop_turn_calls == [
        ("спроси ai: привет", AppCommandSource.TEST, None)
    ]
    assert result.text_result is not None
    assert result.text_result.network_may_be_used is False
    assert "привет" in result.text_result.output_text
    assert "privet" not in result.safe_text_ru().lower()
    assert recognizer.closed is True


def test_one_shot_voice_vertical_russian_confirmation_required_is_not_executed():
    phrase = "сбросить имя ассистента"
    recognizer = DeterministicRecognition(phrase)
    service = SpyAppService(
        command_processor=CommandProcessor(),
        one_shot_voice_recognition=recognizer,
    )

    result = service.process_one_shot_voice_request(AppCommandSource.TEST)

    assert result.ok is True
    assert result.requires_confirmation is True
    assert result.result_type == "confirmation_required"
    assert result.recognized_text == phrase
    assert service.desktop_turn_calls == [(phrase, AppCommandSource.TEST, None)]
    assert result.text_result is not None
    assert result.text_result.requires_confirmation is True
    assert result.text_result.executed is False
