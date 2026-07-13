from core.command_processor import CommandProcessor
from voice import SpeechSynthesisResult, VoiceOutputManager


class FakeDryRunTtsBackend:
    def __init__(self):
        self.calls = []

    def get_name(self):
        return "dry_run"

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


def test_voice_cycle_offline_smoke_sequence():
    backend = FakeDryRunTtsBackend()
    manager = VoiceOutputManager(backend=backend)
    processor = CommandProcessor(voice_output_manager=manager)

    system_status = processor.process("статус системы")
    assert system_status["intent"] == "system.status"

    cycle_status = processor.process("статус голосового цикла")
    assert cycle_status["intent"] == "voice.cycle.status"
    assert "one-shot" in cycle_status["response"]

    command_map = processor.process("карта голосовых команд")
    assert command_map["intent"] == "voice.cycle.command_map"
    assert "Safety / mute:" in command_map["response"]

    safety_status = processor.process("статус голосовой безопасности")
    assert safety_status["intent"] == "voice.output.safety.status"

    dry_run = processor.process("включить тестовый голос")
    assert dry_run["intent"] == "voice.output.dry_run.enabled"

    say_test = processor.process("скажи: финальная проверка голоса")
    assert say_test["intent"] == "voice.output.spoken"
    assert backend.calls[-1] == ("финальная проверка голоса", "DRY_RUN")

    status_after_voice = processor.process("статус системы")
    assert status_after_voice["intent"] == "system.status"

    repeat = processor.process("повтори")
    assert repeat["intent"] == "assistant.speak_last_response.dry_run"
    assert "Активных сервисов" in backend.calls[-1][0]

    skip = processor.process("не озвучивай следующий ответ")
    assert skip["intent"] == "voice.output.safety.skip_next"

    skipped_repeat = processor.process("повтори")
    assert skipped_repeat["intent"] == "assistant.speak_last_response.skipped"
    calls_after_skip = len(backend.calls)

    repeat_again = processor.process("повтори")
    assert repeat_again["intent"] == "assistant.speak_last_response.dry_run"
    assert len(backend.calls) == calls_after_skip + 1

    muted = processor.process("замолчи")
    assert muted["intent"] == "voice.output.safety.muted"

    blocked_repeat = processor.process("повтори")
    assert blocked_repeat["intent"] == "assistant.speak_last_response.muted"

    unmuted = processor.process("снова говори")
    assert unmuted["intent"] == "voice.output.safety.unmuted"

    simulated_status = processor.process("симулируй распознавание: статус системы")
    assert simulated_status["intent"] == "system.status"
    assert simulated_status["safe_voice_command_allowed"] is True

    what_i_said = processor.process("что я сказал")
    assert what_i_said["intent"] == "voice.history.last"
    assert "статус системы" in what_i_said["response"]

    repeat_last_voice = processor.process("повтори последнюю голосовую команду")
    assert repeat_last_voice["intent"] == "voice.history.repeat.dry_run"
    assert "Команда не выполнялась повторно" in repeat_last_voice["response"]

    clarify = processor.process("объясни короче")
    assert clarify["intent"] == "assistant.clarify.short"

    dialogue_status = processor.process("статус голосового диалога")
    assert dialogue_status["intent"] == "voice.dialogue.status"

    dialogue_enabled = processor.process("включить голосовой диалог")
    assert dialogue_enabled["intent"] == "voice.dialogue.manual.enabled"

    backend.calls.clear()
    spoken_system_status = processor.process("статус системы")
    assert spoken_system_status["intent"] == "system.status"
    assert backend.calls

    disabled = processor.process("выключить голос")
    assert disabled["intent"] == "voice.output.disabled"
    assert processor.voice_dialogue_mode_manager.is_manual_enabled() is False

    final_safety_status = processor.process("статус голосовой безопасности")
    assert final_safety_status["intent"] == "voice.output.safety.status"
