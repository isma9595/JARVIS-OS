import pytest

from ai import AIProviderCapability, AIProviderRouter, AIRequest


def test_router_starts_with_dry_run_provider():
    router = AIProviderRouter()

    assert router.get_default_provider().get_info().name == "dry_run"


def test_list_providers():
    providers = AIProviderRouter().list_providers()

    assert len(providers) == 3
    assert providers[0].name == "dry_run"
    assert providers[1].name == "gemini"
    assert providers[1].enabled is False
    assert providers[2].name == "openai"
    assert providers[2].enabled is False


def test_status_text_mentions_offline_dry_run_no_network():
    status = AIProviderRouter().status_text_ru()

    assert "dry-run" in status
    assert "offline deterministic" in status
    assert "переменных окружения" in status
    assert "Сеть не используется" in status
    assert "OpenAI" in status
    assert "Gemini" in status


def test_route_chat_to_dry_run():
    provider = AIProviderRouter().route(AIProviderCapability.CHAT)

    assert provider.get_info().name == "dry_run"


def test_openai_is_known_but_not_default():
    router = AIProviderRouter()

    assert router.get_default_provider().get_info().name == "dry_run"
    assert "openai" in [provider.name for provider in router.list_providers()]
    assert "gemini" in [provider.name for provider in router.list_providers()]


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

    assert provider_names == ["dry_run", "gemini", "openai"]
    assert config_names == ["dry_run", "groq", "gemini", "openai"]
    assert "groq" not in provider_names
    assert router.get_default_provider().get_info().name == "dry_run"


def test_generic_route_still_uses_dry_run_with_gemini_registered():
    router = AIProviderRouter()

    response = router.generate(AIRequest(prompt="hello"), AIProviderCapability.CHAT)

    assert response.provider_name == "dry_run"
    assert router.route(AIProviderCapability.CHAT).get_info().name == "dry_run"


def test_openai_disabled_or_network_disabled_does_not_call_network():
    class FailingHTTPClient:
        def post_json(self, url, headers, payload, timeout):
            raise AssertionError("network must not be called")

    from ai import AIProviderConfig
    from ai.providers.openai_provider import OpenAIProvider

    router = AIProviderRouter(
        providers=[
            OpenAIProvider(
                config=AIProviderConfig(
                    name="openai",
                    provider_type="openai",
                    enabled=True,
                    default_model="openai-default",
                    api_key_env_var="OPENAI_API_KEY",
                ),
                http_client=FailingHTTPClient(),
                allow_network=False,
                environ={"OPENAI_API_KEY": "fake-key"},
            )
        ]
    )

    response = router.generate_with_provider(
        "openai",
        AIRequest(prompt="привет"),
        AIProviderCapability.CHAT,
    )

    assert response.is_error is True
    assert "network calls are disabled" in response.text
