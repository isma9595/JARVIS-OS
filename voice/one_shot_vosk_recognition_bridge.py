"""Safe coordinator for a future one-shot microphone to Vosk path."""

from dataclasses import dataclass, field

from voice.vosk_local_backend import VoskLocalBackend
from voice.vosk_local_recognition_gate import evaluate_vosk_local_recognition_gate


DEFAULT_BRIDGE_SAFETY_NOTES = [
    "Реальный микрофон не запускался автоматически.",
    "Постоянное прослушивание не использовалось.",
    "Аудио не отправлялось в облако.",
    "Распознанный текст не выполнялся как команда.",
]


@dataclass(frozen=True)
class OneShotVoskRecognitionBridgeResult:
    allowed: bool
    completed: bool
    blocked: bool
    simulated: bool
    recognized_text: str | None = None
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    safety_notes: list[str] = field(default_factory=lambda: list(DEFAULT_BRIDGE_SAFETY_NOTES))

    def to_dict(self):
        return {
            "allowed": self.allowed,
            "completed": self.completed,
            "blocked": self.blocked,
            "simulated": self.simulated,
            "recognized_text": self.recognized_text,
            "reasons": list(self.reasons),
            "warnings": list(self.warnings),
            "safety_notes": list(self.safety_notes),
        }


class OneShotVoskRecognitionBridge:
    """Coordinate only explicit, injected one-shot capture and recognition."""

    def __init__(self, gate_checker=None, capture_provider=None, recognizer=None):
        self.gate_checker = gate_checker or self._default_gate_check
        self.capture_provider = capture_provider
        self.recognizer = recognizer

    def run_once(
        self,
        explicit_one_shot_requested=False,
        capture_provider=None,
        recognizer=None,
    ):
        safety_notes = list(DEFAULT_BRIDGE_SAFETY_NOTES)

        if not explicit_one_shot_requested:
            return self._blocked_result(
                ["Нужен явный one-shot запрос пользователя."],
                safety_notes=safety_notes,
            )

        gate_result = self.gate_checker()
        gate_allowed = bool(self._get_value(gate_result, "allowed", False))
        gate_blockers = list(self._get_value(gate_result, "blockers", []))
        gate_warnings = list(self._get_value(gate_result, "warnings", []))

        if not gate_allowed:
            reasons = gate_blockers or ["Локальное распознавание Vosk не разрешено gate."]
            return self._blocked_result(
                reasons,
                warnings=gate_warnings,
                safety_notes=safety_notes,
            )

        active_capture_provider = capture_provider or self.capture_provider
        if active_capture_provider is None:
            return self._blocked_result(
                ["Провайдер one-shot аудио не передан."],
                warnings=gate_warnings,
                safety_notes=safety_notes,
            )

        active_recognizer = recognizer or self.recognizer
        if active_recognizer is None:
            return self._blocked_result(
                ["Распознаватель Vosk не передан."],
                warnings=gate_warnings,
                safety_notes=safety_notes,
            )

        try:
            capture_result = self._capture_once(active_capture_provider)
        except Exception as exc:
            return self._blocked_result(
                [f"Провайдер one-shot аудио вернул ошибку: {exc}"],
                warnings=gate_warnings,
                safety_notes=safety_notes,
            )

        audio_payload = self._extract_audio_payload(capture_result)
        if audio_payload is None:
            return self._blocked_result(
                ["Провайдер one-shot аудио не вернул аудио для распознавания."],
                warnings=gate_warnings,
                safety_notes=safety_notes,
            )

        try:
            recognized_text = self._recognize(active_recognizer, audio_payload)
        except Exception as exc:
            return self._blocked_result(
                [f"Распознаватель Vosk вернул ошибку: {exc}"],
                warnings=gate_warnings,
                safety_notes=safety_notes,
            )

        return OneShotVoskRecognitionBridgeResult(
            allowed=True,
            completed=True,
            blocked=False,
            simulated=self._is_simulated_capture(capture_result),
            recognized_text=recognized_text,
            reasons=[],
            warnings=gate_warnings,
            safety_notes=safety_notes,
        )

    @staticmethod
    def format_result(result):
        if result.blocked:
            lines = ["One-shot Vosk bridge заблокирован."]
            if result.reasons:
                lines.append("Причины:")
                lines.extend(f"- {reason}" for reason in result.reasons)
            lines.append("Безопасность: " + " ".join(result.safety_notes))
            return "\n".join(lines)

        mode = "безопасном тестовом режиме" if result.simulated else "безопасном режиме"
        lines = [f"One-shot Vosk bridge выполнен в {mode}."]
        if result.recognized_text:
            lines.append(f"Распознанный текст: {result.recognized_text}")
        lines.append("Безопасность: " + " ".join(result.safety_notes))
        return "\n".join(lines)

    @staticmethod
    def _default_gate_check():
        backend = VoskLocalBackend()
        status = backend.get_status()
        return evaluate_vosk_local_recognition_gate(
            model_path=status.get("model_path"),
            package_available=status.get("vosk_package_available"),
            explicit_activation_required=True,
            microphone_capture_automatic=False,
            recognition_continuous=False,
        )

    @staticmethod
    def _blocked_result(reasons, warnings=None, safety_notes=None):
        return OneShotVoskRecognitionBridgeResult(
            allowed=False,
            completed=False,
            blocked=True,
            simulated=False,
            recognized_text=None,
            reasons=list(reasons),
            warnings=list(warnings or []),
            safety_notes=list(safety_notes or DEFAULT_BRIDGE_SAFETY_NOTES),
        )

    @staticmethod
    def _capture_once(capture_provider):
        if callable(capture_provider):
            return capture_provider()
        return capture_provider.capture_once()

    @staticmethod
    def _recognize(recognizer, audio_payload):
        if callable(recognizer):
            result = recognizer(audio_payload)
        else:
            result = recognizer.recognize(audio_payload)

        if isinstance(result, dict):
            result = result.get("text")

        recognized_text = "" if result is None else str(result).strip()
        return recognized_text or None

    @staticmethod
    def _extract_audio_payload(capture_result):
        if isinstance(capture_result, dict):
            if not capture_result.get("audio_captured", True):
                return None
            if "audio" in capture_result:
                return capture_result.get("audio")
            if "audio_payload" in capture_result:
                return capture_result.get("audio_payload")
            return capture_result
        return capture_result

    @staticmethod
    def _is_simulated_capture(capture_result):
        if isinstance(capture_result, dict):
            return bool(
                capture_result.get("simulated")
                or capture_result.get("fake")
                or capture_result.get("test_data")
                or capture_result.get("source") in {"fake", "test", "injected_test"}
            )
        return True

    @staticmethod
    def _get_value(source, key, default=None):
        if isinstance(source, dict):
            return source.get(key, default)
        return getattr(source, key, default)
