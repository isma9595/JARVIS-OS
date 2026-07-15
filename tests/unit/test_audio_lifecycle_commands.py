from core.command_processor import CommandProcessor


def test_audio_lifecycle_status_commands_work_without_audio_or_action_router():
    class FailingActionRouter:
        calls = 0

        def route(self, command):
            self.calls += 1
            raise AssertionError("audio lifecycle status must not route to ActionRouter")

    processor = CommandProcessor()
    processor.action_router = FailingActionRouter()

    for command in (
        "статус audio lifecycle",
        "статус audio",
        "статус аудио",
        "статус аудио цикла",
        "статус голосового lifecycle",
        "статус голосового цикла расширенный",
    ):
        result = processor.process(command)

        assert result["intent"] == "audio_lifecycle.status"
        assert "audio lifecycle foundation: yes" in result["response"]
        assert "state: idle" in result["response"]
        assert "capture mode: off" in result["response"]
        assert "output mode: off" in result["response"]
        assert "microphone active: no" in result["response"]
        assert "one-shot active: no" in result["response"]
        assert "continuous listening enabled: no" in result["response"]
        assert "continuous listening allowed: no" in result["response"]
        assert "network used: no" in result["response"]
        assert "audio saved: no" in result["response"]
        assert "auto listening on startup: no" in result["response"]
        assert "no command executed" in result["response"]

    assert processor.action_router.calls == 0


def test_audio_lifecycle_capabilities_commands_work():
    processor = CommandProcessor()

    for command in (
        "audio lifecycle capabilities",
        "возможности audio lifecycle",
        "возможности аудио цикла",
        "возможности голосового цикла",
    ):
        result = processor.process(command)

        assert result["intent"] == "audio_lifecycle.capabilities"
        assert "can report safe lifecycle state" in result["response"]
        assert "can expose status to future Desktop UI" in result["response"]
        assert "does not start microphone" in result["response"]
        assert "does not play audio" in result["response"]
        assert "does not enable continuous listening" in result["response"]


def test_reset_audio_lifecycle_metadata_only():
    processor = CommandProcessor()
    processor.audio_lifecycle_controller.start_one_shot_metadata_only()

    result = processor.process("reset audio lifecycle")

    assert result["intent"] == "audio_lifecycle.reset_metadata_only"
    assert "next state: idle" in result["response"]
    assert "network used: no" in result["response"]
    assert "audio saved: no" in result["response"]
    assert "microphone called: no" in result["response"]
    assert "tts called: no" in result["response"]
    assert "no command executed" in result["response"]
    assert processor.audio_lifecycle_controller.status().state == "idle"
