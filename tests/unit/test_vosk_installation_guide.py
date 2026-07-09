import sys
from types import SimpleNamespace
from unittest.mock import patch

from core.command_processor import CommandProcessor
from voice.vosk_installation_guide import VoskInstallationGuide


def test_python_version_status_uses_current_interpreter():
    status = VoskInstallationGuide().get_python_version_status()

    assert status["python_version"] == (
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )
    assert status["official_supported_range"] == "3.5-3.9"
    assert isinstance(status["is_likely_compatible"], bool)


def test_python_39_is_likely_compatible_and_newer_version_warns():
    guide = VoskInstallationGuide()

    with patch(
        "voice.vosk_installation_guide.sys.version_info",
        SimpleNamespace(major=3, minor=9, micro=18),
    ):
        compatible = guide.get_python_version_status()
    with patch(
        "voice.vosk_installation_guide.sys.version_info",
        SimpleNamespace(major=3, minor=12, micro=1),
    ):
        unsupported = guide.get_python_version_status()

    assert compatible["is_likely_compatible"] is True
    assert unsupported["is_likely_compatible"] is False
    assert "отдельный совместимый venv" in unsupported["message"]


def test_install_command_is_text_only():
    command = VoskInstallationGuide().get_pip_install_command()

    assert command["command"] == "python -m pip install vosk"
    assert command["minimum_pip_version"] == "20.3"
    assert command["execute_automatically"] is False


def test_recommended_model_and_download_guidance_are_informational():
    guide = VoskInstallationGuide()
    model = guide.get_recommended_model()
    guidance = guide.get_model_download_guidance()

    assert model["name"] == "vosk-model-small-ru-0.22"
    assert model["download_automatically"] is False
    assert guidance["network_access_performed"] is False
    assert guidance["files_changed"] is False


def test_public_status_keeps_all_runtime_capabilities_disabled():
    status = VoskInstallationGuide().get_public_status()

    assert status["mode"] == "information_only"
    assert status["automatic_installation"] is False
    assert status["runtime_enabled"] is False
    assert status["microphone_enabled"] is False
    assert status["audio_recording_enabled"] is False
    assert status["network_access_enabled"] is False


def test_safe_enablement_plan_recommends_isolation():
    guide = VoskInstallationGuide()

    assert any("отдельный venv" in step for step in guide.get_safe_enablement_steps())
    assert guide.get_runtime_risks()
    assert guide.get_installation_summary()["automatic_installation"] is False


def test_real_vosk_information_commands_are_routed():
    processor = CommandProcessor()
    expected_intents = {
        "инструкция vosk": "speech.backend.vosk.installation.guide",
        "совместимость vosk": "speech.backend.vosk.compatibility",
        "план подключения vosk": "speech.backend.vosk.enablement.plan",
        "риски vosk": "speech.backend.vosk.risks",
        "какую модель vosk скачать": "speech.backend.vosk.model.guide",
    }

    for command, expected_intent in expected_intents.items():
        assert processor.process(command)["intent"] == expected_intent


def test_vosk_information_command_aliases_are_routed():
    processor = CommandProcessor()
    aliases = {
        "проверить совместимость vosk": "speech.backend.vosk.compatibility",
        "python vosk": "speech.backend.vosk.compatibility",
        "версия python vosk": "speech.backend.vosk.compatibility",
        "совместимость воск": "speech.backend.vosk.compatibility",
        "безопасный план vosk": "speech.backend.vosk.enablement.plan",
        "подключить vosk план": "speech.backend.vosk.enablement.plan",
        "план воск": "speech.backend.vosk.enablement.plan",
        "риски подключения vosk": "speech.backend.vosk.risks",
        "опасности vosk": "speech.backend.vosk.risks",
        "риски воск": "speech.backend.vosk.risks",
    }

    for command, expected_intent in aliases.items():
        assert processor.process(command)["intent"] == expected_intent


def test_vosk_installation_response_does_not_repeat_venv_recommendation():
    response = CommandProcessor().process("инструкция vosk")["response"]

    recommendation = "рекомендуется отдельный совместимый venv."
    assert response.lower().count(recommendation) <= 1
