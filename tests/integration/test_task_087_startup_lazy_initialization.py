import json
import socket

from app.app_service import AppCommandSource, JarvisAppService
from app.desktop_shell import DesktopShellViewModel


STATUS_SYSTEM = "\u0441\u0442\u0430\u0442\u0443\u0441 \u0441\u0438\u0441\u0442\u0435\u043c\u044b"
CURRENT_LANGUAGE = "\u0442\u0435\u043a\u0443\u0449\u0438\u0439 \u044f\u0437\u044b\u043a"
SET_ENGLISH = "language english"


class CountingFactory:
    def __init__(self, value=None, error=None):
        self.value = value if value is not None else object()
        self.error = error
        self.count = 0

    def __call__(self):
        self.count += 1
        if self.error is not None:
            raise self.error
        return self.value


class FakeCommandProcessor:
    def __init__(self):
        self.calls = []
        self.user_profile = {}
        self.language_manager = None
        self.one_shot_vosk_real_recognition = None
        self.secure_provider_runtime = None

    def process(self, text):
        self.calls.append(text)
        return {
            "intent": "system.status",
            "response": "system status ok",
            "should_exit": False,
        }


class FakeProviderRuntime:
    def __init__(self):
        self.status_calls = 0

    def all_credential_statuses(self):
        self.status_calls += 1
        return ()

    def status_text_ru(self):
        self.status_calls += 1
        return "Secure provider runtime status:\n- no secrets\n- no network"


class FakeVoiceRecognition:
    def __init__(self, text=STATUS_SYSTEM):
        self.calls = 0
        self.closed = False
        self.text = text

    def run_once(self, **_kwargs):
        self.calls += 1
        return {
            "allowed": True,
            "completed": True,
            "blocked": False,
            "recognized_text": self.text,
        }

    def close(self):
        self.closed = True


def build_service(provider_factory=None, voice_factory=None):
    provider_factory = provider_factory or CountingFactory(FakeProviderRuntime())
    voice_factory = voice_factory or CountingFactory(FakeVoiceRecognition())
    service = JarvisAppService(
        command_processor=FakeCommandProcessor(),
        provider_runtime_factory=provider_factory,
        one_shot_voice_recognition_factory=voice_factory,
    )
    return service, provider_factory, voice_factory


def component_state(profile, component_id):
    for component in profile.deferred_components:
        if component.component_id == component_id:
            return component
    raise AssertionError(f"missing component {component_id}")


def test_cold_start_keeps_optional_components_deferred(monkeypatch):
    network_calls = []

    def blocked_socket(*args, **kwargs):
        network_calls.append((args, kwargs))
        raise AssertionError("network must not be used")

    monkeypatch.setattr(socket, "socket", blocked_socket)

    service, provider_factory, voice_factory = build_service()

    status = service.execute_contract(STATUS_SYSTEM, AppCommandSource.TEST)
    language = service.execute_contract(CURRENT_LANGUAGE, AppCommandSource.TEST)
    profile = service.get_startup_profile()

    assert status.ok is True
    assert language.ok is True
    assert provider_factory.count == 0
    assert voice_factory.count == 0
    assert network_calls == []
    assert component_state(profile, "secure_provider_runtime").state == "deferred"
    assert component_state(profile, "one_shot_voice_recognition").state == "deferred"
    assert service.get_language_preference().language_code == "ru-RU"


def test_diagnostics_and_preview_initialize_nothing():
    service, provider_factory, voice_factory = build_service()

    profile = service.get_startup_profile()
    text = service.startup_profile_text_ru()
    preview = service.preview_text_ru("groq real request: hello")
    command = service.execute_contract("startup profile", AppCommandSource.TEST)

    assert profile.startup_completed is True
    assert "Startup profile:" in text
    assert command.ok is True
    assert "does not execute command" in preview
    assert provider_factory.count == 0
    assert voice_factory.count == 0
    json.dumps(profile.to_dict(), sort_keys=True)


def test_language_change_does_not_initialize_provider_or_voice():
    service, provider_factory, voice_factory = build_service()

    result = service.execute_contract(SET_ENGLISH, AppCommandSource.TEST)

    assert result.ok is True
    assert service.get_language_preference().language_code == "en-US"
    assert provider_factory.count == 0
    assert voice_factory.count == 0


def test_first_provider_use_initializes_once_and_reuses_runtime():
    runtime = FakeProviderRuntime()
    provider_factory = CountingFactory(runtime)
    service, _, voice_factory = build_service(provider_factory=provider_factory)

    first = service.provider_runtime_status_text_ru()
    second = service.provider_runtime_credentials_text_ru()
    profile = service.get_startup_profile()

    assert "no secrets" in first
    assert "no network" in second
    assert provider_factory.count == 1
    assert runtime.status_calls == 2
    assert voice_factory.count == 0
    assert component_state(profile, "secure_provider_runtime").state == "ready"
    assert component_state(profile, "secure_provider_runtime").initialization_count == 1


def test_first_voice_use_initializes_voice_once_and_leaves_provider_deferred():
    recognizer = FakeVoiceRecognition()
    voice_factory = CountingFactory(recognizer)
    service, provider_factory, _ = build_service(voice_factory=voice_factory)

    first = service.process_one_shot_voice_request(AppCommandSource.TEST)
    second = service.process_one_shot_voice_request(AppCommandSource.TEST)
    profile = service.get_startup_profile()

    assert first.ok is True
    assert second.ok is True
    assert voice_factory.count == 1
    assert recognizer.calls == 2
    assert provider_factory.count == 0
    assert component_state(profile, "one_shot_voice_recognition").state == "ready"
    assert component_state(profile, "secure_provider_runtime").state == "deferred"


def test_lazy_failure_is_safe_and_status_remains_usable():
    provider_factory = CountingFactory(error=RuntimeError("raw secret sk-test-1234567890secret"))
    service, _, voice_factory = build_service(provider_factory=provider_factory)

    try:
        service.provider_runtime_status_text_ru()
    except Exception as exc:
        failure_text = str(exc)
    else:
        raise AssertionError("provider factory should fail")

    status = service.execute_contract(STATUS_SYSTEM, AppCommandSource.TEST)
    language = service.execute_contract(CURRENT_LANGUAGE, AppCommandSource.TEST)
    profile = service.get_startup_profile()

    assert "sk-test-1234567890secret" not in failure_text
    assert status.ok is True
    assert language.ok is True
    assert voice_factory.count == 0
    failed = component_state(profile, "secure_provider_runtime")
    assert failed.state == "failed"
    assert failed.error_code == "provider_runtime_initialization_failed"


def test_desktop_shell_view_model_does_not_initialize_deferred_components():
    service, provider_factory, voice_factory = build_service()

    view_model = DesktopShellViewModel(service)

    assert view_model.state.ui_ready is True
    assert "Desktop shell status:" in view_model.state.status_text
    assert provider_factory.count == 0
    assert voice_factory.count == 0
