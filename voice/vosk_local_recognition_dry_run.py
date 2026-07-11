"""Safe fake-audio dry run for a future local Vosk recognition path."""

from dataclasses import dataclass, field

from voice.vosk_local_backend import VoskLocalBackend
from voice.vosk_local_recognition_gate import evaluate_vosk_local_recognition_gate


DEFAULT_FAKE_RECOGNIZED_TEXT = "тестовая команда"


@dataclass(frozen=True)
class VoskLocalRecognitionDryRunResult:
    success: bool
    allowed: bool
    dry_run: bool
    used_fake_audio: bool
    microphone_used: bool
    real_model_loaded: bool
    recognized_text: str | None = None
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    message: str = ""
    next_steps: list[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "success": self.success,
            "allowed": self.allowed,
            "dry_run": self.dry_run,
            "used_fake_audio": self.used_fake_audio,
            "microphone_used": self.microphone_used,
            "real_model_loaded": self.real_model_loaded,
            "recognized_text": self.recognized_text,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "message": self.message,
            "next_steps": list(self.next_steps),
        }


class VoskLocalRecognitionDryRun:
    """Run only a gate-checked fake recognizer path with no audio side effects."""

    def __init__(self, gate_checker=None, recognizer=None):
        self.gate_checker = gate_checker or self._default_gate_check
        self.recognizer = recognizer or self._default_fake_recognizer

    def run(self):
        gate_result = self.gate_checker()
        allowed = bool(self._get_value(gate_result, "allowed", False))
        blockers = list(self._get_value(gate_result, "blockers", []))
        warnings = list(self._get_value(gate_result, "warnings", []))
        next_steps = list(self._get_value(gate_result, "next_steps", []))

        if not allowed:
            return VoskLocalRecognitionDryRunResult(
                success=False,
                allowed=False,
                dry_run=True,
                used_fake_audio=True,
                microphone_used=False,
                real_model_loaded=False,
                recognized_text=None,
                blockers=blockers,
                warnings=warnings,
                message=self._blocked_message(blockers),
                next_steps=next_steps,
            )

        try:
            recognized_text = self._run_fake_recognizer()
        except Exception as exc:
            failure = f"Пробный распознаватель вернул ошибку: {exc}"
            return VoskLocalRecognitionDryRunResult(
                success=False,
                allowed=True,
                dry_run=True,
                used_fake_audio=True,
                microphone_used=False,
                real_model_loaded=False,
                recognized_text=None,
                blockers=blockers + [failure],
                warnings=warnings,
                message=(
                    "Пробный запуск локального распознавания Vosk не завершился. "
                    "Использовались только тестовые данные. Реальный микрофон не запускался."
                ),
                next_steps=next_steps,
            )

        return VoskLocalRecognitionDryRunResult(
            success=True,
            allowed=True,
            dry_run=True,
            used_fake_audio=True,
            microphone_used=False,
            real_model_loaded=False,
            recognized_text=recognized_text,
            blockers=blockers,
            warnings=warnings,
            message=(
                "Пробный запуск локального распознавания Vosk выполнен в безопасном режиме. "
                "Использовались тестовые данные. Реальный микрофон не запускался. "
                "Настоящая модель Vosk не загружалась."
            ),
            next_steps=next_steps,
        )

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
    def _default_fake_recognizer(_fake_audio):
        return DEFAULT_FAKE_RECOGNIZED_TEXT

    def _run_fake_recognizer(self):
        fake_audio = self._fake_audio_payload()
        if callable(self.recognizer):
            result = self.recognizer(fake_audio)
        else:
            result = self.recognizer.recognize(fake_audio)

        if isinstance(result, dict):
            result = result.get("text")

        recognized_text = "" if result is None else str(result).strip()
        return recognized_text or None

    @staticmethod
    def _fake_audio_payload():
        return {
            "source": "vosk_dry_run_stub",
            "audio": b"",
            "stored_on_disk": False,
            "microphone_used": False,
        }

    @staticmethod
    def _blocked_message(blockers):
        lines = [
            "Пробный запуск локального распознавания Vosk заблокирован.",
        ]
        if blockers:
            lines.append("Причины:")
            lines.extend(f"- {blocker}" for blocker in blockers)
        lines.extend(
            [
                "Использовались только тестовые данные.",
                "Реальный микрофон не запускался.",
                "Настоящая модель Vosk не загружалась.",
            ]
        )
        return "\n".join(lines)

    @staticmethod
    def _get_value(source, key, default=None):
        if isinstance(source, dict):
            return source.get(key, default)
        return getattr(source, key, default)
