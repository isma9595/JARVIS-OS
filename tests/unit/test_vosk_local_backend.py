from voice import SpeechRecognitionBackend, VoskLocalBackend, VoskSettingsManager
from unittest.mock import patch


def test_vosk_backend_defaults_are_safe():
    backend = VoskLocalBackend()

    assert isinstance(backend, SpeechRecognitionBackend)
    assert backend.backend_name == "vosk_local"
    assert backend.language == "ru"
    assert backend.model_path is None
    assert backend.installed is False
    assert backend.model_available is False
    assert backend.is_available() is False


def test_vosk_backend_reports_offline_skeleton_without_recognition():
    backend = VoskLocalBackend()
    result = backend.recognize_once()

    assert backend.supports_offline() is True
    assert backend.supports_streaming() is False
    assert backend.requires_permission() is True
    assert backend.requires_installation() is True
    assert result["intent"] == "speech.backend.unavailable"
    assert result["text"] is None
    assert result["status"]["skeleton"] is True


def test_flags_cannot_activate_skeleton():
    backend = VoskLocalBackend(
        model_path="local-placeholder",
        installed=True,
        model_available=True,
    )

    assert backend.is_available() is False
    assert backend.requires_installation() is False
    assert backend.recognize_once()["text"] is None


def test_preflight_reports_missing_dependency_and_model_path():
    backend = VoskLocalBackend()

    with patch("voice.vosk_local_backend.importlib.util.find_spec", return_value=None):
        status = backend.preflight_check()

    assert status["vosk_package_available"] is False
    assert status["dependency_available"] is False
    assert status["model_path_configured"] is False
    assert status["model_path_exists"] is False
    assert status["backend_ready_for_real_recognition"] is False
    assert status["ready"] is False
    assert status["real_recognition_enabled"] is False
    assert status["microphone_enabled"] is False
    assert status["missing_requirements"] == ["vosk_dependency", "model_path"]


def test_readiness_false_when_vosk_package_is_missing(tmp_path):
    backend = VoskLocalBackend(model_path=tmp_path)

    with patch("voice.vosk_local_backend.importlib.util.find_spec", return_value=None):
        report = backend.get_readiness_report()

    assert report["vosk_package_available"] is False
    assert report["model_path_configured"] is True
    assert report["model_path_exists"] is True
    assert report["backend_ready_for_real_recognition"] is False
    assert report["real_recognition_enabled"] is False
    assert report["missing_requirements"] == ["vosk_dependency"]


def test_readiness_false_when_model_path_is_missing():
    backend = VoskLocalBackend()

    with patch(
        "voice.vosk_local_backend.importlib.util.find_spec",
        return_value=object(),
    ):
        report = backend.get_readiness_report()

    assert report["vosk_package_available"] is True
    assert report["model_path_configured"] is False
    assert report["model_path_exists"] is False
    assert report["backend_ready_for_real_recognition"] is False
    assert report["missing_requirements"] == ["model_path"]


def test_readiness_false_when_configured_model_path_does_not_exist(tmp_path):
    missing_path = tmp_path / "missing-model"
    backend = VoskLocalBackend(model_path=missing_path)

    with patch(
        "voice.vosk_local_backend.importlib.util.find_spec",
        return_value=object(),
    ):
        report = backend.get_readiness_report()

    assert report["model_path_configured"] is True
    assert report["model_path_exists"] is False
    assert report["backend_ready_for_real_recognition"] is False
    assert report["missing_requirements"] == ["model_directory"]
    assert missing_path.exists() is False


def test_preflight_detects_dependency_and_existing_model_directory(tmp_path):
    backend = VoskLocalBackend(
        settings_manager=VoskSettingsManager(tmp_path / "vosk_settings.json")
    )
    configured = backend.configure_model_path(tmp_path)

    assert configured["model_path_configured"] is True
    assert configured["model_path_exists"] is True
    with patch(
        "voice.vosk_local_backend.importlib.util.find_spec",
        return_value=object(),
    ):
        status = backend.preflight_check()

    assert status["ready"] is True
    assert status["backend_ready_for_real_recognition"] is True
    assert status["real_recognition_enabled"] is False
    assert status["microphone_enabled"] is False
    assert status["missing_requirements"] == []
    assert backend.is_available() is False


def test_configure_model_path_does_not_create_missing_directory(tmp_path):
    missing_path = tmp_path / "not-created"
    backend = VoskLocalBackend(
        settings_manager=VoskSettingsManager(tmp_path / "vosk_settings.json")
    )

    status = backend.configure_model_path(missing_path)

    assert backend.model_path == str(missing_path)
    assert status["model_path_exists"] is False
    assert status["missing_requirements"][-1] == "model_directory"
    assert missing_path.exists() is False
