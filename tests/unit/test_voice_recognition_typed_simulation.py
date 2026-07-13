from core.command_processor import CommandProcessor


def test_empty_simulation_text_returns_helpful_message():
    processor = CommandProcessor()

    result = processor.process("симулируй распознавание:")

    assert result["intent"] == "voice.recognition.typed_simulation.empty"
    assert result["response"] == "Укажите текст для симуляции распознавания."
    assert processor.voice_command_history.count() == 0


def test_safe_allowlisted_simulation_auto_executes_read_only_command():
    processor = CommandProcessor()

    result = processor.process("симулируй распознавание: статус системы")

    assert processor.has_pending_voice_command() is False
    assert result["intent"] == "system.status"
    assert result["safe_voice_command_allowed"] is True
    assert result["recognized_voice_command"] == "статус системы"
    assert result["canonical_voice_command"] == "статус системы"
    assert result["voice_recognition_source"] == "typed_simulation"
    assert "Симуляция распознавания завершена." in result["response"]
    assert 'Я распознал: "статус системы".' in result["response"]
    assert "Команда входит в безопасный read-only список. Выполняю." in result["response"]
    assert "Активных сервисов" in result["response"]

    entry = processor.voice_command_history.last_entry()
    assert entry.source == "typed_simulation"
    assert entry.status == "allowlisted_executed"


def test_unknown_or_risky_simulation_creates_pending_confirmation():
    processor = CommandProcessor()

    result = processor.process("симулируй распознавание: открой браузер")

    assert result["intent"] == "voice.recognition.typed_simulation"
    assert processor.get_pending_voice_command() == "открой браузер"
    assert "Симуляция распознавания завершена." in result["response"]
    assert 'Я распознал: "открой браузер".' in result["response"]
    assert "Выполнить эту команду? Подтвердите: да / нет." in result["response"]
    assert "Безопасность: команда не выполнена автоматически." in result["response"]

    entry = processor.voice_command_history.last_entry()
    assert entry.source == "typed_simulation"
    assert entry.status == "pending_confirmation"


def test_pending_no_cancels_simulated_command():
    processor = CommandProcessor()
    processor.process("симулируй распознавание: открой браузер")

    result = processor.process("нет")

    assert result["intent"] == "voice.pending_command.cancelled"
    assert processor.has_pending_voice_command() is False
    assert processor.voice_command_history.last_entry().status == "canceled"


def test_pending_yes_routes_through_action_router_without_bypass():
    processor = CommandProcessor()
    processor.process("симулируй распознавание: открой браузер")

    result = processor.process("да")

    assert result["intent"] == "action.confirmation_required"
    assert result["requires_confirmation"] is True
    assert processor.has_pending_voice_command() is False
    assert "Подтверждение получено" in result["response"]
    assert processor.voice_command_history.last_entry().status == (
        "confirmed_requires_additional_safety_confirmation"
    )


def test_session_correction_applies_to_simulated_recognition():
    processor = CommandProcessor()
    processor.process("я сказал не статуя система, а статус системы")

    result = processor.process("симулируй распознавание: статуя система")

    assert result["intent"] == "system.status"
    assert result["recognized_voice_command"] == "статуя система"
    assert result["corrected_voice_command"] == "статус системы"
    assert result["canonical_voice_command"] == "статус системы"
    assert 'Применено исправление текущей сессии: "статус системы".' in result["response"]
    assert processor.has_pending_voice_command() is False
    assert processor.voice_command_history.last_entry().source == "typed_simulation"


def test_correction_to_risky_simulated_command_still_requires_confirmation():
    processor = CommandProcessor()
    processor.process("исправь распознавание: браузер -> открой браузер")

    result = processor.process("симулируй распознавание: браузер")

    assert result["intent"] == "voice.recognition.typed_simulation"
    assert processor.get_pending_voice_command() == "открой браузер"
    assert 'Я распознал: "браузер".' in result["response"]
    assert 'Применено исправление текущей сессии: "открой браузер".' in result["response"]
    assert "Безопасность: команда не выполнена автоматически." in result["response"]
    assert "Активных сервисов" not in result["response"]


def test_history_and_last_recognition_show_typed_simulation_source():
    processor = CommandProcessor()
    processor.process("симулируй распознавание: статус системы")

    last = processor.process("последнее распознавание")
    history = processor.process("история голосовых команд")

    assert last["intent"] == "voice.history.last"
    assert "Источник: текстовая симуляция" in last["response"]
    assert history["intent"] == "voice.history.list"
    assert "источник: текстовая симуляция" in history["response"]


def test_diagnostics_work_while_simulated_pending_command_exists():
    processor = CommandProcessor()
    processor.process("симулируй распознавание: открой браузер")

    last = processor.process("последнее распознавание")
    history = processor.process("история голосовых команд")
    count = processor.process("сколько голосовых команд")

    assert last["intent"] == "voice.history.last"
    assert history["intent"] == "voice.history.list"
    assert count["intent"] == "voice.history.count"
    assert processor.get_pending_voice_command() == "открой браузер"


def test_simulation_does_not_use_microphone_vosk_model_cloud_or_audio_files():
    class ExplodingDependency:
        def __getattr__(self, name):
            raise AssertionError(f"typed simulation must not use {name}")

    processor = CommandProcessor(
        one_shot_vosk_real_recognition=ExplodingDependency(),
        vosk_runtime_loader=ExplodingDependency(),
        vosk_recognition_dry_run=ExplodingDependency(),
        audio_dependency_readiness_checker=ExplodingDependency(),
    )
    processor.voice_input_manager = ExplodingDependency()

    result = processor.process("симулируй распознавание: статус системы")

    assert result["intent"] == "system.status"
    entry = processor.voice_command_history.last_entry()
    assert entry.source == "typed_simulation"
    assert not hasattr(entry, "audio")
    assert not hasattr(entry, "audio_path")
    assert not hasattr(entry, "audio_bytes")
