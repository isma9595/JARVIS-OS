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
    app_commands = [
        command
        for command in registry.list_by_category(CommandCategory.APP)
        if command.command_id.endswith("_future")
    ]

    assert app_commands
    assert all(command.risk_level == CommandRiskLevel.FUTURE for command in app_commands)
    assert all(command.app_ready is False for command in app_commands)


def test_app_service_commands_registered():
    registry = CommandRegistry()

    command_ids = {command.command_id for command in registry.list_by_category(CommandCategory.APP)}

    assert "app_service.status" in command_ids
    assert "app_service.capabilities" in command_ids
    assert "app_service.preview" in command_ids
    assert "app_service.commands" in command_ids


def test_app_service_preview_command_is_not_voice_auto_allowed():
    registry = CommandRegistry()
    command = registry.find_by_alias("app preview: <text>")

    assert command is not None
    assert command.command_id == "app_service.preview"
    assert command.voice_auto_allowed is False
    assert command.app_ready is True
    assert command.requires_network is False


def test_app_service_status_capabilities_and_list_are_read_only_and_app_ready():
    registry = CommandRegistry()

    for alias in (
        "статус app service",
        "app service capabilities",
        "app service commands",
    ):
        command = registry.find_by_alias(alias)

        assert command is not None
        assert command.read_only is True
        assert command.risk_level == CommandRiskLevel.READ_ONLY
        assert command.voice_auto_allowed is True
        assert command.app_ready is True
        assert command.requires_network is False


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


def test_desktop_shell_commands_registered():
    registry = CommandRegistry()
    command_ids = {command.command_id for command in registry.list_by_category(CommandCategory.APP)}

    assert "desktop_shell.status" in command_ids
    assert "desktop_shell.capabilities" in command_ids


def test_desktop_shell_status_capabilities_are_read_only_app_ready():
    registry = CommandRegistry()

    for alias in (
        "статус desktop app",
        "статус jarvis desktop",
        "статус desktop shell",
        "статус app shell",
        "статус окна jarvis",
        "возможности desktop app",
        "возможности desktop shell",
        "возможности окна jarvis",
        "desktop app capabilities",
    ):
        command = registry.find_by_alias(alias)

        assert command is not None
        assert command.category == CommandCategory.APP
        assert command.read_only is True
        assert command.risk_level == CommandRiskLevel.READ_ONLY
        assert command.app_ready is True
        assert command.requires_network is False


def test_desktop_shell_status_capability_voice_auto_allowed_yes():
    registry = CommandRegistry()

    for alias in ("статус desktop app", "desktop app capabilities"):
        command = registry.find_by_alias(alias)

        assert command is not None
        assert command.voice_auto_allowed is True


def test_no_gui_launch_command_is_voice_auto_allowed():
    registry = CommandRegistry()

    for command in registry.commands:
        aliases = " ".join(command.aliases).lower()
        if "run_desktop.py" in aliases or "launch" in command.command_id:
            assert command.voice_auto_allowed is False


def test_secure_key_commands_registered():
    registry = CommandRegistry()
    command_ids = {
        command.command_id
        for command in registry.list_by_category(CommandCategory.SECURE_KEYS)
    }

    assert "secure_keys.status" in command_ids
    assert "secure_keys.list" in command_ids
    assert "secure_keys.help" in command_ids
    assert "secure_keys.import_from_env" in command_ids
    assert "secure_keys.delete" in command_ids


def test_secure_key_read_only_commands_are_app_ready_and_voice_allowed():
    registry = CommandRegistry()

    for alias in (
        "статус secure keys",
        "статус api ключей",
        "список api ключей",
        "безопасность api ключей",
    ):
        command = registry.find_by_alias(alias)

        assert command is not None
        assert command.category == CommandCategory.SECURE_KEYS
        assert command.read_only is True
        assert command.risk_level == CommandRiskLevel.READ_ONLY
        assert command.voice_auto_allowed is True
        assert command.app_ready is True
        assert command.requires_network is False


def test_secure_key_import_and_delete_are_sensitive_not_voice_allowed_no_network():
    registry = CommandRegistry()

    for alias in ("импортировать groq ключ из env", "удалить groq ключ"):
        command = registry.find_by_alias(alias)

        assert command is not None
        assert command.category == CommandCategory.SECURE_KEYS
        assert command.risk_level == CommandRiskLevel.SENSITIVE
        assert command.read_only is False
        assert command.voice_auto_allowed is False
        assert command.requires_confirmation is True
        assert command.requires_network is False
        assert command.requires_ai_key is False
        assert command.app_ready is True


def test_no_raw_key_command_exists():
    registry = CommandRegistry()
    raw_markers = ("<key>", "<api_key>", "<secret>", "ключ: <text>", "api key: <text>")

    for command in registry.commands:
        alias_text = " ".join(command.aliases).lower()
        assert all(marker not in alias_text for marker in raw_markers)


def test_contract_commands_registered():
    registry = CommandRegistry()
    command_ids = {command.command_id for command in registry.list_by_category(CommandCategory.APP)}

    assert "app_contracts.status" in command_ids
    assert "app_contracts.manifest" in command_ids
    assert "app_contracts.status_cards" in command_ids
    assert "app_contracts.command_cards" in command_ids


def test_contract_status_manifest_and_cards_are_read_only_app_ready_and_voice_allowed():
    registry = CommandRegistry()

    for alias in (
        "статус app contracts",
        "app contracts manifest",
        "app status cards",
        "app command cards",
    ):
        command = registry.find_by_alias(alias)

        assert command is not None
        assert command.category == CommandCategory.APP
        assert command.read_only is True
        assert command.app_ready is True
        assert command.voice_auto_allowed is True
        assert command.requires_network is False


def test_contract_commands_do_not_require_network():
    registry = CommandRegistry()
    contract_commands = [
        command
        for command in registry.commands
        if command.command_id.startswith("app_contracts.")
    ]

    assert contract_commands
    assert all(command.requires_network is False for command in contract_commands)
