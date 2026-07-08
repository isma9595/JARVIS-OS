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


def test_normalize_voice_text_handles_none():
    manager = VoiceInputManager(user_profile=sample_profile())

    assert manager.normalize_voice_text(None) == ""


def test_normalize_voice_text_trims_spaces_and_lowercases():
    manager = VoiceInputManager(user_profile=sample_profile())

    assert manager.normalize_voice_text("  Джарвис   кто Я  ") == "джарвис кто я"


def test_extract_voice_command_jarvis_alias():
    manager = VoiceInputManager(user_profile=sample_profile())

    assert manager.extract_voice_command("джарвис кто я") == "кто я"


def test_extract_voice_command_say_alias():
    manager = VoiceInputManager(user_profile=sample_profile())

    assert manager.extract_voice_command("скажи кто я") == "кто я"


def test_extract_voice_command_ask_alias():
    manager = VoiceInputManager(user_profile=sample_profile())

    assert (
        manager.extract_voice_command("спроси статус системы")
        == "статус системы"
    )


def test_extract_voice_command_voice_ask_alias():
    manager = VoiceInputManager(user_profile=sample_profile())

    assert (
        manager.extract_voice_command("голосом спроси статус системы")
        == "статус системы"
    )


def test_extract_voice_command_nested_jarvis_say_alias():
    manager = VoiceInputManager(user_profile=sample_profile())

    assert (
        manager.extract_voice_command("джарвис скажи покажи память")
        == "покажи память"
    )


def test_is_voice_alias():
    manager = VoiceInputManager(user_profile=sample_profile())

    assert manager.is_voice_alias("джарвис кто я") is True
    assert manager.is_voice_alias("спроси статус системы") is True
    assert manager.is_voice_alias("кто я") is False


def test_is_voice_confirmation():
    manager = VoiceInputManager(user_profile=sample_profile())

    assert manager.is_voice_confirmation("подтверждаю") is True
    assert manager.is_voice_confirmation("можно") is True
    assert manager.is_voice_confirmation("кто я") is False


def test_is_voice_cancel():
    manager = VoiceInputManager(user_profile=sample_profile())

    assert manager.is_voice_cancel("отмена") is True
    assert manager.is_voice_cancel("стоп") is True
    assert manager.is_voice_cancel("кто я") is False


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


def test_process_recognized_text_jarvis_alias():
    manager = VoiceInputManager(user_profile=sample_profile())

    result = manager.process_recognized_text("джарвис кто я")

    assert result["intent"] == "user.identity"
    assert "принял голосовую команду: кто я" in result["response"]


def test_process_recognized_text_say_status_alias():
    manager = VoiceInputManager(user_profile=sample_profile())

    result = manager.process_recognized_text("скажи статус системы")

    assert result["intent"] == "system.status"
    assert "принял голосовую команду: статус системы" in result["response"]


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


def test_voice_alias_requires_pending_confirmation():
    manager = VoiceInputManager(user_profile=sample_profile())

    result = manager.process_recognized_text("джарвис отправь письмо")

    assert result["intent"] == "voice.confirmation_required"
    assert manager.has_pending_confirmation() is True
    assert manager.get_pending_confirmation()["text"] == "отправь письмо"


def test_short_confirmation_works_only_with_pending_voice_action():
    manager = VoiceInputManager(user_profile=sample_profile())

    none_result = manager.process_recognized_text("подтверждаю")
    assert none_result["intent"] == "voice.confirmation.none"

    manager.process_recognized_text("джарвис отправь письмо")
    confirmed_result = manager.process_recognized_text("подтверждаю")

    assert confirmed_result["intent"] == "voice.confirmation.confirmed"
    assert manager.has_pending_confirmation() is False


def test_short_cancel_works_only_with_pending_voice_action():
    manager = VoiceInputManager(user_profile=sample_profile())

    none_result = manager.process_recognized_text("стоп")
    assert none_result["intent"] == "voice.confirmation.none"

    manager.process_recognized_text("джарвис отправь письмо")
    cancelled_result = manager.process_recognized_text("отмена")

    assert cancelled_result["intent"] == "voice.confirmation.cancelled"
    assert manager.has_pending_confirmation() is False


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
    test_normalize_voice_text_handles_none()
    test_normalize_voice_text_trims_spaces_and_lowercases()
    test_extract_voice_command_jarvis_alias()
    test_extract_voice_command_say_alias()
    test_extract_voice_command_ask_alias()
    test_extract_voice_command_voice_ask_alias()
    test_extract_voice_command_nested_jarvis_say_alias()
    test_is_voice_alias()
    test_is_voice_confirmation()
    test_is_voice_cancel()
    test_process_recognized_text()
    test_process_empty_recognized_text()
    test_process_recognized_text_jarvis_alias()
    test_process_recognized_text_say_status_alias()
    test_recognized_text_requires_pending_confirmation()
    test_voice_alias_requires_pending_confirmation()
    test_short_confirmation_works_only_with_pending_voice_action()
    test_short_cancel_works_only_with_pending_voice_action()
    test_clear_pending_confirmation()
    test_confirm_pending_action_is_safe_simulation()
    test_confirm_pending_action_without_pending()
    test_cancel_pending_action()
    test_cancel_pending_action_without_pending()
    test_forbidden_voice_command_does_not_create_pending_confirmation()


if __name__ == "__main__":
    run_tests()
