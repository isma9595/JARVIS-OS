from voice import NoSpeechRecognitionBackend, SpeechRecognitionBackend


def test_base_backend_is_safe_and_not_implemented():
    backend = SpeechRecognitionBackend()

    assert backend.get_name() == "base"
    assert backend.is_available() is False
    assert backend.requires_permission() is False
    assert backend.requires_installation() is False
    assert backend.supports_streaming() is False
    assert backend.supports_offline() is False
    assert backend.recognize_once()["intent"] == "speech.backend.not_implemented"
    assert backend.recognize_once()["text"] is None


def test_none_backend_is_unavailable_and_does_not_recognize():
    backend = NoSpeechRecognitionBackend()

    assert backend.get_name() == "none"
    assert backend.is_available() is False
    assert backend.get_status()["available"] is False
    assert backend.recognize_once()["intent"] == "speech.backend.unavailable"
    assert backend.recognize_once()["text"] is None
