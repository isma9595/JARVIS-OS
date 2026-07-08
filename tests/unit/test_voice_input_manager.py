from voice import VoiceInputManager


def sample_profile():
    return {
        "user_name": "Исмаил",
        "preferred_name": "Исмаил",
        "assistant_name": "JARVIS",
        "language": "ru",
        "communication_style": "естественный, понятный, не робот",
    }


def test_creation_without_parameters():
    manager = VoiceInputManager()

    assert manager.command_processor is not None
    assert manager.dialogue_manager is not None
    assert manager.user_profile == {}


def test_initial_state_is_disabled():
    manager = VoiceInputManager()

    assert manager.get_state() == "disabled"
    assert manager.is_enabled() is False
    assert manager.has_pending_confirmation() is False


def test_enable():
    manager = VoiceInputManager(user_profile=sample_profile())

    result = manager.enable()

    assert result["state"] == "ready"
    assert manager.get_state() == "ready"
    assert manager.is_enabled() is True
    assert "голосовой ввод подготовлен" in result["message"]
    assert "микрофон пока не включается" in result["message"]


def test_disable():
    manager = VoiceInputManager(user_profile=sample_profile())
    manager.enable()

    result = manager.disable()

    assert result["state"] == "disabled"
    assert manager.get_state() == "disabled"
    assert manager.is_enabled() is False
    assert "голосовой ввод отключён" in result["message"]


def test_start_listening_when_disabled():
    manager = VoiceInputManager(user_profile=sample_profile())

    result = manager.start_listening()

    assert result["state"] == "disabled"
    assert manager.get_state() == "disabled"
    assert "не слушаю микрофон" in result["message"]


def test_start_listening_when_ready():
    manager = VoiceInputManager(user_profile=sample_profile())
    manager.enable()

    result = manager.start_listening()

    assert result["state"] == "listening"
    assert manager.get_state() == "listening"
    assert "Микрофон в этой версии не включается" in result["message"]


def test_stop_listening():
    manager = VoiceInputManager(user_profile=sample_profile())
    manager.enable()
    manager.start_listening()

    result = manager.stop_listening()

    assert result["state"] == "ready"
    assert manager.get_state() == "ready"
    assert "остановлен" in result["message"]


def test_process_recognized_text():
    manager = VoiceInputManager(user_profile=sample_profile())

    result = manager.process_recognized_text("кто я")

    assert result["intent"] == "user.identity"
    assert result["should_exit"] is False
    assert result["channel"] == "voice"
    assert result["source"] == "recognized_text"
    assert "Исмаил" in result["response"]
    assert "принял голосовую команду" in result["response"]


def test_process_empty_recognized_text():
    manager = VoiceInputManager(user_profile=sample_profile())

    result = manager.process_recognized_text("")

    assert result["intent"] == "voice.empty"
    assert result["should_exit"] is False
    assert "не получил распознанный текст" in result["response"]


def test_recognized_text_requires_pending_confirmation():
    manager = VoiceInputManager(user_profile=sample_profile())

    result = manager.process_recognized_text("отправь письмо")

    assert result["intent"] == "voice.confirmation_required"
    assert result["should_exit"] is False
    assert result["channel"] == "voice"
    assert result["source"] == "recognized_text"
    assert manager.has_pending_confirmation() is True
    assert manager.get_pending_confirmation() == {
        "text": "отправь письмо",
        "channel": "voice",
        "risk": "confirmation_required",
    }
    assert "требует подтверждения" in result["response"]


def test_clear_pending_confirmation():
    manager = VoiceInputManager(user_profile=sample_profile())
    manager.process_recognized_text("отправь письмо")

    manager.clear_pending_confirmation()

    assert manager.has_pending_confirmation() is False
    assert manager.get_pending_confirmation() is None


def test_confirm_pending_action_is_safe_simulation():
    manager = VoiceInputManager(user_profile=sample_profile())
    manager.process_recognized_text("отправь письмо")

    result = manager.confirm_pending_action()

    assert result["intent"] == "voice.confirmation.confirmed"
    assert result["should_exit"] is False
    assert result["channel"] == "voice"
    assert result["source"] == "confirmation_simulation"
    assert manager.has_pending_confirmation() is False
    assert "Реальное выполнение действий" in result["response"]


def test_confirm_pending_action_without_pending():
    manager = VoiceInputManager(user_profile=sample_profile())

    result = manager.confirm_pending_action()

    assert result["intent"] == "voice.confirmation.none"
    assert result["should_exit"] is False
    assert "нет голосового действия" in result["response"]
    assert "для подтверждения" in result["response"]


def test_cancel_pending_action():
    manager = VoiceInputManager(user_profile=sample_profile())
    manager.process_recognized_text("отправь письмо")

    result = manager.cancel_pending_action()

    assert result["intent"] == "voice.confirmation.cancelled"
    assert result["should_exit"] is False
    assert result["channel"] == "voice"
    assert result["source"] == "confirmation_simulation"
    assert manager.has_pending_confirmation() is False
    assert "отменено" in result["response"]


def test_cancel_pending_action_without_pending():
    manager = VoiceInputManager(user_profile=sample_profile())

    result = manager.cancel_pending_action()

    assert result["intent"] == "voice.confirmation.none"
    assert result["should_exit"] is False
    assert "для отмены" in result["response"]


def test_forbidden_voice_command_does_not_create_pending_confirmation():
    manager = VoiceInputManager(user_profile=sample_profile())

    result = manager.process_recognized_text("удали system32")

    assert result["intent"] == "voice.forbidden"
    assert result["should_exit"] is False
    assert manager.has_pending_confirmation() is False
    assert "опасной" in result["response"]


def run_tests():
    test_creation_without_parameters()
    test_initial_state_is_disabled()
    test_enable()
    test_disable()
    test_start_listening_when_disabled()
    test_start_listening_when_ready()
    test_stop_listening()
    test_process_recognized_text()
    test_process_empty_recognized_text()
    test_recognized_text_requires_pending_confirmation()
    test_clear_pending_confirmation()
    test_confirm_pending_action_is_safe_simulation()
    test_confirm_pending_action_without_pending()
    test_cancel_pending_action()
    test_cancel_pending_action_without_pending()
    test_forbidden_voice_command_does_not_create_pending_confirmation()


if __name__ == "__main__":
    run_tests()
