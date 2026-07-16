from app.intent_resolver import (
    HybridIntentResolver,
    IntentConfidence,
    IntentKind,
    ResolutionStatus,
)
from core.command_registry import DEFAULT_COMMAND_REGISTRY


def resolver():
    return HybridIntentResolver(DEFAULT_COMMAND_REGISTRY)


def test_exact_command_resolves_high_confidence():
    result = resolver().resolve("статус системы", source="test")

    assert result.intent_kind == IntentKind.LOCAL_COMMAND
    assert result.resolution_status == ResolutionStatus.RESOLVED
    assert result.matched_command == "system.status"
    assert result.confidence == IntentConfidence.HIGH
    assert "registry_exact_or_alias" in result.reason_codes


def test_registered_alias_resolves_high_confidence():
    result = resolver().resolve("статус ии", source="test")

    assert result.matched_command == "ai.status"
    assert result.confidence == IntentConfidence.HIGH


def test_safe_voice_normalized_command_resolves():
    result = resolver().resolve(
        original_text="статус система",
        processing_text="статус системы",
        source="voice",
    )

    assert result.matched_command == "system.status"
    assert "safe_source_normalization" in result.reason_codes


def test_safe_semantic_read_only_phrase_resolves():
    result = resolver().resolve("покажи состояние системы", source="test")

    assert result.matched_command == "system.status"
    assert result.command_text == "статус системы"
    assert "semantic_system_status" in result.reason_codes


def test_ambiguous_status_phrase_requests_russian_clarification():
    result = resolver().resolve("покажи статус", source="test")

    assert result.intent_kind == IntentKind.AMBIGUOUS
    assert result.resolution_status == ResolutionStatus.REQUIRES_CLARIFICATION
    assert result.requires_clarification is True
    assert result.confidence == IntentConfidence.MEDIUM
    assert "Какой статус проверить" in result.clarification_question
    assert [option.label_ru for option in result.clarification_options] == [
        "системы",
        "AI",
        "микрофона",
        "AppService",
    ]


def test_clarification_options_are_serializable_with_cyrillic():
    data = resolver().resolve("какой статус", source="test").to_dict()

    assert data["requires_clarification"] is True
    assert data["clarification_options"][0]["label_ru"] == "системы"
    assert data["clarification_options"][0]["command_text"] == "статус системы"


def test_provider_prompt_remains_unchanged():
    prompt = "groq реальный запрос: сохрани URL https://example.test и email user@example.test"
    result = resolver().resolve(prompt, source="test")

    assert result.intent_kind == IntentKind.PROVIDER_REQUEST
    assert result.processing_text == prompt
    assert result.command_text == prompt


def test_quoted_text_file_paths_urls_and_emails_remain_unchanged():
    text = 'диалог: объясни "C:\\Temp\\file.txt" https://example.test user@example.test'
    result = resolver().resolve(text, source="test")

    assert result.processing_text == text
    assert result.command_text == text


def test_risky_misspelling_is_not_repaired():
    result = resolver().resolve("удали фал", source="test")

    assert result.intent_kind == IntentKind.UNSUPPORTED
    assert result.resolution_status == ResolutionStatus.UNSUPPORTED
    assert "risky_misspelling_not_repaired" in result.reason_codes


def test_vague_risky_phrase_is_not_executed_intent():
    result = resolver().resolve("удали это", source="test")

    assert result.intent_kind == IntentKind.UNSUPPORTED
    assert "vague_risky_action_not_executed" in result.reason_codes


def test_question_about_risky_action_is_ordinary_conversation():
    result = resolver().resolve("можно ли удалить файл", source="test")

    assert result.intent_kind == IntentKind.ORDINARY_CONVERSATION
    assert result.confidence == IntentConfidence.LOW
    assert "risky_action_question" in result.reason_codes


def test_resolver_has_no_runtime_execution_dependencies():
    instance = resolver()

    assert not hasattr(instance, "command_processor")
    assert not hasattr(instance, "action_router")
    assert not hasattr(instance, "provider")
