from core.command_processor import CommandProcessor


def test_voice_cycle_status_commands_return_summary():
    processor = CommandProcessor()

    result = processor.process("статус голосового цикла")

    assert result["intent"] == "voice.cycle.status"
    response = result["response"]
    assert "Vosk" in response
    assert "one-shot" in response
    assert "DRY_RUN" in response
    assert "локальный голос Windows" in response
    assert "ручной голосовой диалог" in response
    assert "mute / skip-next / stop controls" in response
    assert "постоянное прослушивание не включено" in response
    assert "облако не используется" in response
    assert "аудиофайлы не сохраняются" in response
    assert "рискованные команды требуют подтверждения" in response
    assert "не выполняется повторно автоматически" in response


def test_voice_cycle_status_aliases():
    processor = CommandProcessor()

    for command in (
        "голосовой цикл статус",
        "итог голосового цикла",
        "что умеет голос",
        "список голосовых возможностей",
    ):
        assert processor.process(command)["intent"] == "voice.cycle.status"


def test_voice_command_map_returns_grouped_index():
    processor = CommandProcessor()

    result = processor.process("карта голосовых команд")

    assert result["intent"] == "voice.cycle.command_map"
    response = result["response"]
    assert "Recognition:" in response
    assert "History:" in response
    assert "Output / TTS:" in response
    assert "Dialogue / repeat:" in response
    assert "Safety / mute:" in response
    assert "Diagnostics:" in response
    assert "симулируй распознавание: <текст>" in response
    assert "статус голосового цикла" in response


def test_typed_voice_simulation_allows_final_status_and_map():
    processor = CommandProcessor()

    status = processor.process("симулируй распознавание: статус голосового цикла")
    command_map = processor.process("симулируй распознавание: карта голосовых команд")

    assert status["intent"] == "voice.cycle.status"
    assert status["safe_voice_command_allowed"] is True
    assert status["canonical_voice_command"] == "статус голосового цикла"
    assert "Голосовой цикл JARVIS v0.2 стабилизирован" in status["response"]

    assert command_map["intent"] == "voice.cycle.command_map"
    assert command_map["safe_voice_command_allowed"] is True
    assert command_map["canonical_voice_command"] == "карта голосовых команд"
    assert "Карта голосовых команд JARVIS v0.2" in command_map["response"]


def test_help_mentions_voice_cycle_status_and_map_commands():
    processor = CommandProcessor()

    response = processor.process("помощь")["response"]

    assert "статус голосового цикла" in response
    assert "карта голосовых команд" in response
    assert "постоянное прослушивание" in response
    assert "Облако не используется" in response or "облако не используется" in response
    assert "аудиофайлы не сохраняются" in response
    assert "требуют подтверждения" in response
    assert "не выполняет команду повторно" in response or "не выполняется повторно" in response
