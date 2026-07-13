from dialogue import AssistantResponseHistory, VoiceInteractionControls
from voice import VoiceCommandSessionHistory


def test_no_last_assistant_response():
    controls = VoiceInteractionControls(AssistantResponseHistory())

    assert controls.get_last_assistant_response() is None


def test_returns_last_assistant_response():
    history = AssistantResponseHistory()
    history.add_response("Первый ответ.")
    history.add_response("Второй ответ.")

    controls = VoiceInteractionControls(history)

    assert controls.get_last_assistant_response() == "Второй ответ."


def test_shortens_long_response_safely():
    history = AssistantResponseHistory()
    history.add_response(
        "Первое короткое предложение. Второе предложение содержит детали, которые не нужны для короткого повтора."
    )

    controls = VoiceInteractionControls(history)

    assert controls.get_short_last_assistant_response(max_chars=60) == (
        "Первое короткое предложение."
    )


def test_simple_response_fallback_trims_when_sentence_is_too_long():
    history = AssistantResponseHistory()
    history.add_response("А" * 250)

    controls = VoiceInteractionControls(history)

    simplified = controls.get_simple_last_assistant_response(max_chars=40)
    assert simplified == ("А" * 37) + "..."


def test_no_voice_history_returns_safe_message():
    controls = VoiceInteractionControls(
        AssistantResponseHistory(),
        VoiceCommandSessionHistory(),
    )

    assert controls.get_last_voice_recognition_summary() is None
    assert (
        controls.format_last_voice_command_for_display()
        == "В этой сессии ещё нет распознанной голосовой команды."
    )


def test_formats_last_voice_recognition_summary():
    voice_history = VoiceCommandSessionHistory()
    voice_history.add_entry(
        recognized_text="статус системы",
        normalized_text="статус системы",
        canonical_command="статус системы",
        source="typed_simulation",
        status="allowlisted_executed",
    )
    controls = VoiceInteractionControls(AssistantResponseHistory(), voice_history)

    response = controls.format_last_voice_command_for_display()

    assert "Последняя распознанная голосовая команда:" in response
    assert "Распознано: статус системы" in response
    assert "Каноническая команда: статус системы" in response
    assert "Источник: текстовая симуляция" in response
    assert "Статус: выполнено как безопасная read-only команда" in response


def test_does_not_write_files_or_call_external_services():
    history = AssistantResponseHistory()
    voice_history = VoiceCommandSessionHistory()
    controls = VoiceInteractionControls(history, voice_history)

    controls.get_last_assistant_response()
    controls.get_short_last_assistant_response()
    controls.get_simple_last_assistant_response()
    controls.format_last_voice_command_for_display()

    assert not hasattr(controls, "path")
    assert not hasattr(controls, "file_path")
    assert not hasattr(controls, "client")
    assert not hasattr(controls, "provider")
