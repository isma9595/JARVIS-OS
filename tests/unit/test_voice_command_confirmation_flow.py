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
    entry = processor.voice_command_history.last_entry()
    assert entry.recognized_text == "статус системы"
    assert entry.canonical_command == "статус системы"
    assert entry.status == "allowlisted_executed"


def test_safe_status_system_misrecognition_auto_executes_canonical_command():
    processor = CommandProcessor(
        one_shot_vosk_real_recognition=FakeRealRecognition(
            [success_result("статуя система")]
        )
    )

    result = processor.process("распознай голос один раз")

    assert processor.has_pending_voice_command() is False
    assert result["intent"] == "system.status"
    assert "Я распознал безопасную голосовую команду: \"статуя система\"." in result["response"]
    assert "Выполняю: статус системы" in result["response"]
    assert result["safe_voice_command_allowed"] is True
    assert result["recognized_voice_command"] == "статуя система"
    assert result["canonical_voice_command"] == "статус системы"


def test_safe_status_system_case_alias_auto_executes_canonical_command():
    processor = CommandProcessor(
        one_shot_vosk_real_recognition=FakeRealRecognition(
            [success_result("статусе системы")]
        )
    )

    result = processor.process("распознай голос один раз")

    assert processor.has_pending_voice_command() is False
    assert result["intent"] == "system.status"
    assert "Выполняю: статус системы" in result["response"]
    assert result["canonical_voice_command"] == "статус системы"


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
    entry = processor.voice_command_history.last_entry()
    assert entry.recognized_text == "расскажи что-нибудь"
    assert entry.status == "pending_confirmation"


def test_risky_unknown_recognition_creates_pending_command_and_asks_confirmation():
    processor = CommandProcessor(
        one_shot_vosk_real_recognition=FakeRealRecognition(
            [success_result("открой браузер")]
        )
    )

    result = processor.process("распознай голос один раз")

    assert processor.get_pending_voice_command() == "открой браузер"
    assert result["intent"] == "speech.backend.vosk.one_shot_real_recognition"
    assert "Я распознал: \"открой браузер\"." in result["response"]
    assert "Выполнить эту команду? Подтвердите: да / нет." in result["response"]
    assert "без дополнительного подтверждения" not in result["response"]


def test_no_pending_command_remains_after_safe_alias_auto_execution():
    processor = CommandProcessor(
        one_shot_vosk_real_recognition=FakeRealRecognition(
            [success_result("статуя система")]
        )
    )

    processor.process("распознай голос один раз")

    assert processor.has_pending_voice_command() is False
    assert processor.get_pending_voice_command() is None


def test_positive_confirmation_executes_pending_command_through_processor():
    processor = CommandProcessor(
        one_shot_vosk_real_recognition=FakeRealRecognition([success_result()])
    )
    processor.process("распознай голос один раз")

    result = processor.process("да")

    assert processor.has_pending_voice_command() is False
    assert result["intent"] == "system.version"
    assert (
        "Подтверждение получено. Передаю распознанную команду в безопасную обработку: версия"
        in result["response"]
    )
    assert "0.2" in result["response"]
    assert processor.voice_command_history.last_entry().status == "confirmed_safe_processing"


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
        assert processor.voice_command_history.last_entry().status == "canceled"


def test_typed_yes_no_flow_still_works_for_non_allowlisted_commands():
    approve_processor = CommandProcessor(
        one_shot_vosk_real_recognition=FakeRealRecognition(
            [success_result("открой браузер")]
        )
    )
    approve_processor.process("распознай голос один раз")

    approved = approve_processor.process("да")

    assert approve_processor.has_pending_voice_command() is False
    assert approved["intent"] == "action.confirmation_required"
    assert approved["requires_confirmation"] is True
    assert (
        approve_processor.voice_command_history.last_entry().status
        == "confirmed_requires_additional_safety_confirmation"
    )
    history = approve_processor.process("история голосовых команд")
    assert "подтверждено и выполнено" not in history["response"]
    assert "требует дополнительного подтверждения безопасности" in history["response"]
    stray_yes = approve_processor.process("да")
    assert stray_yes["response"] == "Нет голосовой команды, ожидающей подтверждения."

    cancel_processor = CommandProcessor(
        one_shot_vosk_real_recognition=FakeRealRecognition(
            [success_result("открой браузер")]
        )
    )
    cancel_processor.process("распознай голос один раз")

    cancelled = cancel_processor.process("нет")

    assert cancel_processor.has_pending_voice_command() is False
    assert cancelled["intent"] == "voice.pending_command.cancelled"


def test_confirmation_words_without_pending_return_clear_response():
    processor = CommandProcessor()

    yes = processor.process("да")
    no = processor.process("нет")

    assert yes["intent"] == "voice.pending_command.none"
    assert yes["response"] == "Нет голосовой команды, ожидающей подтверждения."
    assert no["intent"] == "voice.pending_command.none"
    assert no["response"] == "Нет голосовой команды, ожидающей подтверждения."
    assert processor.has_pending_voice_command() is False
    assert processor.voice_command_history.count() == 0


def test_unrelated_input_keeps_pending_command_and_asks_yes_no():
    processor = CommandProcessor(
        one_shot_vosk_real_recognition=FakeRealRecognition([success_result()])
    )
    processor.process("распознай голос один раз")

    result = processor.process("статус системы")

    assert processor.get_pending_voice_command() == "версия"
    assert result["intent"] == "voice.pending_command.awaiting_confirmation"
    assert processor.voice_command_history.last_entry().status == "unknown_confirmation"
    assert (
        "Ожидаю подтверждение для распознанной команды: версия. Ответьте: да / нет."
        == result["response"]
    )


def test_exit_command_clears_pending_command_without_executing_it():
    processor = CommandProcessor(
        one_shot_vosk_real_recognition=FakeRealRecognition(
            [success_result("открой браузер")]
        )
    )
    processor.process("распознай голос один раз")

    result = processor.process("выход")

    assert result["intent"] == "system.exit"
    assert result["should_exit"] is True
    assert processor.has_pending_voice_command() is False
    assert processor.get_pending_voice_command() is None
    assert "Ожидаю подтверждение" not in result["response"]
    assert "браузер" not in result["response"]
    assert "Выполняю распознанную команду" not in result["response"]


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
    assert processor.voice_command_history.last_entry().status == "canceled"


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
    assert processor.voice_command_history.last_entry().status == "empty"


def test_failed_recognition_does_not_create_pending_command():
    processor = CommandProcessor(
        one_shot_vosk_real_recognition=FakeRealRecognition([blocked_result()])
    )

    result = processor.process("распознай голос один раз")

    assert processor.has_pending_voice_command() is False
    assert "Реальное распознавание Vosk заблокировано." in result["response"]
    assert processor.voice_command_history.last_entry().status == "blocked"


def test_correction_command_adds_session_correction():
    processor = CommandProcessor()

    result = processor.process("я сказал не статуя система, а статус системы")

    assert result["intent"] == "voice.recognition_correction.added"
    assert processor.voice_recognition_correction_manager.count() == 1
    entry = processor.voice_command_history.last_entry()
    assert entry.status == "correction_added"
    assert entry.recognized_text == "статуя система"
    assert entry.corrected_text == "статус системы"


def test_recognized_text_with_safe_correction_auto_executes_canonical_command():
    processor = CommandProcessor(
        one_shot_vosk_real_recognition=FakeRealRecognition(
            [success_result("статуя система")]
        )
    )
    processor.process("я сказал не статуя система, а статус системы")

    result = processor.process("распознай голос один раз")

    assert result["intent"] == "system.status"
    assert processor.has_pending_voice_command() is False
    assert result["recognized_voice_command"] == "статуя система"
    assert result["corrected_voice_command"] == "статус системы"
    assert result["canonical_voice_command"] == "статус системы"
    assert "Я распознал: \"статуя система\"." in result["response"]
    assert "Применено исправление текущей сессии: \"статус системы\"." in result["response"]
    assert "Активных сервисов" in result["response"]
    entry = processor.voice_command_history.last_entry()
    assert entry.status == "correction_applied"
    assert entry.recognized_text == "статуя система"
    assert entry.corrected_text == "статус системы"


def test_correction_to_risky_command_still_creates_pending_confirmation():
    processor = CommandProcessor(
        one_shot_vosk_real_recognition=FakeRealRecognition([success_result("браузер")])
    )
    processor.process("исправь распознавание: браузер -> открой браузер")

    result = processor.process("распознай голос один раз")

    assert result["intent"] == "speech.backend.vosk.one_shot_real_recognition"
    assert processor.get_pending_voice_command() == "открой браузер"
    assert "Я распознал: \"браузер\"." in result["response"]
    assert "Применено исправление текущей сессии: \"открой браузер\"." in result["response"]
    assert "Подтвердите: да / нет" in result["response"]
    assert "Активных сервисов" not in result["response"]
    assert processor.voice_command_history.last_entry().status == "pending_confirmation"


def test_corrections_do_not_bypass_action_router_after_confirmation():
    processor = CommandProcessor(
        one_shot_vosk_real_recognition=FakeRealRecognition([success_result("браузер")])
    )
    processor.process("исправь распознавание: браузер -> открой браузер")
    processor.process("распознай голос один раз")

    result = processor.process("да")

    assert result["intent"] == "action.confirmation_required"
    assert result["requires_confirmation"] is True
    assert processor.has_pending_voice_command() is False


def test_list_clear_count_corrections_commands_work():
    processor = CommandProcessor()
    processor.process("я сказал не статуя система, а статус системы")

    listed = processor.process("список голосовых исправлений")
    count = processor.process("сколько голосовых исправлений")
    cleared = processor.process("сбросить голосовые исправления")

    assert listed["intent"] == "voice.recognition_correction.list"
    assert "статуя система -> статус системы" in listed["response"]
    assert count["response"] == "Голосовых исправлений в текущей сессии: 1."
    assert cleared["intent"] == "voice.recognition_correction.cleared"
    assert processor.voice_recognition_correction_manager.count() == 0


def test_unknown_text_without_correction_keeps_existing_behavior():
    processor = CommandProcessor(
        one_shot_vosk_real_recognition=FakeRealRecognition(
            [success_result("расскажи что-нибудь")]
        )
    )

    result = processor.process("распознай голос один раз")

    assert result["intent"] == "speech.backend.vosk.one_shot_real_recognition"
    assert processor.get_pending_voice_command() == "расскажи что-нибудь"
    assert "Применено исправление" not in result["response"]


def test_corrections_are_session_only_and_do_not_touch_audio_or_cloud():
    processor = CommandProcessor()

    processor.process("я сказал не статуя система, а статус системы")
    correction = processor.voice_recognition_correction_manager.list_corrections()[0]

    assert not hasattr(processor.voice_recognition_correction_manager, "path")
    assert not hasattr(processor.voice_recognition_correction_manager, "file_path")
    assert not hasattr(correction, "audio")
    assert not hasattr(correction, "audio_path")
    assert not hasattr(correction, "audio_bytes")


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


def test_last_recognition_command_shows_last_history_entry():
    processor = CommandProcessor(
        one_shot_vosk_real_recognition=FakeRealRecognition(
            [success_result("статус системы")]
        )
    )
    processor.process("распознай голос один раз")

    result = processor.process("последнее распознавание")

    assert result["intent"] == "voice.history.last"
    assert "Последнее голосовое распознавание:" in result["response"]
    assert "Распознано: статус системы" in result["response"]
    assert "Каноническая команда: статус системы" in result["response"]


def test_voice_history_command_shows_recent_entries():
    processor = CommandProcessor(
        one_shot_vosk_real_recognition=FakeRealRecognition(
            [success_result("статус системы"), success_result("открой браузер")]
        )
    )
    processor.process("распознай голос один раз")
    processor.process("распознай голос один раз")

    result = processor.process("история голосовых команд")

    assert result["intent"] == "voice.history.list"
    assert "История голосовых команд за текущую сессию:" in result["response"]
    assert "статус системы -> статус системы" in result["response"]
    assert "открой браузер" in result["response"]
    assert "ожидает подтверждения" in result["response"]


def test_voice_history_clear_and_count_commands():
    processor = CommandProcessor(
        one_shot_vosk_real_recognition=FakeRealRecognition([success_result()])
    )
    processor.process("распознай голос один раз")

    count = processor.process("сколько голосовых команд")
    clear = processor.process("очистить историю голосовых команд")
    after_clear = processor.process("история голосовых команд")

    assert count["intent"] == "voice.history.count"
    assert count["response"] == "В этой сессии записано голосовых событий: 1."
    assert clear["intent"] == "voice.history.cleared"
    assert processor.voice_command_history.count() == 0
    assert after_clear["response"] == "В этой сессии ещё нет голосовых распознаваний."


def test_history_commands_do_not_bypass_pending_voice_safety():
    processor = CommandProcessor(
        one_shot_vosk_real_recognition=FakeRealRecognition(
            [success_result("открой браузер")]
        )
    )
    processor.process("распознай голос один раз")

    history = processor.process("история голосовых команд")

    assert history["intent"] == "voice.history.list"
    assert processor.has_pending_voice_command() is True
    assert processor.get_pending_voice_command() == "открой браузер"


def test_voice_diagnostic_commands_bypass_pending_confirmation_without_executing_pending():
    processor = CommandProcessor(
        one_shot_vosk_real_recognition=FakeRealRecognition(
            [success_result("открой браузер")]
        )
    )
    processor.process("распознай голос один раз")

    last = processor.process("последнее распознавание")
    history = processor.process("история голосовых команд")
    count = processor.process("сколько голосовых команд")
    typo_last = processor.process("последнее распознование")
    typo_history = processor.process("история распознования")

    assert last["intent"] == "voice.history.last"
    assert history["intent"] == "voice.history.list"
    assert count["intent"] == "voice.history.count"
    assert typo_last["intent"] == "voice.history.last"
    assert typo_history["intent"] == "voice.history.list"
    assert "Ожидаю подтверждение" not in last["response"]
    assert "Ожидаю подтверждение" not in history["response"]
    assert "Ожидаю подтверждение" not in count["response"]
    assert processor.has_pending_voice_command() is True
    assert processor.get_pending_voice_command() == "открой браузер"

    cancelled = processor.process("нет")

    assert cancelled["intent"] == "voice.pending_command.cancelled"
    assert processor.has_pending_voice_command() is False


def test_clear_voice_history_while_pending_keeps_pending_command():
    processor = CommandProcessor(
        one_shot_vosk_real_recognition=FakeRealRecognition(
            [success_result("открой браузер")]
        )
    )
    processor.process("распознай голос один раз")

    cleared = processor.process("очистить историю голосовых команд")

    assert cleared["intent"] == "voice.history.cleared"
    assert processor.voice_command_history.count() == 0
    assert processor.has_pending_voice_command() is True
    assert processor.get_pending_voice_command() == "открой браузер"

    cancelled = processor.process("нет")

    assert cancelled["intent"] == "voice.pending_command.cancelled"
    assert processor.has_pending_voice_command() is False
