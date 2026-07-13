from voice import VoiceOutputSafetyController, VoiceOutputSafetyStatus


def test_default_state_allows_speaking():
    controller = VoiceOutputSafetyController()

    decision = controller.can_speak(source="test")

    assert decision.allowed is True
    assert decision.reason is None
    assert decision.muted is False
    assert decision.skip_next is False
    assert "Облачный TTS не используется." in decision.safety_notes


def test_mute_blocks_speaking():
    controller = VoiceOutputSafetyController()

    controller.mute(reason="user_request")
    decision = controller.can_speak()

    assert decision.allowed is False
    assert decision.reason == "muted"
    assert decision.muted is True
    assert "Тихий режим блокирует голосовую озвучку." in decision.safety_notes


def test_unmute_allows_speaking_again():
    controller = VoiceOutputSafetyController()
    controller.mute()

    controller.unmute()

    assert controller.can_speak().allowed is True
    assert controller.status().muted is False


def test_skip_next_blocks_once_and_then_clears():
    controller = VoiceOutputSafetyController()
    controller.skip_next_speech()

    first = controller.can_speak()
    consumed = controller.consume_skip_if_needed()
    second = controller.can_speak()

    assert first.allowed is False
    assert first.reason == "skip_next"
    assert consumed is True
    assert second.allowed is True
    assert controller.status().skip_next is False


def test_request_stop_mutes_and_records_stop_requested():
    controller = VoiceOutputSafetyController()

    status = controller.request_stop()

    assert status.muted is True
    assert status.last_stop_requested is True
    assert controller.can_speak().reason == "muted"


def test_status_reports_muted_and_skip_state():
    controller = VoiceOutputSafetyController()
    controller.mute()
    controller.skip_next_speech()

    status = controller.status()

    assert isinstance(status, VoiceOutputSafetyStatus)
    assert status.muted is True
    assert status.skip_next is True
    assert "Аудиофайлы не сохраняются." in status.safety_notes


def test_state_is_in_memory_only():
    controller = VoiceOutputSafetyController()
    controller.request_stop()
    controller.skip_next_speech()

    assert not hasattr(controller, "storage_path")
    assert not hasattr(controller, "file_path")
    assert not hasattr(controller, "settings_path")
