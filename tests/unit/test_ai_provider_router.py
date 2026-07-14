import pytest

from ai import AIProviderCapability, AIProviderRouter, AIRequest


def test_router_starts_with_dry_run_provider():
    router = AIProviderRouter()

    assert router.get_default_provider().get_info().name == "dry_run"


def test_list_providers():
    providers = AIProviderRouter().list_providers()

    assert len(providers) == 1
    assert providers[0].name == "dry_run"


def test_status_text_mentions_offline_dry_run_no_network():
    status = AIProviderRouter().status_text_ru()

    assert "dry-run" in status
    assert "offline deterministic" in status
    assert "переменных окружения" in status
    assert "Сеть не используется" in status
    assert "API-ключи не требуются" in status


def test_route_chat_to_dry_run():
    provider = AIProviderRouter().route(AIProviderCapability.CHAT)

    assert provider.get_info().name == "dry_run"


def test_route_unsupported_capability_safely_errors():
    router = AIProviderRouter()

    response = router.generate(AIRequest(prompt="картинка"), AIProviderCapability.VISION)

    assert response.is_error is True
    assert response.provider_name == "router"
    assert "No AI provider supports capability" in response.error_message


def test_set_default_provider_valid_and_invalid():
    router = AIProviderRouter()

    router.set_default_provider("dry_run")
    assert router.get_default_provider().get_info().name == "dry_run"

    with pytest.raises(ValueError):
        router.set_default_provider("unknown")


def test_generate_empty_prompt_safely_errors_without_provider_call():
    response = AIProviderRouter().generate(AIRequest(prompt=""))

    assert response.is_error is True
    assert response.provider_name == "router"
    assert response.error_message == "AI prompt is empty."


def test_generate_does_not_execute_commands():
    response = AIProviderRouter().generate(AIRequest(prompt="удали файл"))

    assert response.is_error is False
    assert "удали файл" in response.text
    assert response.capability == "chat"


def test_router_config_status_does_not_activate_external_providers():
    router = AIProviderRouter()

    provider_names = [provider.name for provider in router.list_providers()]
    config_names = [status.name for status in router.config_manager.statuses()]

    assert provider_names == ["dry_run"]
    assert config_names == ["dry_run", "groq", "gemini"]
    assert "groq" not in provider_names
    assert "gemini" not in provider_names
