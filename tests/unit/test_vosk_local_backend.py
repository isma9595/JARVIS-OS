from voice import SpeechRecognitionBackend, VoskLocalBackend


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
