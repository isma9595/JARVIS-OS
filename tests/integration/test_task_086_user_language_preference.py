from pathlib import Path

from ai.provider_contracts import AIProviderCapability, AIRequest, AIResponse
from app import AppCommandSource, JarvisAppService
from core.command_processor import CommandProcessor
from language.language_manager import ApplicationLanguageManager
from users.user_profile import UserProfileManager
from voice.one_shot_vosk_real_recognition import OneShotVoskRealRecognitionResult


class NoActionRouter:
    def __init__(self):
        self.calls = []

    def route(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        raise AssertionError("ActionRouter must not be called")


class RecordingProviderRouter:
    def __init__(self):
        self.requests = []

    def generate(self, request, capability=AIProviderCapability.CHAT):
        self.requests.append(request)
        return AIResponse(
            text="provider text",
            provider_name="dry_run",
            model_name="dry",
            capability=capability.value,
            safety_level="offline_deterministic",
        )


class NoCredentialRuntime:
    calls = []

    def __getattr__(self, name):
        def _blocked(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            raise AssertionError("credentials must not be accessed")

        return _blocked


class RecordingVoice:
    def __init__(self, allowed=False):
        self.calls = []
        self.allowed = allowed

    def run_once(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return OneShotVoskRealRecognitionResult(
            allowed=self.allowed,
            completed=self.allowed,
            blocked=not self.allowed,
            recognized_text="current language" if self.allowed else None,
            capture_seconds=0,
            reasons=[] if self.allowed else ["english model unavailable"],
            runtime_language=kwargs.get("language_code", "ru-RU"),
        )

    def close(self):
        pass


def build_service(tmp_path, provider_router=None, voice=None):
    profile = UserProfileManager(Path(tmp_path) / "profile.json")
    processor = CommandProcessor(
        user_profile_manager=profile,
        ai_provider_router=provider_router or RecordingProviderRouter(),
        secure_provider_runtime=NoCredentialRuntime(),
        one_shot_vosk_real_recognition=voice,
    )
    processor.action_router = NoActionRouter()
    manager = ApplicationLanguageManager.from_profile_manager(profile)
    return JarvisAppService(
        command_processor=processor,
        language_manager=manager,
        one_shot_voice_recognition=voice,
    ), profile, processor


def test_vertical_default_switch_persist_switch_back_invalid_and_clarification(tmp_path):
    service, profile, processor = build_service(tmp_path)

    default = service.execute_contract("текущий язык", AppCommandSource.TEST)
    assert default.ok is True
    assert "ru-RU" in default.output_text
    assert "русский" in default.output_text

    switched = service.execute_contract("язык английский", AppCommandSource.TEST)
    assert switched.ok is True
    assert "English" in switched.output_text
    assert service.get_language_preference().language_code == "en-US"

    new_service, _, _ = build_service(tmp_path)
    current = new_service.execute_contract("current language", AppCommandSource.TEST)
    assert "English" in current.output_text
    assert new_service.get_language_preference().language_code == "en-US"

    back = new_service.execute_contract("language Russian", AppCommandSource.TEST)
    assert "русский" in back.output_text
    assert new_service.get_language_preference().language_code == "ru-RU"

    invalid = new_service.execute_contract("язык немецкий", AppCommandSource.TEST)
    assert "Неподдерживаемый язык" in invalid.output_text
    assert new_service.get_language_preference().language_code == "ru-RU"

    clarification = new_service.execute_contract("поменяй язык", AppCommandSource.TEST)
    assert clarification.requires_clarification is True
    assert clarification.executed is False
    assert {option.command_text for option in clarification.clarification_options} == {
        "язык русский",
        "язык английский",
    }
    assert new_service.get_language_preference().language_code == "ru-RU"
    assert processor.action_router.calls == []


def test_preference_change_has_no_provider_network_credential_microphone_or_workflow(tmp_path):
    provider = RecordingProviderRouter()
    voice = RecordingVoice()
    service, _, processor = build_service(tmp_path, provider_router=provider, voice=voice)

    result = service.execute_contract("язык английский", AppCommandSource.TEST)

    assert result.ok is True
    assert result.network_may_be_used is False
    assert result.response_executed_as_command is False
    assert result.workflow_id is None
    assert provider.requests == []
    assert voice.calls == []
    assert processor.action_router.calls == []


def test_voice_configuration_uses_preferred_english_without_real_vosk(tmp_path):
    voice = RecordingVoice(allowed=False)
    service, _, _ = build_service(tmp_path, voice=voice)
    service.set_language_preference("en-US")

    result = service.process_one_shot_voice_request(AppCommandSource.TEST)

    assert result.ok is False
    assert result.error_code == "vosk_model_unavailable"
    assert voice.calls[0][1]["language_code"] == "en-US"


def test_provider_request_receives_preferred_language_but_is_not_triggered_by_change(tmp_path):
    provider = RecordingProviderRouter()
    service, _, processor = build_service(tmp_path, provider_router=provider)

    service.execute_contract("язык английский", AppCommandSource.TEST)
    assert provider.requests == []

    processor._generate_ai_result("hello", AIProviderCapability.CHAT, "ai.test")
    assert isinstance(provider.requests[0], AIRequest)
    assert provider.requests[0].language == "en"


def test_provider_output_is_not_executed_as_command(tmp_path):
    provider = RecordingProviderRouter()
    service, _, _ = build_service(tmp_path, provider_router=provider)

    result = service.execute_contract("текущий язык", AppCommandSource.TEST)

    assert result.response_executed_as_command is False
    assert "provider text" not in result.output_text

