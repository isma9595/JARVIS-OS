from core.command_processor import CommandProcessor
from voice.vosk_runtime_loader import VoskRuntimeLoader


class ReadyBackend:
    def preflight_check(self):
        return {
            "vosk_package_available": True,
            "dependency_available": True,
            "model_path_configured": True,
            "model_path_exists": True,
            "backend_ready_for_real_recognition": True,
            "ready": True,
            "real_recognition_enabled": False,
            "microphone_enabled": False,
            "missing_requirements": [],
        }


class BlockedBackend:
    def preflight_check(self):
        return {
            "vosk_package_available": False,
            "dependency_available": False,
            "model_path_configured": False,
            "model_path_exists": False,
            "backend_ready_for_real_recognition": False,
            "ready": False,
            "real_recognition_enabled": False,
            "microphone_enabled": False,
            "missing_requirements": ["vosk_dependency", "model_path"],
        }


class ModelPathBlockedBackend:
    def preflight_check(self):
        return {
            "vosk_package_available": True,
            "dependency_available": True,
            "model_path_configured": False,
            "model_path_exists": False,
            "backend_ready_for_real_recognition": False,
            "ready": False,
            "real_recognition_enabled": False,
            "microphone_enabled": False,
            "missing_requirements": ["model_path"],
        }


def test_runtime_always_remains_unloaded_even_when_preflight_is_ready():
    loader = VoskRuntimeLoader(backend=ReadyBackend())

    assert loader.can_prepare_runtime() is True
    assert loader.is_runtime_loaded() is False
    status = loader.get_runtime_status()
    assert status["runtime_loaded"] is False
    assert status["backend_ready_for_real_recognition"] is True
    assert status["real_recognition_enabled"] is False
    assert status["microphone_enabled"] is False
    assert loader.prepare_runtime_stub()["prepared"] is False


def test_runtime_reports_missing_requirements_clearly():
    status = VoskRuntimeLoader(backend=BlockedBackend()).get_runtime_status()

    assert status["vosk_package_available"] is False
    assert status["model_path_configured"] is False
    assert status["model_path_exists"] is False
    assert status["backend_ready_for_real_recognition"] is False
    assert status["missing_requirements"] == ["vosk_dependency", "model_path"]
    assert status["runtime_loaded"] is False
    assert status["real_recognition_enabled"] is False


def test_blockers_include_preflight_and_stub_boundaries():
    blockers = VoskRuntimeLoader(backend=BlockedBackend()).get_blockers()

    assert "vosk_dependency" in blockers
    assert "model_path" in blockers
    assert "runtime_loading_not_implemented" in blockers
    assert "real_recognition_disabled" in blockers


def test_safety_summary_disables_all_side_effects():
    summary = VoskRuntimeLoader(backend=ReadyBackend()).get_safety_summary()

    assert all(value is False for key, value in summary.items() if key.endswith("_enabled"))


def test_recognition_stub_never_recognizes():
    result = VoskRuntimeLoader(backend=ReadyBackend()).recognize_text_stub()

    assert result["recognized"] is False
    assert result["text"] is None
    assert result["reason"] == "real_recognition_disabled"
    assert result["microphone_enabled"] is False


def test_runtime_commands_use_safe_loader_responses():
    processor = CommandProcessor(
        vosk_runtime_loader=VoskRuntimeLoader(backend=BlockedBackend())
    )

    expected_intents = {
        "runtime vosk": "speech.backend.vosk.runtime.status",
        "блокировки vosk runtime": "speech.backend.vosk.runtime.blockers",
        "безопасность runtime vosk": "speech.backend.vosk.runtime.safety",
        "подготовить runtime vosk": "speech.backend.vosk.runtime.prepare.stub",
        "распознать через vosk": (
            "speech.backend.vosk.runtime.recognition.disabled"
        ),
    }
    for command, intent in expected_intents.items():
        result = processor.process(command)
        assert result["intent"] == intent


def test_runtime_commands_return_short_russian_responses():
    processor = CommandProcessor(
        user_profile={"preferred_name": "Исмаил"},
        vosk_runtime_loader=VoskRuntimeLoader(backend=ModelPathBlockedBackend())
    )

    assert processor.process("runtime vosk")["response"] == (
        "Исмаил, Vosk runtime работает только как безопасная заглушка. Runtime "
        "не загружен, распознавание отключено, микрофон выключен."
    )
    assert processor.process("блокировки vosk runtime")["response"] == (
        "Исмаил, блокировки Vosk runtime: путь к модели не готов, загрузка "
        "runtime ещё не реализована, реальное распознавание отключено. Runtime "
        "и модель не загружались."
    )
    assert processor.process("подготовить runtime vosk")["response"] == (
        "Исмаил, я подготовил только runtime stub. Настоящий Vosk не "
        "импортировался, модель не загружалась, микрофон не включался."
    )
    assert processor.process("безопасность runtime vosk")["response"] == (
        "Исмаил, безопасность Vosk runtime: настоящий Vosk не импортируется, "
        "модель не загружается, распознавание отключено, микрофон выключен, "
        "звук не записывается."
    )
    assert processor.process("распознать через vosk")["response"] == (
        "Исмаил, распознавание через Vosk пока отключено. Микрофон не "
        "включается, аудио не читается, звук не записывается."
    )


def test_runtime_status_command_variants():
    processor = CommandProcessor(
        vosk_runtime_loader=VoskRuntimeLoader(backend=BlockedBackend())
    )

    commands = (
        "runtime vosk",
        "статус runtime vosk",
        "статус рантайм vosk",
        "runtime воск",
        "рантайм vosk",
        "рантайм воск",
    )
    for command in commands:
        assert (
            processor.process(command)["intent"]
            == "speech.backend.vosk.runtime.status"
        )


def test_runtime_blockers_command_variants():
    processor = CommandProcessor(
        vosk_runtime_loader=VoskRuntimeLoader(backend=BlockedBackend())
    )

    commands = (
        "блокировки vosk runtime",
        "блокировки рантайм vosk",
        "почему runtime vosk не готов",
        "почему рантайм vosk не готов",
        "почему vosk не запускается",
    )
    for command in commands:
        assert (
            processor.process(command)["intent"]
            == "speech.backend.vosk.runtime.blockers"
        )
