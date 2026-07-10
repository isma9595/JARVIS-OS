from dataclasses import dataclass
from importlib.util import find_spec

from voice.microphone_listening_modes import MicrophoneListeningModeManager


DEFAULT_CAPTURE_DURATION_SECONDS = 5
HARD_MAX_CAPTURE_DURATION_SECONDS = 15


@dataclass(frozen=True)
class OneShotCaptureResult:
    success: bool
    available: bool
    duration_seconds: float
    audio_captured: bool
    message: str
    error: str | None = None

    def to_dict(self):
        return {
            "success": self.success,
            "available": self.available,
            "duration_seconds": self.duration_seconds,
            "audio_captured": self.audio_captured,
            "message": self.message,
            "error": self.error,
        }


class SoundDeviceOneShotCaptureAdapter:
    def __init__(self, sample_rate=16000, channels=1):
        self.sample_rate = sample_rate
        self.channels = channels

    def is_available(self):
        return find_spec("sounddevice") is not None

    def capture_once(self, duration_seconds):
        if not self.is_available():
            return {"audio_captured": False, "audio": None}

        import sounddevice

        frame_count = int(self.sample_rate * duration_seconds)
        audio = sounddevice.rec(
            frame_count,
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="int16",
        )
        sounddevice.wait()
        return {"audio_captured": True, "audio": audio}


class OneShotMicrophoneCapture:
    def __init__(
        self,
        adapter=None,
        mode_manager=None,
        default_duration_seconds=DEFAULT_CAPTURE_DURATION_SECONDS,
        hard_max_duration_seconds=HARD_MAX_CAPTURE_DURATION_SECONDS,
    ):
        self.adapter = adapter or SoundDeviceOneShotCaptureAdapter()
        self.mode_manager = mode_manager or MicrophoneListeningModeManager()
        self.default_duration_seconds = default_duration_seconds
        self.hard_max_duration_seconds = hard_max_duration_seconds
        self._validate_configuration()

    def _validate_configuration(self):
        self._validate_duration(self.default_duration_seconds)
        self._validate_duration(self.hard_max_duration_seconds)
        if self.default_duration_seconds > self.hard_max_duration_seconds:
            raise ValueError("Default capture duration cannot exceed hard maximum.")

    def _validate_duration(self, duration_seconds):
        if isinstance(duration_seconds, bool):
            raise ValueError("Capture duration must be a positive number.")

        try:
            normalized_duration = float(duration_seconds)
        except (TypeError, ValueError) as exc:
            raise ValueError("Capture duration must be a positive number.") from exc

        if normalized_duration <= 0:
            raise ValueError("Capture duration must be a positive number.")

        if normalized_duration > self.hard_max_duration_seconds:
            raise ValueError(
                "Capture duration exceeds the hard safety maximum of "
                f"{self.hard_max_duration_seconds} seconds."
            )

        return normalized_duration

    def get_status(self):
        return {
            "available": self.is_available(),
            "default_duration_seconds": self.default_duration_seconds,
            "hard_max_duration_seconds": self.hard_max_duration_seconds,
            "mode": self.mode_manager.get_mode(),
            "message": "Микрофон не был запущен автоматически.",
            "recognition_active": False,
            "recognition_message": "Реальное распознавание речи пока не активировано.",
        }

    def is_available(self):
        try:
            return bool(self.adapter.is_available())
        except Exception:
            return False

    def capture_once(self, duration_seconds=None):
        requested_duration = (
            self.default_duration_seconds
            if duration_seconds is None
            else duration_seconds
        )

        try:
            safe_duration = self._validate_duration(requested_duration)
        except ValueError as exc:
            return OneShotCaptureResult(
                success=False,
                available=self.is_available(),
                duration_seconds=0,
                audio_captured=False,
                message="Одноразовый захват микрофона отклонен: небезопасная длительность.",
                error=str(exc),
            ).to_dict()

        if not self.mode_manager.allows_limited_listening():
            return OneShotCaptureResult(
                success=False,
                available=self.is_available(),
                duration_seconds=safe_duration,
                audio_captured=False,
                message=(
                    "Одноразовый захват микрофона не запущен: нужен режим PARTIAL "
                    "и явный запрос пользователя."
                ),
                error="microphone listening mode must be PARTIAL",
            ).to_dict()

        if not self.is_available():
            return OneShotCaptureResult(
                success=False,
                available=False,
                duration_seconds=safe_duration,
                audio_captured=False,
                message="Одноразовый захват микрофона недоступен: не найден аудиоадаптер.",
                error="audio adapter is unavailable",
            ).to_dict()

        try:
            capture_result = self.adapter.capture_once(safe_duration)
        except Exception as exc:
            return OneShotCaptureResult(
                success=False,
                available=False,
                duration_seconds=safe_duration,
                audio_captured=False,
                message="Одноразовый захват микрофона недоступен: аудиоадаптер вернул ошибку.",
                error=str(exc),
            ).to_dict()

        audio_captured = bool(capture_result.get("audio_captured"))
        return OneShotCaptureResult(
            success=audio_captured,
            available=True,
            duration_seconds=safe_duration,
            audio_captured=audio_captured,
            message="Одноразовый захват микрофона завершен.",
            error=None if audio_captured else "audio was not captured",
        ).to_dict()
