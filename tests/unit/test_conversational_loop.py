from app.conversational_loop import (
    ConversationIntent,
    SafeConversationalLoop,
    ConversationalRequest,
)


SECRET = "sk-test-1234567890secret"


def test_status_safe_no_network_providers_audio_or_secrets():
    status = SafeConversationalLoop().status()

    assert status["ready"] is True
    assert status["network_default"] is False
    assert status["providers_called"] is False
    assert status["audio_started"] is False
    assert status["microphone_started"] is False
    assert status["tts_started"] is False
    assert status["secrets_included"] is False
    assert status["response_executed_as_command"] is False


def test_classify_required_examples():
    loop = SafeConversationalLoop()

    assert loop.classify("привет") == ConversationIntent.SMALL_TALK
    assert loop.classify("что ты умеешь") == ConversationIntent.AI_QUESTION
    assert loop.classify("статус ai") == ConversationIntent.KNOWN_COMMAND
    assert loop.classify("напиши письмо мэру") == ConversationIntent.DRAFTING_TASK
    assert loop.classify("открой папку документы") == ConversationIntent.SIMPLE_ACTION
    assert (
        loop.classify("покажи закон о защите прав потребителей")
        == ConversationIntent.RESEARCH_TASK
    )
    assert (
        loop.classify("найди фильм на вечер и запусти")
        == ConversationIntent.COMPLEX_AGENT_TASK
    )
    assert loop.classify("удали все файлы") == ConversationIntent.RISKY_ACTION


def test_preview_never_executes_commands_or_calls_providers():
    result = SafeConversationalLoop().preview("статус ai")

    assert result.intent == "known_command"
    assert result.known_command is True
    assert result.command_id == "ai.status"
    assert result.command_executed is False
    assert result.providers_called is False
    assert result.network_used is False
    assert result.response_executed_as_command is False


def test_provider_fallback_and_consensus_text_do_not_call_network_by_default():
    loop = SafeConversationalLoop()

    for text in (
        "groq реальный запрос: привет",
        "fallback ai запрос: привет",
        "консенсус ai: привет",
    ):
        result = loop.handle(ConversationalRequest(text=text, source="test"))
        assert result.network_used is False
        assert result.providers_called is False
        assert result.command_executed is False
        assert result.requires_network is True


def test_result_text_ru_is_human_like_and_safe():
    loop = SafeConversationalLoop()
    text = loop.result_text_ru(loop.preview("привет"))

    assert "Исмаил" in text
    assert "Привет" in text
    assert SECRET not in text
    assert "providers called: no" in text
    assert "command executed: no" in text


def test_risky_request_blocked_or_confirmation_required():
    result = SafeConversationalLoop().preview("удали все файлы")

    assert result.intent == "risky_action"
    assert result.route == "risky_blocked_or_confirmation_required"
    assert result.safety_level == "risky_blocked"
    assert result.requires_confirmation is True
    assert result.command_executed is False
    assert "не удаляю" in result.answer_text_ru
