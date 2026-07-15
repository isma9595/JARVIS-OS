from voice.audio_lifecycle import AudioLifecycleController


class FailingMicrophoneAdapter:
    def __init__(self):
        self.calls = []

    def get_status(self):
        self.calls.append("get_status")
        return {
            "state": "disabled",
            "permission_granted": False,
            "backend_name": "none",
            "last_error": None,
            "backend_available": False,
        }

    def start_listening(self):
        raise AssertionError("audio lifecycle must not start microphone")

    def stop_listening(self):
        raise AssertionError("audio lifecycle must not stop microphone")

    def read_text(self):
        raise AssertionError("audio lifecycle must not record audio")


class FakeVoiceInputManager:
    def __init__(self):
        self.microphone_adapter = FailingMicrophoneAdapter()

    def get_microphone_status(self):
        return self.microphone_adapter.get_status()


class FailingVoiceOutputManager:
    mode = "OFF"

    def __init__(self):
        self.calls = []

    def is_enabled(self):
        self.calls.append("is_enabled")
        return False

    def speak(self, text, source="test"):
        raise AssertionError("audio lifecycle must not call TTS")

    def test_voice(self):
        raise AssertionError("audio lifecycle must not play audio")


class FakeListeningModeManager:
    def get_mode(self):
        return "off"


class FakeDialogueModeManager:
    def is_manual_enabled(self):
        return False


def _controller():
    return AudioLifecycleController(
        voice_input_manager=FakeVoiceInputManager(),
        voice_output_manager=FailingVoiceOutputManager(),
        microphone_listening_mode_manager=FakeListeningModeManager(),
        voice_dialogue_mode_manager=FakeDialogueModeManager(),
        pending_voice_command_checker=lambda: False,
    )


def test_default_status_safe():
    status = _controller().status()

    assert status.lifecycle_enabled is True
    assert status.state == "idle"
    assert status.capture_mode == "off"
    assert status.output_mode == "off"
    assert status.microphone_available is False
    assert status.microphone_active is False
    assert status.one_shot_active is False
    assert status.tts_enabled is False
    assert status.speaking_active is False
    assert status.voice_dialogue_active is False
    assert status.pending_voice_command is False
    assert status.safe_to_start_capture is True


def test_safe_defaults_do_not_allow_automatic_or_continuous_audio():
    status = _controller().status()

    assert status.auto_listening_on_startup is False
    assert status.continuous_listening_enabled is False
    assert status.continuous_listening_allowed is False
    assert status.network_used is False
    assert status.audio_saved is False


def test_status_text_mentions_safe_boundaries():
    text = _controller().status_text_ru()

    assert "network used: no" in text
    assert "audio saved: no" in text
    assert "auto listening on startup: no" in text
    assert "no command executed" in text


def test_metadata_stop_reset_does_not_call_microphone_or_tts():
    controller = _controller()

    stop = controller.stop_audio_metadata_only()
    reset = controller.reset_to_idle()

    assert stop.safe is True
    assert reset.safe is True
    assert stop.network_used is False
    assert reset.audio_saved is False
    assert controller.status().state == "idle"


def test_lifecycle_events_are_safe_and_metadata_only():
    controller = _controller()

    start = controller.start_one_shot_metadata_only()
    pause = controller.pause_output_metadata_only()
    resume = controller.resume_output_metadata_only()

    assert start.safe is True
    assert pause.safe is True
    assert resume.safe is True
    assert start.audio_saved is False
    assert pause.network_used is False
    assert "Microphone was not opened" in start.message_ru
    assert "TTS was not called" in pause.message_ru


def test_capabilities_have_no_command_execution_or_secret_like_strings():
    text = _controller().capabilities_text_ru()

    assert "does not start microphone" in text
    assert "does not play audio" in text
    assert "does not enable continuous listening" in text
    assert "sk-" not in text.lower()
    assert "api key" not in text.lower()
    assert "token" not in text.lower()
