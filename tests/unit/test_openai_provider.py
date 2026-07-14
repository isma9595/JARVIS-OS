import json
import socket
import urllib.error

from ai import AIProviderCapability, AIProviderConfig, AIRequest, OpenAIProvider


class FakeHTTPClient:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def post_json(self, url, headers, payload, timeout):
        self.calls.append(
            {
                "url": url,
                "headers": dict(headers),
                "payload": dict(payload),
                "timeout": timeout,
            }
        )
        if self.error is not None:
            raise self.error
        return self.response


def enabled_config():
    return AIProviderConfig(
        name="openai",
        provider_type="openai",
        enabled=True,
        default_model="openai-default",
        api_key_env_var="OPENAI_API_KEY",
    )


def disabled_config():
    return AIProviderConfig(
        name="openai",
        provider_type="openai",
        enabled=False,
        default_model="openai-default",
        api_key_env_var="OPENAI_API_KEY",
    )


def test_provider_info_includes_openai():
    info = OpenAIProvider(config=disabled_config()).get_info()

    assert info.name == "openai"
    assert info.model_name == "openai-default"
    assert info.enabled is False
    assert info.safety_level == "external_api"


def test_supports_safe_text_capabilities_only():
    provider = OpenAIProvider(config=disabled_config())

    assert provider.supports(AIProviderCapability.CHAT) is True
    assert provider.supports(AIProviderCapability.SUMMARY) is True
    assert provider.supports(AIProviderCapability.CLASSIFICATION) is True
    assert provider.supports(AIProviderCapability.VISION) is False
    assert provider.supports(AIProviderCapability.TOOL_PLANNING) is False


def test_disabled_provider_returns_safe_error_without_calling_client():
    client = FakeHTTPClient(response='{"output_text":"unused"}')
    response = OpenAIProvider(
        config=disabled_config(),
        http_client=client,
        allow_network=True,
        environ={"OPENAI_API_KEY": "fake-key"},
    ).generate(AIRequest(prompt="hello"))

    assert response.is_error is True
    assert response.text == "OpenAI provider is disabled."
    assert client.calls == []


def test_missing_key_returns_safe_error_without_calling_client():
    client = FakeHTTPClient(response='{"output_text":"unused"}')
    response = OpenAIProvider(
        config=enabled_config(),
        http_client=client,
        allow_network=True,
        environ={},
    ).generate(AIRequest(prompt="hello"))

    assert response.is_error is True
    assert "missing" in response.text.lower()
    assert "OPENAI_API_KEY" in response.text
    assert client.calls == []


def test_network_disabled_returns_safe_error_even_with_fake_key():
    client = FakeHTTPClient(response='{"output_text":"unused"}')
    response = OpenAIProvider(
        config=enabled_config(),
        http_client=client,
        allow_network=False,
        environ={"OPENAI_API_KEY": "fake-key"},
    ).generate(AIRequest(prompt="hello"))

    assert response.is_error is True
    assert response.text == "OpenAI provider is configured but real network calls are disabled."
    assert client.calls == []


def test_enabled_fake_client_posts_responses_api_and_parses_output_text():
    secret = "fake-openai-key-that-must-not-leak"
    client = FakeHTTPClient(response=json.dumps({"output_text": "hello from fake"}))
    response = OpenAIProvider(
        config=enabled_config(),
        http_client=client,
        allow_network=True,
        environ={"OPENAI_API_KEY": secret},
    ).generate(AIRequest(prompt="hello"))

    assert response.is_error is False
    assert response.text == "hello from fake"
    assert client.calls[0]["url"] == "https://api.openai.com/v1/responses"
    assert client.calls[0]["headers"]["Authorization"] == f"Bearer {secret}"
    assert client.calls[0]["headers"]["Content-Type"] == "application/json"
    assert client.calls[0]["payload"] == {
        "model": "openai-default",
        "input": "hello",
    }
    assert secret not in response.text


def test_summary_and_classification_inputs_are_mapped():
    client = FakeHTTPClient(response=json.dumps({"output_text": "ok"}))
    provider = OpenAIProvider(
        config=enabled_config(),
        http_client=client,
        allow_network=True,
        environ={"OPENAI_API_KEY": "fake-key"},
    )

    provider.generate(AIRequest(prompt="текст", task_type="summary"))
    provider.generate(AIRequest(prompt="запрос", task_type="classification"))

    assert client.calls[0]["payload"]["input"] == "Кратко перескажи следующий текст:\n\nтекст"
    assert (
        client.calls[1]["payload"]["input"]
        == "Классифицируй запрос одной короткой категорией:\n\nзапрос"
    )


def test_parses_fallback_output_shape():
    client = FakeHTTPClient(
        response=json.dumps(
            {
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "fallback text"}],
                    }
                ]
            }
        )
    )
    response = OpenAIProvider(
        config=enabled_config(),
        http_client=client,
        allow_network=True,
        environ={"OPENAI_API_KEY": "fake-key"},
    ).generate(AIRequest(prompt="hello"))

    assert response.is_error is False
    assert response.text == "fallback text"


def test_http_error_returns_status_only():
    error = OSError("server failed with secret fake-key")
    error.status = 429
    response = OpenAIProvider(
        config=enabled_config(),
        http_client=FakeHTTPClient(error=error),
        allow_network=True,
        environ={"OPENAI_API_KEY": "fake-key"},
    ).generate(AIRequest(prompt="hello"))

    assert response.is_error is True
    assert response.text == "OpenAI HTTP error: status 429."
    assert "fake-key" not in response.text


def test_urllib_http_error_returns_status_only():
    error = urllib.error.HTTPError(
        url="https://api.openai.com/v1/responses",
        code=500,
        msg="server failed",
        hdrs=None,
        fp=None,
    )
    response = OpenAIProvider(
        config=enabled_config(),
        http_client=FakeHTTPClient(error=error),
        allow_network=True,
        environ={"OPENAI_API_KEY": "fake-key"},
    ).generate(AIRequest(prompt="hello"))

    assert response.is_error is True
    assert response.text == "OpenAI HTTP error: status 500."


def test_timeout_or_network_exception_returns_safe_error():
    for error in (TimeoutError("timeout fake-key"), socket.timeout("timeout fake-key")):
        response = OpenAIProvider(
            config=enabled_config(),
            http_client=FakeHTTPClient(error=error),
            allow_network=True,
            environ={"OPENAI_API_KEY": "fake-key"},
        ).generate(AIRequest(prompt="hello"))

        assert response.is_error is True
        assert "fake-key" not in response.text


def test_malformed_json_returns_safe_error():
    response = OpenAIProvider(
        config=enabled_config(),
        http_client=FakeHTTPClient(response="{not json"),
        allow_network=True,
        environ={"OPENAI_API_KEY": "fake-key"},
    ).generate(AIRequest(prompt="hello"))

    assert response.is_error is True
    assert response.text == "OpenAI response was not valid JSON."


def test_unparseable_response_returns_safe_error():
    response = OpenAIProvider(
        config=enabled_config(),
        http_client=FakeHTTPClient(response=json.dumps({"unexpected": "shape"})),
        allow_network=True,
        environ={"OPENAI_API_KEY": "fake-key"},
    ).generate(AIRequest(prompt="hello"))

    assert response.is_error is True
    assert response.text == "OpenAI response text could not be parsed safely."


def test_response_text_and_errors_never_contain_api_key_value():
    secret = "fake-openai-key-that-must-not-leak"
    client = FakeHTTPClient(error=OSError(f"boom {secret}"))
    response = OpenAIProvider(
        config=enabled_config(),
        http_client=client,
        allow_network=True,
        environ={"OPENAI_API_KEY": secret},
    ).generate(AIRequest(prompt="hello"))

    assert response.is_error is True
    assert secret not in response.text
    assert secret not in response.error_message
