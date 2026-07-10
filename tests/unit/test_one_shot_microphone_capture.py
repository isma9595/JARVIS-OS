from unittest.mock import Mock, patch

from voice import (
    DEFAULT_CAPTURE_DURATION_SECONDS,
    HARD_MAX_CAPTURE_DURATION_SECONDS,
    MicrophoneListeningModeManager,
    OneShotMicrophoneCapture,
)


class FakeCaptureAdapter:
    def __init__(self, available=True, audio_captured=True):
        self.available = available
        self.audio_captured = audio_captured
        self.availability_checks = 0
        self.capture_calls = []

    def is_available(self):
        self.availability_checks += 1
        return self.available

    def capture_once(self, duration_seconds):
        self.capture_calls.append(duration_seconds)
        return {"audio_captured": self.audio_captured, "audio": b"fake-audio"}


def partial_mode_manager():
    manager = MicrophoneListeningModeManager()
    manager.switch_to_partial()
    return manager


def test_constructing_service_does_not_open_microphone():
    adapter = FakeCaptureAdapter()

    OneShotMicrophoneCapture(adapter=adapter)

    assert adapter.availability_checks == 0
    assert adapter.capture_calls == []


def test_checking_availability_does_not_capture_audio():
    adapter = FakeCaptureAdapter()
    service = OneShotMicrophoneCapture(adapter=adapter)

    assert service.is_available() is True
    assert adapter.availability_checks == 1
    assert adapter.capture_calls == []


def test_status_does_not_capture_audio_and_is_russian_first():
    adapter = FakeCaptureAdapter()
    service = OneShotMicrophoneCapture(adapter=adapter)

    status = service.get_status()

    assert status["available"] is True
    assert status["message"] == "Микрофон не был запущен автоматически."
    assert status["recognition_message"] == "Реальное распознавание речи пока не активировано."
    assert adapter.capture_calls == []


def test_default_duration_is_safe():
    service = OneShotMicrophoneCapture(adapter=FakeCaptureAdapter())

    assert service.default_duration_seconds == DEFAULT_CAPTURE_DURATION_SECONDS
    assert service.default_duration_seconds == 5
    assert service.hard_max_duration_seconds == HARD_MAX_CAPTURE_DURATION_SECONDS
    assert service.hard_max_duration_seconds == 15


def test_duration_over_hard_maximum_is_rejected():
    adapter = FakeCaptureAdapter()
    service = OneShotMicrophoneCapture(
        adapter=adapter,
        mode_manager=partial_mode_manager(),
    )

    result = service.capture_once(HARD_MAX_CAPTURE_DURATION_SECONDS + 1)

    assert result["success"] is False
    assert result["audio_captured"] is False
    assert "небезопасная длительность" in result["message"]
    assert adapter.capture_calls == []


def test_invalid_duration_is_rejected():
    adapter = FakeCaptureAdapter()
    service = OneShotMicrophoneCapture(
        adapter=adapter,
        mode_manager=partial_mode_manager(),
    )

    result = service.capture_once(0)

    assert result["success"] is False
    assert result["duration_seconds"] == 0
    assert result["audio_captured"] is False
    assert adapter.capture_calls == []


def test_successful_fake_one_shot_capture_returns_success():
    adapter = FakeCaptureAdapter()
    service = OneShotMicrophoneCapture(
        adapter=adapter,
        mode_manager=partial_mode_manager(),
    )

    result = service.capture_once()

    assert result == {
        "success": True,
        "available": True,
        "duration_seconds": 5.0,
        "audio_captured": True,
        "message": "Одноразовый захват микрофона завершен.",
        "error": None,
    }


def test_unavailable_adapter_returns_safe_russian_message():
    adapter = FakeCaptureAdapter(available=False)
    service = OneShotMicrophoneCapture(
        adapter=adapter,
        mode_manager=partial_mode_manager(),
    )

    result = service.capture_once()

    assert result["success"] is False
    assert result["available"] is False
    assert result["audio_captured"] is False
    assert result["message"] == "Одноразовый захват микрофона недоступен: не найден аудиоадаптер."
    assert adapter.capture_calls == []


def test_capture_stops_after_one_fake_capture_call():
    adapter = FakeCaptureAdapter()
    service = OneShotMicrophoneCapture(
        adapter=adapter,
        mode_manager=partial_mode_manager(),
    )

    service.capture_once(3)

    assert adapter.capture_calls == [3.0]


def test_no_background_thread_is_started():
    service = OneShotMicrophoneCapture(
        adapter=FakeCaptureAdapter(),
        mode_manager=partial_mode_manager(),
    )

    with patch("threading.Thread.start") as thread_start:
        service.capture_once()

    thread_start.assert_not_called()


def test_vosk_recognition_is_not_called():
    adapter = FakeCaptureAdapter()
    speech_backend = Mock()
    service = OneShotMicrophoneCapture(
        adapter=adapter,
        mode_manager=partial_mode_manager(),
    )

    service.capture_once()

    speech_backend.recognize_once.assert_not_called()


def test_off_mode_rejects_capture_without_opening_microphone():
    adapter = FakeCaptureAdapter()
    service = OneShotMicrophoneCapture(adapter=adapter)

    result = service.capture_once()

    assert result["success"] is False
    assert result["audio_captured"] is False
    assert "нужен режим PARTIAL" in result["message"]
    assert adapter.capture_calls == []


def test_partial_mode_allows_bounded_one_shot_capture():
    adapter = FakeCaptureAdapter()
    service = OneShotMicrophoneCapture(
        adapter=adapter,
        mode_manager=partial_mode_manager(),
    )

    result = service.capture_once(2)

    assert result["success"] is True
    assert adapter.capture_calls == [2.0]


def test_continuous_mode_does_not_start_real_continuous_capture():
    adapter = FakeCaptureAdapter()
    manager = MicrophoneListeningModeManager()
    manager.switch_to_continuous()
    service = OneShotMicrophoneCapture(adapter=adapter, mode_manager=manager)

    result = service.capture_once()

    assert result["success"] is False
    assert "нужен режим PARTIAL" in result["message"]
    assert adapter.capture_calls == []
