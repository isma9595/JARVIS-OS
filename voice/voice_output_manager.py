from voice.speech_synthesis_backend import DryRunSpeechSynthesisBackend
from voice.voice_output_safety import VoiceOutputSafetyController
from voice.windows_local_tts_backend import WindowsLocalSpeechSynthesisBackend


class VoiceOutputManager:
    OFF = "OFF"
    DRY_RUN = "DRY_RUN"
    WINDOWS_LOCAL = "WINDOWS_LOCAL"
    MAX_TEXT_LENGTH = 500

    def __init__(
        self,
        backend=None,
        mode=OFF,
        windows_local_backend=None,
        safety_controller=None,
    ):
        self.backend = backend or DryRunSpeechSynthesisBackend()
        self.windows_local_backend = windows_local_backend or WindowsLocalSpeechSynthesisBackend()
        self.safety_controller = safety_controller or VoiceOutputSafetyController()
        self.mode = self._normalize_mode(mode)

    def status(self):
        return {
            "mode": self.mode,
            "enabled": self.is_enabled(),
            "backend_name": self._active_backend().get_name(),
            "muted": self.safety_controller.status().muted,
            "skip_next": self.safety_controller.status().skip_next,
            "safety_notes": self._safety_notes(),
            "message": self.status_message(),
        }

    def status_message(self):
        state = "отключён"
        if self.mode == self.DRY_RUN:
            state = "включён в тестовом режиме"
        elif self.mode == self.WINDOWS_LOCAL:
            state = "включён в локальном режиме Windows"
        return (
            f"Голосовой ответ {state}.\n"
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

    def enable_windows_local(self):
        diagnostics = self.windows_local_backend.availability_diagnostics()
        if not diagnostics["available"]:
            self.mode = self.OFF
            return {
                "mode": self.mode,
                "enabled": False,
                "available": False,
                "message": (
                    "Локальный голос Windows недоступен. "
                    "Используйте диагностику: диагностика локального голоса."
                ),
                "diagnostics": diagnostics,
            }

        self.mode = self.WINDOWS_LOCAL
        return {
            "mode": self.mode,
            "enabled": True,
            "available": True,
            "message": (
                "Локальный голос Windows включён.\n"
                "Режим: WINDOWS_LOCAL.\n"
                "Безопасность: используется локальный TTS, облако не используется, аудиофайлы не сохраняются."
            ),
            "diagnostics": diagnostics,
        }

    def disable(self):
        self.mode = self.OFF
        return {
            "mode": self.mode,
            "enabled": False,
            "message": "Голосовой ответ отключён.",
        }

    def is_enabled(self):
        return self.mode in {self.DRY_RUN, self.WINDOWS_LOCAL}

    def local_tts_status(self):
        diagnostics = self.windows_local_backend.availability_diagnostics()
        if diagnostics["available"]:
            message = (
                "Локальный голос Windows доступен.\n"
                f"Backend: {self.windows_local_backend.get_name()}.\n"
                "Безопасность: используется локальный TTS, облако не используется, аудиофайлы не сохраняются."
            )
        else:
            message = (
                "Локальный голос Windows недоступен.\n"
                f"Причина: {diagnostics['reason']}.\n"
                "Можно использовать тестовый режим: включить тестовый голос."
            )
        return {
            "available": diagnostics["available"],
            "backend_name": self.windows_local_backend.get_name(),
            "mode": self.WINDOWS_LOCAL,
            "message": message,
            "diagnostics": diagnostics,
        }

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
                    "включить тестовый голос. Для реального локального голоса используйте: "
                    "включить локальный голос."
                ),
                "safety_notes": self._safety_notes(),
            }

        safety_decision = self.safety_controller.can_speak(source=source)
        if not safety_decision.allowed:
            if safety_decision.reason == "skip_next":
                self.safety_controller.consume_skip_if_needed()
                message = "Следующая голосовая озвучка пропущена по команде пользователя."
                intent = "voice.output.skipped"
            else:
                message = "Голосовая озвучка заблокирована: включён тихий режим."
                intent = "voice.output.muted"
            return {
                "success": False,
                "intent": intent,
                "mode": self.mode,
                "source": source,
                "spoken_text": normalized_text,
                "backend_called": False,
                "message": message,
                "safety_notes": safety_decision.safety_notes,
            }

        result = self._active_backend().synthesize(normalized_text, mode=self.mode)
        if self.mode == self.WINDOWS_LOCAL:
            message = self._windows_local_message(result)
        else:
            message = self._dry_run_message(result.spoken_text)
        return {
            "success": result.success,
            "intent": "voice.output.spoken",
            "mode": self.mode,
            "source": source,
            "spoken_text": result.spoken_text,
            "backend_name": result.backend_name,
            "backend_called": True,
            "result": result,
            "message": message,
            "safety_notes": result.safety_notes,
            "error": result.error,
        }

    def test_voice(self):
        if self.mode == self.WINDOWS_LOCAL:
            return self.speak(
                "Исмаил, локальный голос JARVIS работает.",
                source="test",
            )
        return self.speak(
            "Исмаил, голосовой ответ JARVIS готов к тестированию.",
            source="test",
        )

    def test_local_voice(self):
        if self.mode != self.WINDOWS_LOCAL:
            return {
                "success": False,
                "intent": "voice.output.local_test.not_enabled",
                "mode": self.mode,
                "source": "test",
                "spoken_text": "",
                "backend_called": False,
                "message": (
                    "Локальный голос Windows не включён. "
                    "Сначала выполните: включить локальный голос. "
                    "Для проверки доступности используйте: диагностика локального голоса."
                ),
                "safety_notes": self._safety_notes(),
            }
        return self.test_voice()

    def capabilities_message(self):
        return (
            "Сейчас голосовой ответ доступен только явно: в тестовом режиме DRY_RUN или через локальный Windows TTS после включения. "
            "Команды: статус голосового ответа, диагностика локального голоса, включить тестовый голос, включить локальный голос, выключить голос, "
            "скажи: <текст>, произнеси: <текст>, озвучь: <текст>, тест голоса, тест локального голоса. "
            "Облако не используется, аудиофайлы не сохраняются, автоматические голосовые ответы не включаются."
        )

    def _normalize_mode(self, mode):
        normalized = str(mode or self.OFF).strip().upper().replace("-", "_").replace(" ", "_")
        if normalized in {"DRY_RUN", "TEST", "ТЕСТ"}:
            return self.DRY_RUN
        if normalized in {"WINDOWS_LOCAL", "LOCAL", "WINDOWS", "ЛОКАЛЬНЫЙ", "ЛОКАЛЬНЫЙ_WINDOWS"}:
            return self.WINDOWS_LOCAL
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

    def _windows_local_message(self, result):
        if result.success:
            return (
                "Голосовая озвучка выполнена локально.\n"
                "Безопасность: облако не использовалось, аудиофайл не сохранялся."
            )
        return (
            "Не удалось выполнить локальную озвучку.\n"
            f"Причина: {result.error}.\n"
            "Можно переключиться в тестовый режим: включить тестовый голос."
        )

    def _safety_notes(self):
        notes = [
            "Облачный TTS не используется.",
            "Аудиофайлы не сохраняются.",
        ]
        safety_status = self.safety_controller.status()
        if safety_status.muted:
            notes.append("Тихий режим включён: голосовая озвучка блокируется.")
        if safety_status.skip_next:
            notes.append("Следующая голосовая озвучка будет пропущена один раз.")
        if self.mode == self.WINDOWS_LOCAL:
            notes.append("Реальное воспроизведение запускается только для явных команд озвучки.")
        else:
            notes.append("Реальное воспроизведение звука не запускается.")
        return notes

    def _active_backend(self):
        if self.mode == self.WINDOWS_LOCAL:
            return self.windows_local_backend
        return self.backend
