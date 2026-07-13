from dialogue import VoiceDialogueModeManager


def test_default_mode_off():
    manager = VoiceDialogueModeManager()

    assert manager.mode == "OFF"
    assert manager.is_manual_enabled() is False


def test_enable_manual_mode():
    manager = VoiceDialogueModeManager()

    status = manager.enable_manual()

    assert status.enabled is True
    assert status.mode == "MANUAL"
    assert manager.is_manual_enabled() is True


def test_disable_manual_mode():
    manager = VoiceDialogueModeManager()
    manager.enable_manual()

    status = manager.disable()

    assert status.enabled is False
    assert status.mode == "OFF"


def test_status_off():
    status = VoiceDialogueModeManager().status()

    assert status.enabled is False
    assert status.mode == "OFF"
    assert "Постоянное прослушивание не включается." in status.safety_notes


def test_status_manual():
    manager = VoiceDialogueModeManager()
    manager.enable_manual()

    status = manager.status()

    assert status.enabled is True
    assert status.mode == "MANUAL"


def test_should_speak_response_returns_false_for_empty_text():
    manager = VoiceDialogueModeManager()
    manager.enable_manual()

    assert manager.should_speak_response("   ", source_command="статус системы") is False


def test_should_speak_response_returns_false_for_non_speakable_response():
    manager = VoiceDialogueModeManager()
    manager.enable_manual()

    assert (
        manager.should_speak_response(
            "служебный ответ",
            source_command="статус голосового диалога",
            speakable=False,
        )
        is False
    )


def test_should_speak_response_returns_false_for_control_commands():
    manager = VoiceDialogueModeManager()
    manager.enable_manual()

    for command in (
        "включить голосовой диалог",
        "статус голосового диалога",
        "озвучь последний ответ",
        "история ответов",
        "скажи: тест",
    ):
        assert manager.should_speak_response("ответ", source_command=command) is False


def test_should_speak_response_returns_true_for_normal_meaningful_response():
    manager = VoiceDialogueModeManager()
    manager.enable_manual()

    assert manager.should_speak_response("система работает", source_command="статус системы") is True


def test_history_is_in_memory_only():
    manager = VoiceDialogueModeManager()
    manager.enable_manual()
    manager.disable()

    assert not hasattr(manager, "storage_path")
    assert not hasattr(manager, "file_path")
    assert not hasattr(manager, "settings_path")
