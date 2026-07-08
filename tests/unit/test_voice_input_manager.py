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
    assert "Исмаил" in result["response"]


def test_process_empty_recognized_text():
    manager = VoiceInputManager(user_profile=sample_profile())

    result = manager.process_recognized_text("")

    assert result["intent"] == "voice.empty"
    assert result["should_exit"] is False
    assert "не получил распознанный текст" in result["response"]


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


if __name__ == "__main__":
    run_tests()
