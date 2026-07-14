import os

from ai import AIProviderCapability, AIRequest
from ai.providers import DryRunAIProvider


def test_provider_info():
    info = DryRunAIProvider().get_info()

    assert info.name == "dry_run"
    assert info.model_name == "jarvis-dry-run-v0"
    assert info.safety_level == "offline_deterministic"
    assert info.enabled is True
    assert "chat" in info.capabilities


def test_supports_safe_capabilities_only():
    provider = DryRunAIProvider()

    assert provider.supports(AIProviderCapability.CHAT) is True
    assert provider.supports(AIProviderCapability.SUMMARY) is True
    assert provider.supports(AIProviderCapability.CLASSIFICATION) is True
    assert provider.supports(AIProviderCapability.VISION) is False
    assert provider.supports(AIProviderCapability.TOOL_PLANNING) is False


def test_chat_returns_dry_run_message_and_preview():
    response = DryRunAIProvider().generate(AIRequest(prompt="Привет, кто ты?"))

    assert response.is_error is False
    assert "AI dry-run" in response.text
    assert "внешний AI-провайдер ещё не подключён" in response.text
    assert "Привет, кто ты?" in response.text


def test_summary_is_deterministic_and_trims():
    request = AIRequest(
        prompt="Первое предложение очень длинное для проверки. Второе не нужно.",
        task_type="summary",
        max_chars=24,
    )

    response = DryRunAIProvider().generate(request)

    assert response.text == "AI dry-run summary: Первое предложение оч..."


def test_classification_categories_are_deterministic():
    provider = DryRunAIProvider()

    assert provider.generate(AIRequest("python код", "classification")).text.endswith("code")
    assert provider.generate(AIRequest("письмо документ", "classification")).text.endswith(
        "writing"
    )
    assert provider.generate(AIRequest("статус проверка", "classification")).text.endswith(
        "diagnostic"
    )
    assert provider.generate(AIRequest("обычный вопрос", "classification")).text.endswith(
        "general"
    )


def test_unsupported_capability_returns_error():
    response = DryRunAIProvider().generate_for_capability(
        AIRequest(prompt="картинка"),
        AIProviderCapability.VISION,
    )

    assert response.is_error is True
    assert "Unsupported dry-run capability" in response.error_message


def test_no_network_or_api_key_dependency(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "should_not_be_read")
    monkeypatch.setenv("GROQ_API_KEY", "should_not_be_read")

    response = DryRunAIProvider().generate(AIRequest(prompt="привет"))

    assert response.is_error is False
    assert os.environ["OPENAI_API_KEY"] == "should_not_be_read"
    assert os.environ["GROQ_API_KEY"] == "should_not_be_read"
