from app import JarvisAppService
from core.command_processor import CommandProcessor
from core.command_registry import CommandCategory, CommandRegistry, CommandRiskLevel
from security import ApiKeyManager, MemorySecureKeyBackend, SecureKeyStore
from voice import SafeVoiceCommandAllowlist


SECRET = "dummy-test-runtime-secret"


def test_command_processor_runtime_commands_work_without_leaking_secrets():
    manager = ApiKeyManager(
        SecureKeyStore(MemorySecureKeyBackend()),
        environ={"GROQ_API_KEY": SECRET},
    )
    processor = CommandProcessor(api_key_manager=manager)

    for command in (
        "статус provider runtime",
        "статус runtime ключей ai",
        "provider runtime credentials",
    ):
        result = processor.process(command)
        assert result["intent"].startswith("ai.provider_runtime")
        assert "secure provider runtime: yes" in result["response"]
        assert "no secrets" in result["response"]
        assert "no network" in result["response"]
        assert "no provider call" in result["response"]
        assert SECRET not in result["response"]


def test_command_processor_runtime_provider_status_commands_work():
    processor = CommandProcessor()

    for command, provider in (
        ("статус runtime groq", "groq"),
        ("статус runtime openai", "openai"),
        ("статус runtime gemini", "gemini"),
        ("статус runtime gigachat", "gigachat"),
        ("статус runtime ollama", "ollama"),
    ):
        result = processor.process(command)
        assert result["intent"] == "ai.provider_runtime.provider_status"
        assert f"- provider: {provider}" in result["response"]
        assert "- no secrets" in result["response"]
        assert "- no network" in result["response"]


def test_app_service_runtime_text_methods_are_safe():
    service = JarvisAppService(command_processor=CommandProcessor())

    assert "secure provider runtime: yes" in service.provider_runtime_status_text_ru()
    assert "no secrets" in service.provider_runtime_credentials_text_ru()
    for provider in ("groq", "openai", "gemini", "gigachat", "ollama"):
        text = service.provider_runtime_provider_text_ru(provider)
        assert f"- provider: {provider}" in text
        assert "- no provider call" in text


def test_command_registry_provider_runtime_commands_are_read_only():
    registry = CommandRegistry()

    for alias in (
        "статус provider runtime",
        "provider runtime credentials",
        "статус runtime groq",
    ):
        command = registry.find_by_alias(alias)
        assert command is not None
        assert command.category == CommandCategory.PROVIDER_RUNTIME
        assert command.risk_level == CommandRiskLevel.READ_ONLY
        assert command.read_only is True
        assert command.app_ready is True
        assert command.voice_auto_allowed is True
        assert command.requires_network is False
        assert command.requires_ai_key is False


def test_voice_allowlist_runtime_status_allowed_but_real_requests_not_allowed():
    allowlist = SafeVoiceCommandAllowlist()

    for command in (
        "статус provider runtime",
        "provider runtime credentials",
        "статус runtime groq",
        "статус runtime openai",
        "статус runtime gemini",
        "статус runtime gigachat",
        "статус runtime ollama",
    ):
        assert allowlist.decide(command).allowed is True

    for command in (
        "groq реальный запрос: hello",
        "openai реальный запрос: hello",
        "импортировать groq ключ из env",
        "удалить groq ключ",
        "чат: что ты умеешь",
    ):
        assert allowlist.decide(command).allowed is False


def test_vertical_integration_reports_runtime_safety():
    report = JarvisAppService(command_processor=CommandProcessor()).vertical_integration_report()
    text = JarvisAppService(command_processor=CommandProcessor()).vertical_integration_report_text_ru()

    assert report.overall_passed is True
    assert report.network_used is False
    assert report.secrets_included is False
    assert report.providers_called is False
    assert any(check.check_id == "secure_provider_runtime_safe" for check in report.checks)
    assert "network used: no" in text
    assert "secrets included: no" in text
