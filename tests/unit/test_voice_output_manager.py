from voice import SpeechSynthesisResult, VoiceOutputManager


class TrackingBackend:
    def __init__(self):
        self.calls = []

    def get_name(self):
        return "tracking"

    def synthesize(self, text, mode="DRY_RUN"):
        self.calls.append((text, mode))
        return SpeechSynthesisResult(
            success=True,
            spoken_text=text,
            backend_name=self.get_name(),
            mode=mode,
            safety_notes=[
                "Реальный звук не воспроизводился.",
                "Облачный TTS не использовался.",
                "Аудиофайл не сохранялся.",
            ],
        )


def test_default_mode_is_off():
    manager = VoiceOutputManager()

    assert manager.mode == "OFF"
    assert manager.is_enabled() is False


def test_status_reports_off():
    manager = VoiceOutputManager()

    status = manager.status()

    assert status["mode"] == "OFF"
    assert status["enabled"] is False
    assert "Голосовой ответ отключён." in status["message"]


def test_enable_dry_run():
    manager = VoiceOutputManager()

    result = manager.enable_dry_run()

    assert result["mode"] == "DRY_RUN"
    assert manager.is_enabled() is True
    assert "Тестовый голосовой режим включён." in result["message"]


def test_disable_back_to_off():
    manager = VoiceOutputManager()
    manager.enable_dry_run()

    result = manager.disable()

    assert result["mode"] == "OFF"
    assert manager.is_enabled() is False
    assert result["message"] == "Голосовой ответ отключён."


def test_speak_while_off_does_not_call_backend():
    backend = TrackingBackend()
    manager = VoiceOutputManager(backend=backend)

    result = manager.speak("тест")

    assert result["intent"] == "voice.output.disabled"
    assert result["backend_called"] is False
    assert backend.calls == []
    assert "Включите тестовый режим" in result["message"]


def test_speak_while_dry_run_returns_dry_run_result():
    backend = TrackingBackend()
    manager = VoiceOutputManager(backend=backend)
    manager.enable_dry_run()

    result = manager.speak("Исмаил, система работает.")

    assert result["intent"] == "voice.output.spoken"
    assert result["backend_called"] is True
    assert backend.calls == [("Исмаил, система работает.", "DRY_RUN")]
    assert "[TTS dry-run] Исмаил, система работает." in result["message"]


def test_empty_text_is_rejected():
    backend = TrackingBackend()
    manager = VoiceOutputManager(backend=backend)
    manager.enable_dry_run()

    result = manager.speak("   ")

    assert result["intent"] == "voice.output.empty"
    assert result["backend_called"] is False
    assert backend.calls == []
    assert result["message"] == "Укажите текст для озвучки."


def test_long_text_is_capped():
    backend = TrackingBackend()
    manager = VoiceOutputManager(backend=backend)
    manager.enable_dry_run()
    long_text = "а" * (manager.MAX_TEXT_LENGTH + 20)

    result = manager.speak(long_text)

    assert len(result["spoken_text"]) == manager.MAX_TEXT_LENGTH
    assert len(backend.calls[0][0]) == manager.MAX_TEXT_LENGTH


def test_safety_notes_represent_no_file_cloud_or_audio_behavior():
    manager = VoiceOutputManager()

    status = manager.status()

    assert "Облачный TTS не используется." in status["safety_notes"]
    assert "Аудиофайлы не сохраняются." in status["safety_notes"]
    assert "Реальное воспроизведение звука не запускается." in status["safety_notes"]
