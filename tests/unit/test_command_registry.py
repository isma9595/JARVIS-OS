import pytest
import re

from core.command_registry import (
    CommandCategory,
    CommandMetadata,
    CommandRegistry,
    CommandRiskLevel,
)


def test_registry_builds_with_unique_ids_and_aliases():
    registry = CommandRegistry()

    command_ids = [command.command_id for command in registry.commands]
    aliases = [
        registry.normalize_alias(alias)
        for command in registry.commands
        for alias in command.aliases
    ]

    assert registry.commands
    assert len(command_ids) == len(set(command_ids))
    assert len(aliases) == len(set(aliases))
    assert registry.duplicate_aliases == ()


def test_aliases_normalize_and_duplicate_aliases_are_rejected():
    assert CommandRegistry.normalize_alias("  Статус   Ёлка! ") == "статус елка"

    command = CommandMetadata(
        command_id="one",
        title_ru="One",
        description_ru="One",
        category=CommandCategory.SYSTEM,
        aliases=("same",),
        risk_level=CommandRiskLevel.READ_ONLY,
        read_only=True,
        voice_auto_allowed=False,
        requires_confirmation=False,
        requires_network=False,
        requires_ai_key=False,
        requires_privacy_check=False,
        ui_visible=True,
        app_ready=True,
    )
    duplicate = CommandMetadata(
        command_id="two",
        title_ru="Two",
        description_ru="Two",
        category=CommandCategory.SYSTEM,
        aliases=("same",),
        risk_level=CommandRiskLevel.READ_ONLY,
        read_only=True,
        voice_auto_allowed=False,
        requires_confirmation=False,
        requires_network=False,
        requires_ai_key=False,
        requires_privacy_check=False,
        ui_visible=True,
        app_ready=True,
    )

    with pytest.raises(ValueError, match="Duplicate command aliases"):
        CommandRegistry((command, duplicate))


def test_status_categories_and_list_text_are_safe_and_cover_core_families():
    registry = CommandRegistry()

    status = registry.status_text_ru()
    categories = registry.categories_text_ru()
    listing = registry.list_text_ru()

    assert "- enabled: yes" in status
    assert "- network: not called" in status
    assert "- disk writes: none" in status
    assert "- secrets: not used" in status
    assert "- duplicate aliases: none" in status
    assert "ai" in listing
    assert "voice" in listing
    assert "ai_privacy" in listing
    assert "ai_fallback" in listing
    assert "app" in listing
    assert "Command registry categories" in categories
    assert "network: not called" in categories


def test_manifest_groups_each_category_header_once():
    registry = CommandRegistry()

    listing = registry.manifest_text_ru()

    for category in registry.categories():
        assert listing.count(f"[{category.value}]") == 1


def test_manifest_real_provider_request_titles_are_clean():
    registry = CommandRegistry()
    listing = registry.manifest_text_ru()
    real_request_lines = [
        line
        for line in listing.splitlines()
        if "| id=ai_provider." in line and ".real_request |" in line
    ]

    assert real_request_lines
    assert all(not line.removeprefix("- ").startswith("Статус") for line in real_request_lines)
    assert re.search(r"- OpenAI реальный запрос \| id=ai_provider\.openai\.real_request", listing)
    assert re.search(r"- Gemini реальный запрос \| id=ai_provider\.gemini\.real_request", listing)
    assert re.search(r"- Groq реальный запрос \| id=ai_provider\.groq\.real_request", listing)
    assert re.search(r"- GigaChat реальный запрос \| id=ai_provider\.gigachat\.real_request", listing)


def test_search_finds_ai_voice_ollama_and_fallback_commands():
    registry = CommandRegistry()

    assert any(command.category == CommandCategory.AI for command in registry.search("ai"))
    assert any(command.category == CommandCategory.VOICE for command in registry.search("голос"))
    assert any(command.category == CommandCategory.OLLAMA for command in registry.search("ollama"))
    assert any(command.category == CommandCategory.AI_FALLBACK for command in registry.search("fallback"))


def test_future_app_commands_are_future_and_not_app_ready():
    registry = CommandRegistry()
    app_commands = registry.list_by_category(CommandCategory.APP)

    assert app_commands
    assert all(command.risk_level == CommandRiskLevel.FUTURE for command in app_commands)
    assert all(command.app_ready is False for command in app_commands)


def test_risky_commands_are_not_voice_auto_allowed():
    registry = CommandRegistry()

    risky = [
        command
        for command in registry.commands
        if command.risk_level
        in {
            CommandRiskLevel.CONFIRMATION_REQUIRED,
            CommandRiskLevel.NETWORK_EXPLICIT,
            CommandRiskLevel.LOCAL_RUNTIME,
            CommandRiskLevel.SENSITIVE,
            CommandRiskLevel.DESTRUCTIVE_BLOCKED,
            CommandRiskLevel.FUTURE,
        }
    ]

    assert risky
    assert all(command.voice_auto_allowed is False for command in risky)


def test_real_provider_commands_require_network_privacy_and_key():
    registry = CommandRegistry()
    real_requests = [
        command
        for command in registry.commands
        if command.command_id.endswith(".real_request")
        and command.category == CommandCategory.AI_PROVIDER
    ]

    assert real_requests
    assert all(command.requires_network for command in real_requests)
    assert all(command.requires_ai_key for command in real_requests)
    assert all(command.requires_privacy_check for command in real_requests)
    assert all(command.voice_auto_allowed is False for command in real_requests)


def test_status_and_list_commands_do_not_require_network():
    registry = CommandRegistry()
    safe_commands = [
        command
        for command in registry.commands
        if command.risk_level == CommandRiskLevel.READ_ONLY
    ]

    assert safe_commands
    assert all(command.requires_network is False for command in safe_commands)


def test_search_text_redacts_secrets_and_does_not_execute():
    registry = CommandRegistry()
    secret = "sk-test-1234567890secret"

    text = registry.search_text_ru(f"fallback api key={secret}")

    assert secret not in text
    assert "[REDACTED]" in text
    assert "- network: not called" in text
    assert "- disk writes: none" in text
    assert "- execution: not performed" in text
