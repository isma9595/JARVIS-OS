from core.command_processor import CommandProcessor
from voice import OneShotVoskRealRecognitionResult


class FakeRealRecognition:
    def __init__(self, results):
        self.results = list(results)
        self.calls = 0

    def run_once(self, explicit_one_shot_requested=False):
        assert explicit_one_shot_requested is True
        result = self.results[self.calls]
        self.calls += 1
        return result


def success_result(text="версия"):
    return OneShotVoskRealRecognitionResult(
        allowed=True,
        completed=True,
        blocked=False,
        recognized_text=text,
        capture_seconds=2,
    )


def empty_result():
    return OneShotVoskRealRecognitionResult(
        allowed=True,
        completed=True,
        blocked=False,
        recognized_text=None,
        capture_seconds=2,
    )


def blocked_result():
    return OneShotVoskRealRecognitionResult(
        allowed=False,
        completed=False,
        blocked=True,
        recognized_text=None,
        capture_seconds=0,
        reasons=["Пакет vosk не установлен."],
        safety_notes=[
            "Микрофон не запускался.",
            "Постоянное прослушивание не использовалось.",
            "Аудио не отправлялось в облако.",
            "Распознанный текст не выполнялся как команда.",
        ],
    )


def test_safe_status_system_auto_executes_without_pending_confirmation():
    processor = CommandProcessor(
        one_shot_vosk_real_recognition=FakeRealRecognition(
            [success_result("статус системы")]
        )
    )

    result = processor.process("распознай голос один раз")

    assert processor.has_pending_voice_command() is False
    assert result["intent"] == "system.status"
    assert "Я распознал безопасную голосовую команду: \"статус системы\"." in result["response"]
    assert "Выполняю: статус системы" in result["response"]
    assert "read-only" in result["response"]
    assert "Активных сервисов" in result["response"]


def test_safe_help_auto_executes_without_pending_confirmation():
    processor = CommandProcessor(
        one_shot_vosk_real_recognition=FakeRealRecognition([success_result("помощь")])
    )

    result = processor.process("распознай голос один раз")

    assert processor.has_pending_voice_command() is False
    assert result["intent"] == "assistant.help"
    assert "Выполняю: помощь" in result["response"]
    assert "без дополнительного подтверждения" in result["response"]


def test_safe_vosk_status_auto_executes_without_pending_confirmation():
    processor = CommandProcessor(
        one_shot_vosk_real_recognition=FakeRealRecognition(
            [success_result("статус vosk")]
        )
    )

    result = processor.process("распознай голос один раз")

    assert processor.has_pending_voice_command() is False
    assert result["intent"] == "speech.backend.vosk.recognition.status"
    assert "Выполняю: статус vosk" in result["response"]


def test_unknown_recognition_creates_pending_command_and_asks_confirmation():
    processor = CommandProcessor(
        one_shot_vosk_real_recognition=FakeRealRecognition(
            [success_result("расскажи что-нибудь")]
        )
    )

    result = processor.process("распознай голос один раз")

    assert processor.get_pending_voice_command() == "расскажи что-нибудь"
    assert result["intent"] == "speech.backend.vosk.one_shot_real_recognition"
    assert "Я распознал: \"расскажи что-нибудь\"." in result["response"]
    assert "Выполнить эту команду? Подтвердите: да / нет." in result["response"]
    assert "без дополнительного подтверждения" not in result["response"]


def test_positive_confirmation_executes_pending_command_through_processor():
    processor = CommandProcessor(
        one_shot_vosk_real_recognition=FakeRealRecognition([success_result()])
    )
    processor.process("распознай голос один раз")

    result = processor.process("да")

    assert processor.has_pending_voice_command() is False
    assert result["intent"] == "system.version"
    assert (
        "Подтверждение получено. Выполняю распознанную команду: версия"
        in result["response"]
    )
    assert "0.2" in result["response"]


def test_positive_aliases_execute_pending_command():
    for alias in ("подтверждаю", "выполнить", "выполни", "ок", "ага", "yes"):
        processor = CommandProcessor(
            one_shot_vosk_real_recognition=FakeRealRecognition([success_result()])
        )
        processor.process("распознай голос один раз")

        result = processor.process(alias)

        assert processor.has_pending_voice_command() is False
        assert result["intent"] == "system.version"


def test_negative_aliases_cancel_pending_command():
    for alias in ("нет", "отмена", "отмени", "не надо", "no"):
        processor = CommandProcessor(
            one_shot_vosk_real_recognition=FakeRealRecognition([success_result()])
        )
        processor.process("распознай голос один раз")

        result = processor.process(alias)

        assert processor.has_pending_voice_command() is False
        assert result["intent"] == "voice.pending_command.cancelled"
        assert result["response"] == "Хорошо, распознанная голосовая команда отменена."


def test_unrelated_input_keeps_pending_command_and_asks_yes_no():
    processor = CommandProcessor(
        one_shot_vosk_real_recognition=FakeRealRecognition([success_result()])
    )
    processor.process("распознай голос один раз")

    result = processor.process("статус системы")

    assert processor.get_pending_voice_command() == "версия"
    assert result["intent"] == "voice.pending_command.awaiting_confirmation"
    assert (
        "Ожидаю подтверждение для распознанной команды: версия. Ответьте: да / нет."
        == result["response"]
    )


def test_pending_status_command_shows_pending_text():
    processor = CommandProcessor(
        one_shot_vosk_real_recognition=FakeRealRecognition([success_result()])
    )
    processor.process("распознай голос один раз")

    result = processor.process("ожидающая голосовая команда")

    assert result["intent"] == "voice.pending_command.status"
    assert (
        result["response"]
        == "Ожидает подтверждения голосовая команда: версия. Ответьте: да / нет."
    )


def test_pending_status_command_when_no_pending_text():
    result = CommandProcessor().process("pending voice command")

    assert result["intent"] == "voice.pending_command.status"
    assert result["response"] == "Нет голосовой команды, ожидающей подтверждения."


def test_cancel_command_clears_pending_text():
    processor = CommandProcessor(
        one_shot_vosk_real_recognition=FakeRealRecognition([success_result()])
    )
    processor.process("распознай голос один раз")

    result = processor.process("сбросить голосовую команду")

    assert processor.has_pending_voice_command() is False
    assert result["intent"] == "voice.pending_command.cleared"
    assert result["response"] == "Ожидающая голосовая команда очищена."


def test_new_one_shot_recognition_replaces_old_pending_command():
    processor = CommandProcessor(
        one_shot_vosk_real_recognition=FakeRealRecognition(
            [success_result("версия"), success_result("покажи профиль")]
        )
    )

    processor.process("распознай голос один раз")
    processor.process("распознай голос один раз")

    assert processor.get_pending_voice_command() == "покажи профиль"


def test_allowlisted_command_does_not_bypass_normal_command_processor():
    class TrackingCommandProcessor(CommandProcessor):
        def __init__(self):
            super().__init__(
                one_shot_vosk_real_recognition=FakeRealRecognition(
                    [success_result("статус системы")]
                )
            )
            self.processed_commands = []

        def process(self, command_text):
            self.processed_commands.append(command_text)
            return super().process(command_text)

    processor = TrackingCommandProcessor()

    result = processor.process("распознай голос один раз")

    assert result["intent"] == "system.status"
    assert processor.processed_commands == [
        "распознай голос один раз",
        "статус системы",
    ]
    assert processor.has_pending_voice_command() is False


def test_empty_recognition_does_not_create_pending_command():
    processor = CommandProcessor(
        one_shot_vosk_real_recognition=FakeRealRecognition([empty_result()])
    )

    result = processor.process("распознай голос один раз")

    assert processor.has_pending_voice_command() is False
    assert "речь не распознана" in result["response"]


def test_failed_recognition_does_not_create_pending_command():
    processor = CommandProcessor(
        one_shot_vosk_real_recognition=FakeRealRecognition([blocked_result()])
    )

    result = processor.process("распознай голос один раз")

    assert processor.has_pending_voice_command() is False
    assert "Реальное распознавание Vosk заблокировано." in result["response"]


def test_confirmed_risky_command_still_uses_safety_router():
    processor = CommandProcessor(
        one_shot_vosk_real_recognition=FakeRealRecognition(
            [success_result("отправь письмо")]
        )
    )
    processor.process("распознай голос один раз")

    result = processor.process("да")

    assert processor.has_pending_voice_command() is False
    assert result["intent"] == "action.confirmation_required"
    assert result["requires_confirmation"] is True
    assert "Подтверждение получено" in result["response"]


def test_confirmation_flow_does_not_recurse_forever_for_confirmation_word():
    processor = CommandProcessor(
        one_shot_vosk_real_recognition=FakeRealRecognition([success_result("да")])
    )
    processor.process("распознай голос один раз")

    result = processor.process("да")

    assert processor.has_pending_voice_command() is False
    assert result["intent"] != "voice.pending_command.awaiting_confirmation"
