from voice import MicrophoneInputAdapter, NoSpeechRecognitionBackend


def test_default_speech_backend_is_safe_and_listen_once_delegates():
    adapter = MicrophoneInputAdapter()

    assert isinstance(adapter.get_speech_backend(), NoSpeechRecognitionBackend)
    assert adapter.get_speech_backend_name() == "none"
    assert adapter.speech_backend_status()["available"] is False
    assert adapter.listen_once()["intent"] == "speech.backend.unavailable"


def test_speech_backend_can_be_replaced():
    class StubBackend(NoSpeechRecognitionBackend):
        def get_name(self):
            return "stub"

        def recognize_once(self):
            return {"intent": "stub.result", "text": "safe"}

    adapter = MicrophoneInputAdapter()
    status = adapter.set_speech_backend(StubBackend())

    assert status["name"] == "stub"
    assert adapter.get_speech_backend_name() == "stub"
    assert adapter.listen_once()["intent"] == "stub.result"


def test_initial_state_is_disabled():
    adapter = MicrophoneInputAdapter()

    assert adapter.state == "disabled"
    assert adapter.get_state() == "disabled"
    assert adapter.permission_granted is False
    assert adapter.backend_name == "none"
    assert adapter.last_error is None


def test_status_contains_safe_backend_metadata():
    adapter = MicrophoneInputAdapter()

    assert adapter.get_status() == {
        "state": "disabled",
        "permission_granted": False,
        "backend_name": "none",
        "last_error": None,
        "backend_available": False,
    }


def test_request_permission_does_not_enable_microphone():
    adapter = MicrophoneInputAdapter()

    status = adapter.request_permission()

    assert status["state"] == "permission_required"
    assert adapter.permission_granted is False
    assert adapter.backend_name == "none"


def test_grant_permission_is_logical_only():
    adapter = MicrophoneInputAdapter()

    status = adapter.grant_permission()

    assert status["state"] == "ready"
    assert adapter.permission_granted is True
    assert adapter.backend_name == "none"
    assert adapter.last_error is None


def test_enable_requires_permission_first():
    adapter = MicrophoneInputAdapter()

    status = adapter.enable()

    assert status["state"] == "permission_required"
    assert adapter.permission_granted is False


def test_start_listening_requires_permission():
    adapter = MicrophoneInputAdapter()

    status = adapter.start_listening()

    assert status["state"] == "permission_required"
    assert status["last_error"] == "microphone permission is required"
    assert adapter.permission_granted is False


def test_start_listening_without_backend_does_not_enable_microphone():
    adapter = MicrophoneInputAdapter()
    adapter.grant_permission()

    listening_status = adapter.start_listening()
    stopped_status = adapter.stop_listening()

    assert listening_status["state"] == "unavailable"
    assert listening_status["backend_name"] == "none"
    assert listening_status["backend_available"] is False
    assert listening_status["last_error"] == "speech recognition backend is not connected"
    assert stopped_status["state"] == "ready"


def test_read_text_reports_missing_backend_without_recognition():
    adapter = MicrophoneInputAdapter()
    adapter.grant_permission()

    result = adapter.read_text()

    assert result["text"] is None
    assert result["state"] == "unavailable"
    assert result["backend_name"] == "none"
    assert result["last_error"] == "speech recognition backend is not connected"


def test_disable_keeps_logical_permission_but_stops_adapter_state():
    adapter = MicrophoneInputAdapter()
    adapter.grant_permission()
    adapter.start_listening()

    status = adapter.disable()

    assert status["state"] == "disabled"
    assert status["permission_granted"] is True


def test_revoke_permission_returns_to_disabled():
    adapter = MicrophoneInputAdapter()
    adapter.grant_permission()

    status = adapter.revoke_permission()

    assert status["state"] == "disabled"
    assert status["permission_granted"] is False


def run_tests():
    test_initial_state_is_disabled()
    test_status_contains_safe_backend_metadata()
    test_request_permission_does_not_enable_microphone()
    test_grant_permission_is_logical_only()
    test_enable_requires_permission_first()
    test_start_listening_requires_permission()
    test_start_listening_without_backend_does_not_enable_microphone()
    test_read_text_reports_missing_backend_without_recognition()
    test_disable_keeps_logical_permission_but_stops_adapter_state()
    test_revoke_permission_returns_to_disabled()


if __name__ == "__main__":
    run_tests()
