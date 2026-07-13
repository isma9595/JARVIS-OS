from voice.speech_synthesis_backend import DryRunSpeechSynthesisBackend


class VoiceOutputManager:
    OFF = "OFF"
    DRY_RUN = "DRY_RUN"
    MAX_TEXT_LENGTH = 500

    def __init__(self, backend=None, mode=OFF):
        self.backend = backend or DryRunSpeechSynthesisBackend()
        self.mode = self._normalize_mode(mode)

    def status(self):
        return {
            "mode": self.mode,
            "enabled": self.is_enabled(),
            "backend_name": self.backend.get_name(),
            "safety_notes": self._safety_notes(),
            "message": self.status_message(),
        }

    def status_message(self):
        return (
            f"Голосовой ответ {'включён в тестовом режиме' if self.is_enabled() else 'отключён'}.\n"
            f"Режим: {self.mode}.\n"
            "Безопасность: облачный TTS не используется, аудиофайлы не сохраняются."
        )

    def set_mode(self, mode):
        self.mode = self._normalize_mode(mode)
        return self.status()

    def enable_dry_run(self):
        self.mode = self.DRY_RUN
        return {
            "mode": self.mode,
            "enabled": True,
            "message": (
                "Тестовый голосовой режим включён.\n"
                "Режим: DRY_RUN.\n"
                "JARVIS будет показывать, что он бы произнёс, без реального воспроизведения звука."
            ),
        }

    def disable(self):
        self.mode = self.OFF
        return {
            "mode": self.mode,
            "enabled": False,
            "message": "Голосовой ответ отключён.",
        }

    def is_enabled(self):
        return self.mode == self.DRY_RUN

    def speak(self, text, source="manual"):
        normalized_text = self._normalize_text(text)
        if not normalized_text:
            return {
                "success": False,
                "intent": "voice.output.empty",
                "mode": self.mode,
                "source": source,
                "spoken_text": "",
                "backend_called": False,
                "message": "Укажите текст для озвучки.",
                "safety_notes": self._safety_notes(),
            }

        if self.mode == self.OFF:
            return {
                "success": False,
                "intent": "voice.output.disabled",
                "mode": self.mode,
                "source": source,
                "spoken_text": normalized_text,
                "backend_called": False,
                "message": (
                    "Голосовой ответ отключён. Включите тестовый режим командой: "
                    "включить тестовый голос."
                ),
                "safety_notes": self._safety_notes(),
            }

        result = self.backend.synthesize(normalized_text, mode=self.mode)
        return {
            "success": result.success,
            "intent": "voice.output.spoken",
            "mode": self.mode,
            "source": source,
            "spoken_text": result.spoken_text,
            "backend_name": result.backend_name,
            "backend_called": True,
            "result": result,
            "message": self._dry_run_message(result.spoken_text),
            "safety_notes": result.safety_notes,
            "error": result.error,
        }

    def test_voice(self):
        return self.speak(
            "Исмаил, голосовой ответ JARVIS готов к тестированию.",
            source="test",
        )

    def capabilities_message(self):
        return (
            "Сейчас голосовой ответ доступен только явно и только в тестовом режиме. "
            "Команды: статус голосового ответа, включить тестовый голос, выключить голос, "
            "скажи: <текст>, тест голоса. Облако не используется, аудиофайлы не сохраняются."
        )

    def _normalize_mode(self, mode):
        normalized = str(mode or self.OFF).strip().upper().replace("-", "_").replace(" ", "_")
        if normalized in {"DRY_RUN", "TEST", "ТЕСТ"}:
            return self.DRY_RUN
        return self.OFF

    def _normalize_text(self, text):
        normalized = " ".join(str(text or "").strip().split())
        if len(normalized) > self.MAX_TEXT_LENGTH:
            return normalized[: self.MAX_TEXT_LENGTH].rstrip()
        return normalized

    def _dry_run_message(self, text):
        return (
            "Тестовая озвучка:\n"
            f"[TTS dry-run] {text}\n"
            "Безопасность: реальный звук не воспроизводился, облако не использовалось, аудиофайл не сохранялся."
        )

    def _safety_notes(self):
        return [
            "Облачный TTS не используется.",
            "Аудиофайлы не сохраняются.",
            "Реальное воспроизведение звука не запускается.",
        ]
