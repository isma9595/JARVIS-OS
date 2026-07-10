import pytest

from voice import MicrophoneListeningMode, MicrophoneListeningModeManager


def test_default_mode_is_off():
    manager = MicrophoneListeningModeManager()

    assert manager.get_mode() == "off"
    assert manager.get_status()["mode"] == "off"


def test_off_mode_does_not_allow_listening():
    manager = MicrophoneListeningModeManager()

    assert manager.allows_listening() is False
    assert manager.allows_limited_listening() is False
    assert manager.is_continuous() is False
    assert manager.requires_explicit_user_activation() is False


def test_partial_mode_allows_limited_listening_state_only():
    manager = MicrophoneListeningModeManager()

    status = manager.switch_to_partial()

    assert status["mode"] == "partial"
    assert status["allows_listening"] is True
    assert status["limited_listening"] is True
    assert status["continuous"] is False
    assert status["requires_explicit_user_activation"] is True


def test_continuous_mode_is_marked_as_continuous_and_explicit():
    manager = MicrophoneListeningModeManager()

    status = manager.switch_to_continuous()

    assert status["mode"] == "continuous"
    assert status["allows_listening"] is True
    assert status["limited_listening"] is False
    assert status["continuous"] is True
    assert status["requires_explicit_user_activation"] is True


def test_switching_between_modes_works():
    manager = MicrophoneListeningModeManager()

    manager.switch_to_partial()
    manager.switch_to_continuous()
    status = manager.switch_to_off()

    assert status["mode"] == "off"
    assert manager.allows_listening() is False


def test_mode_names_are_validated():
    assert MicrophoneListeningModeManager.is_valid_mode("off") is True
    assert MicrophoneListeningModeManager.is_valid_mode("partial") is True
    assert MicrophoneListeningModeManager.is_valid_mode("continuous") is True
    assert MicrophoneListeningModeManager.is_valid_mode("always_on") is False
    assert MicrophoneListeningModeManager.validate_mode(
        MicrophoneListeningMode.PARTIAL
    ) == MicrophoneListeningMode.PARTIAL


def test_invalid_mode_names_are_rejected_without_state_change():
    manager = MicrophoneListeningModeManager()
    manager.switch_to_partial()

    with pytest.raises(ValueError, match="Unknown microphone listening mode"):
        manager.set_mode("always_on")

    assert manager.get_mode() == "partial"


def test_mode_switching_never_starts_microphone_capture():
    manager = MicrophoneListeningModeManager()

    off_status = manager.switch_to_off()
    partial_status = manager.switch_to_partial()
    continuous_status = manager.switch_to_continuous()

    assert off_status["starts_microphone_capture"] is False
    assert partial_status["starts_microphone_capture"] is False
    assert continuous_status["starts_microphone_capture"] is False
    assert manager.starts_microphone_capture() is False
