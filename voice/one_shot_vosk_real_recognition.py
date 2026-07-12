"""Explicit one-shot local Vosk recognition path.

This module is intentionally narrow: it may capture audio only for an
explicit one-shot request, recognizes locally, and never executes the text.
"""

from dataclasses import dataclass, field
import json

from voice.microphone_listening_modes import MicrophoneListeningModeManager
from voice.one_shot_microphone_capture import (
    DEFAULT_CAPTURE_DURATION_SECONDS,
    HARD_MAX_CAPTURE_DURATION_SECONDS,
    SoundDeviceOneShotCaptureAdapter,
)
from voice.vosk_local_recognition_gate import evaluate_vosk_local_recognition_gate
from voice.vosk_model_readiness_verifier import VoskModelReadinessVerifier
from voice.vosk_settings_manager import VoskSettingsManager


DEFAULT_REAL_RECOGNITION_SAFETY_NOTES = [
    "Микрофон был включён только для одного короткого захвата.",
    "Постоянное прослушивание не использовалось.",
    "Фоновый слушатель не запускался.",
    "Аудио не отправлялось в облако.",
    "Аудиофайлы не сохранялись.",
    "Распознанный текст не выполнялся как команда.",
]

DEFAULT_BLOCKED_SAFETY_NOTES = [
    "Микрофон не запускался.",
    "Постоянное прослушивание не использовалось.",
    "Фоновый слушатель не запускался.",
    "Аудио не отправлялось в облако.",
    "Аудиофайлы не сохранялись.",
    "Распознавание не выполнялось.",
    "Распознанный текст не выполнялся как команда.",
]


@dataclass(frozen=True)
class OneShotVoskRealRecognitionResult:
    allowed: bool
    completed: bool
    blocked: bool
    recognized_text: str | None
    capture_seconds: float | int
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    safety_notes: list[str] = field(
        default_factory=lambda: list(DEFAULT_REAL_RECOGNITION_SAFETY_NOTES)
    )
    next_steps: list[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "allowed": self.allowed,
            "completed": self.completed,
            "blocked": self.blocked,
            "recognized_text": self.recognized_text,
            "capture_seconds": self.capture_seconds,
            "reasons": list(self.reasons),
            "warnings": list(self.warnings),
            "safety_notes": list(self.safety_notes),
            "next_steps": list(self.next_steps),
        }


class OneShotVoskRealRecognition:
    """Run one explicit local Vosk recognition attempt and stop."""

    def __init__(
        self,
        settings_manager=None,
        gate_checker=None,
        readiness_verifier=None,
        capture_provider=None,
        vosk_runtime_factory=None,
        dependency_checker=None,
        capture_seconds=DEFAULT_CAPTURE_DURATION_SECONDS,
    ):
        self.settings_manager = settings_manager or VoskSettingsManager()
        self.gate_checker = gate_checker
        self.readiness_verifier = readiness_verifier or VoskModelReadinessVerifier()
        self.capture_provider = capture_provider
        self.vosk_runtime_factory = vosk_runtime_factory or self._load_vosk_runtime
        self.dependency_checker = dependency_checker
        if (
            self.dependency_checker is None
            and capture_provider is None
            and vosk_runtime_factory is None
        ):
            from voice.audio_dependency_readiness import (
                AudioDependencyReadinessChecker,
            )

            self.dependency_checker = AudioDependencyReadinessChecker()
        self.capture_seconds = capture_seconds

    def run_once(self, explicit_one_shot_requested=False):
        blocked_safety_notes = list(DEFAULT_BLOCKED_SAFETY_NOTES)
        recognition_safety_notes = list(DEFAULT_REAL_RECOGNITION_SAFETY_NOTES)

        if not explicit_one_shot_requested:
            return self._blocked_result(
                ["Нужна явная команда одноразового распознавания."],
                safety_notes=blocked_safety_notes,
            )

        dependency_block = self._dependency_blocked_result(blocked_safety_notes)
        if dependency_block is not None:
            return dependency_block

        model_path = self._get_model_path()
        if not model_path:
            return self._blocked_result(
                ["Путь к модели Vosk не указан."],
                safety_notes=blocked_safety_notes,
                next_steps=["Укажите путь к модели Vosk."],
            )

        gate_result = self._check_gate(model_path)
        gate_allowed = bool(self._get_value(gate_result, "allowed", False))
        gate_warnings = list(self._get_value(gate_result, "warnings", []))
        gate_next_steps = list(self._get_value(gate_result, "next_steps", []))
        if not gate_allowed:
            reasons = list(self._get_value(gate_result, "blockers", [])) or [
                "Локальное распознавание Vosk не разрешено gate."
            ]
            return self._blocked_result(
                reasons,
                warnings=gate_warnings,
                safety_notes=blocked_safety_notes,
                next_steps=gate_next_steps,
            )

        readiness = self.readiness_verifier.verify(model_path)
        if not bool(self._get_value(readiness, "ready_for_future_recognition", False)):
            return self._blocked_result(
                list(self._get_value(readiness, "reasons", []))
                or ["Папка модели Vosk не готова."],
                warnings=gate_warnings
                + list(self._get_value(readiness, "warnings", [])),
                safety_notes=blocked_safety_notes,
                next_steps=list(self._get_value(readiness, "next_steps", [])),
            )

        try:
            runtime = self.vosk_runtime_factory()
        except ImportError:
            return self._blocked_result(
                ["Пакет vosk не установлен или недоступен для текущего Python."],
                warnings=gate_warnings,
                safety_notes=blocked_safety_notes,
                next_steps=[
                    "python -m pip install vosk",
                ],
            )
        except Exception as exc:
            return self._blocked_result(
                [f"Vosk runtime недоступен: {exc}"],
                warnings=gate_warnings,
                safety_notes=blocked_safety_notes,
                next_steps=["Проверьте установку Vosk вручную."],
            )

        active_capture_provider = self.capture_provider or self._default_capture_provider()
        if active_capture_provider is None:
            return self._blocked_result(
                ["Провайдер одноразового захвата микрофона недоступен."],
                warnings=gate_warnings,
                safety_notes=blocked_safety_notes,
                next_steps=["Проверьте доступность микрофона и аудиоадаптера."],
            )

        try:
            capture_result = self._capture_once(active_capture_provider)
        except Exception as exc:
            return self._blocked_result(
                [f"Одноразовый захват микрофона завершился ошибкой: {exc}"],
                warnings=gate_warnings,
                safety_notes=recognition_safety_notes,
                next_steps=["Проверьте микрофон и повторите явную one-shot команду."],
            )

        audio_payload = self._extract_audio_payload(capture_result)
        if audio_payload is None:
            return self._blocked_result(
                ["Одноразовый захват микрофона не вернул аудио для распознавания."],
                warnings=gate_warnings,
                safety_notes=recognition_safety_notes,
                next_steps=["Проверьте микрофон и повторите явную one-shot команду."],
            )

        try:
            recognized_text = self._recognize(runtime, model_path, audio_payload)
        except Exception as exc:
            return self._blocked_result(
                [f"Распознавание Vosk завершилось ошибкой: {exc}"],
                warnings=gate_warnings,
                safety_notes=recognition_safety_notes,
                next_steps=["Проверьте модель Vosk и совместимость пакета vosk."],
            )

        return OneShotVoskRealRecognitionResult(
            allowed=True,
            completed=True,
            blocked=False,
            recognized_text=recognized_text,
            capture_seconds=self._get_capture_seconds(capture_result),
            reasons=[],
            warnings=gate_warnings,
            safety_notes=recognition_safety_notes,
            next_steps=["Выполнение распознанного текста будет подключено отдельной задачей."],
        )

    @staticmethod
    def format_result(result):
        safety = " ".join(result.safety_notes)
        if result.blocked:
            lines = ["Реальное распознавание Vosk заблокировано."]
            if result.reasons:
                lines.append("Причины:")
                lines.extend(f"- {reason}" for reason in result.reasons)
            if result.next_steps:
                lines.append(f"Следующий шаг: {result.next_steps[0]}")
            lines.append(f"Безопасность: {safety}")
            return "\n".join(lines)

        if result.recognized_text:
            lines = [
                "Распознавание завершено.",
                f"Распознанный текст: {result.recognized_text}",
                "Команда не выполнялась автоматически.",
                f"Безопасность: {safety}",
            ]
            return "\n".join(lines)

        return "\n".join(
            [
                "Распознавание завершено, но речь не распознана.",
                "Команда не выполнялась автоматически.",
                f"Безопасность: {safety}",
            ]
        )

    def _get_model_path(self):
        try:
            return self.settings_manager.get_model_path()
        except AttributeError:
            return self.settings_manager.load_settings().get("model_path")

    def _check_gate(self, model_path):
        if self.gate_checker is not None:
            return self.gate_checker(model_path)
        return evaluate_vosk_local_recognition_gate(
            model_path=model_path,
            explicit_activation_required=True,
            microphone_capture_automatic=False,
            recognition_continuous=False,
        )

    def _default_capture_provider(self):
        return PcmOneShotCaptureProvider(capture_seconds=self.capture_seconds)

    @staticmethod
    def _load_vosk_runtime():
        try:
            import vosk
        except ImportError as exc:
            raise ImportError("vosk package is unavailable") from exc
        return vosk

    @staticmethod
    def _capture_once(capture_provider):
        if callable(capture_provider):
            return capture_provider()
        return capture_provider.capture_once()

    @staticmethod
    def _recognize(runtime, model_path, audio_payload):
        model = runtime.Model(str(model_path))
        recognizer = runtime.KaldiRecognizer(model, 16000)
        audio_bytes = OneShotVoskRealRecognition._audio_to_bytes(audio_payload)
        recognizer.AcceptWaveform(audio_bytes)
        result = json.loads(recognizer.FinalResult() or "{}")
        recognized_text = str(result.get("text") or "").strip()
        return recognized_text or None

    @staticmethod
    def _audio_to_bytes(audio_payload):
        if isinstance(audio_payload, bytes):
            return audio_payload
        if isinstance(audio_payload, bytearray):
            return bytes(audio_payload)
        if hasattr(audio_payload, "tobytes"):
            return audio_payload.tobytes()
        return bytes(audio_payload)

    @staticmethod
    def _extract_audio_payload(capture_result):
        if isinstance(capture_result, dict):
            if capture_result.get("audio_captured", True) is False:
                return None
            if "audio" in capture_result and capture_result["audio"] is not None:
                return capture_result["audio"]
            if (
                "audio_payload" in capture_result
                and capture_result["audio_payload"] is not None
            ):
                return capture_result["audio_payload"]
            return None
        if getattr(capture_result, "audio_captured", True) is False:
            return None
        audio = getattr(capture_result, "audio", None)
        if audio is not None:
            return audio
        audio_payload = getattr(capture_result, "audio_payload", None)
        if audio_payload is not None:
            return audio_payload
        return capture_result

    def _blocked_result(
        self,
        reasons,
        warnings=None,
        safety_notes=None,
        next_steps=None,
    ):
        return OneShotVoskRealRecognitionResult(
            allowed=False,
            completed=False,
            blocked=True,
            recognized_text=None,
            capture_seconds=0,
            reasons=list(reasons),
            warnings=list(warnings or []),
            safety_notes=list(safety_notes or DEFAULT_BLOCKED_SAFETY_NOTES),
            next_steps=list(next_steps or []),
        )

    def _dependency_blocked_result(self, safety_notes):
        if self.dependency_checker is None:
            return None

        readiness = self.dependency_checker.check()
        if readiness.ready:
            return None

        reasons = []
        next_steps = []
        for dependency in readiness.missing_dependencies:
            reasons.append(self._missing_dependency_reason(dependency.name))
            next_steps.append(dependency.manual_install_command)

        return self._blocked_result(
            reasons,
            safety_notes=safety_notes,
            next_steps=next_steps,
        )

    @staticmethod
    def _missing_dependency_reason(dependency_name):
        if dependency_name == "numpy":
            return (
                "Зависимость NumPy не найдена. One-shot захват микрофона может не работать."
            )
        if dependency_name == "sounddevice":
            return (
                "Зависимость sounddevice не найдена. One-shot захват микрофона может не работать."
            )
        if dependency_name == "vosk":
            return (
                "Пакет vosk не найден. Локальное распознавание речи Vosk не будет работать."
            )
        return f"Зависимость {dependency_name} не найдена."

    def _get_capture_seconds(self, capture_result):
        if isinstance(capture_result, dict):
            return capture_result.get("duration_seconds", self.capture_seconds)
        return self.capture_seconds

    @staticmethod
    def _get_value(source, key, default=None):
        if isinstance(source, dict):
            return source.get(key, default)
        return getattr(source, key, default)


class PcmOneShotCaptureProvider:
    """Minimal PCM-preserving one-shot adapter for Vosk."""

    def __init__(
        self,
        adapter=None,
        mode_manager=None,
        capture_seconds=DEFAULT_CAPTURE_DURATION_SECONDS,
        hard_max_capture_seconds=HARD_MAX_CAPTURE_DURATION_SECONDS,
    ):
        self.adapter = adapter or SoundDeviceOneShotCaptureAdapter()
        self.mode_manager = mode_manager or self._explicit_one_shot_mode_manager()
        self.capture_seconds = capture_seconds
        self.hard_max_capture_seconds = hard_max_capture_seconds

    def capture_once(self):
        duration = self._validate_duration(self.capture_seconds)
        if not self.mode_manager.allows_limited_listening():
            return {
                "audio_captured": False,
                "audio": None,
                "duration_seconds": duration,
                "error": "microphone listening mode must allow limited listening",
            }
        if not self.adapter.is_available():
            return {
                "audio_captured": False,
                "audio": None,
                "duration_seconds": duration,
                "error": "audio adapter is unavailable",
            }
        capture_result = self.adapter.capture_once(duration)
        if isinstance(capture_result, dict):
            result = dict(capture_result)
            result.setdefault("duration_seconds", duration)
            result.setdefault("stored_on_disk", False)
            return result
        return {
            "audio_captured": True,
            "audio": capture_result,
            "duration_seconds": duration,
            "stored_on_disk": False,
        }

    def _validate_duration(self, duration_seconds):
        if isinstance(duration_seconds, bool):
            raise ValueError("Capture duration must be a positive number.")
        duration = float(duration_seconds)
        if duration <= 0 or duration > self.hard_max_capture_seconds:
            raise ValueError("Capture duration must be within one-shot safety limits.")
        return duration

    @staticmethod
    def _explicit_one_shot_mode_manager():
        manager = MicrophoneListeningModeManager()
        manager.switch_to_partial()
        return manager
