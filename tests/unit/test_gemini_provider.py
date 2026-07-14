import json
import socket
import urllib.error

from ai import AIProviderCapability, AIProviderConfig, AIRequest, GeminiProvider


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
                "payload": payload,
                "timeout": timeout,
            }
        )
        if self.error is not None:
            raise self.error
        return self.response


def enabled_config():
    return AIProviderConfig(
        name="gemini",
        provider_type="gemini",
        enabled=True,
        default_model="gemini-2.5-flash-lite",
        api_key_env_var="GEMINI_API_KEY",
    )


def disabled_config():
    return AIProviderConfig(
        name="gemini",
        provider_type="gemini",
        enabled=False,
        default_model="gemini-2.5-flash-lite",
        api_key_env_var="GEMINI_API_KEY",
    )


def gemini_response(text="hello from fake"):
    return json.dumps({"candidates": [{"content": {"parts": [{"text": text}]}}]})


def test_provider_info_includes_gemini():
    info = GeminiProvider(config=disabled_config()).get_info()

    assert info.name == "gemini"
    assert info.model_name == "gemini-2.5-flash-lite"
    assert info.enabled is False
    assert info.safety_level == "external_api"


def test_supports_safe_text_capabilities_only():
    provider = GeminiProvider(config=disabled_config())

    assert provider.supports(AIProviderCapability.CHAT) is True
    assert provider.supports(AIProviderCapability.SUMMARY) is True
    assert provider.supports(AIProviderCapability.CLASSIFICATION) is True
    assert provider.supports(AIProviderCapability.VISION) is False
    assert provider.supports(AIProviderCapability.TOOL_PLANNING) is False


def test_disabled_provider_returns_safe_error_without_calling_client():
    client = FakeHTTPClient(response=gemini_response("unused"))
    response = GeminiProvider(
        config=disabled_config(),
        http_client=client,
        allow_network=True,
        environ={"GEMINI_API_KEY": "fake-key"},
    ).generate(AIRequest(prompt="hello"))

    assert response.is_error is True
    assert response.text == "Gemini provider is disabled."
    assert client.calls == []


def test_missing_key_returns_safe_error_without_calling_client():
    client = FakeHTTPClient(response=gemini_response("unused"))
    response = GeminiProvider(
        config=enabled_config(),
        http_client=client,
        allow_network=True,
        environ={},
    ).generate(AIRequest(prompt="hello"))

    assert response.is_error is True
    assert "missing" in response.text.lower()
    assert "GEMINI_API_KEY" in response.text
    assert client.calls == []


def test_network_disabled_returns_safe_error_even_with_fake_key():
    client = FakeHTTPClient(response=gemini_response("unused"))
    response = GeminiProvider(
        config=enabled_config(),
        http_client=client,
        allow_network=False,
        environ={"GEMINI_API_KEY": "fake-key"},
    ).generate(AIRequest(prompt="hello"))

    assert response.is_error is True
    assert response.text == "Gemini provider is configured but real network calls are disabled."
    assert client.calls == []


def test_enabled_fake_client_posts_generate_content_and_parses_text():
    secret = "fake-gemini-key-that-must-not-leak"
    client = FakeHTTPClient(response=gemini_response("hello from fake"))
    response = GeminiProvider(
        config=enabled_config(),
        http_client=client,
        allow_network=True,
        environ={"GEMINI_API_KEY": secret},
    ).generate(AIRequest(prompt="hello", metadata={"max_output_tokens": "128"}))

    assert response.is_error is False
    assert response.text == "hello from fake"
    assert client.calls[0]["url"].startswith(
        "https://generativelanguage.googleapis.com/v1beta/models/"
    )
    assert "gemini-2.5-flash-lite:generateContent" in client.calls[0]["url"]
    assert f"key={secret}" in client.calls[0]["url"]
    assert client.calls[0]["headers"] == {"Content-Type": "application/json"}
    assert client.calls[0]["payload"] == {
        "contents": [{"parts": [{"text": "hello"}]}],
        "generationConfig": {"maxOutputTokens": 128},
    }
    assert secret not in response.text


def test_summary_and_classification_prompts_are_mapped():
    client = FakeHTTPClient(response=gemini_response("ok"))
    provider = GeminiProvider(
        config=enabled_config(),
        http_client=client,
        allow_network=True,
        environ={"GEMINI_API_KEY": "fake-key"},
    )

    provider.generate(AIRequest(prompt="текст", task_type="summary"))
    provider.generate(AIRequest(prompt="запрос", task_type="classification"))

    assert client.calls[0]["payload"]["contents"][0]["parts"][0]["text"].startswith(
        "Кратко перескажи"
    )
    assert client.calls[1]["payload"]["contents"][0]["parts"][0]["text"].startswith(
        "Классифицируй"
    )


def test_malformed_or_missing_response_shape_safe_error():
    for payload in ({}, {"candidates": []}, {"candidates": [{"content": {"parts": []}}]}):
        response = GeminiProvider(
            config=enabled_config(),
            http_client=FakeHTTPClient(response=json.dumps(payload)),
            allow_network=True,
            environ={"GEMINI_API_KEY": "fake-key"},
        ).generate(AIRequest(prompt="hello"))

        assert response.is_error is True
        assert response.text == "Gemini response text could not be parsed safely."


def test_http_error_returns_status_only():
    error = OSError("server failed with secret fake-key")
    error.status = 429
    response = GeminiProvider(
        config=enabled_config(),
        http_client=FakeHTTPClient(error=error),
        allow_network=True,
        environ={"GEMINI_API_KEY": "fake-key"},
    ).generate(AIRequest(prompt="hello"))

    assert response.is_error is True
    assert response.text == "Gemini HTTP error: status 429."
    assert "fake-key" not in response.text


def test_urllib_http_error_returns_status_only():
    error = urllib.error.HTTPError(
        url="https://generativelanguage.googleapis.com/",
        code=500,
        msg="server failed",
        hdrs=None,
        fp=None,
    )
    response = GeminiProvider(
        config=enabled_config(),
        http_client=FakeHTTPClient(error=error),
        allow_network=True,
        environ={"GEMINI_API_KEY": "fake-key"},
    ).generate(AIRequest(prompt="hello"))

    assert response.is_error is True
    assert response.text == "Gemini HTTP error: status 500."


def test_timeout_or_network_exception_returns_safe_error():
    for error in (TimeoutError("timeout fake-key"), socket.timeout("timeout fake-key")):
        response = GeminiProvider(
            config=enabled_config(),
            http_client=FakeHTTPClient(error=error),
            allow_network=True,
            environ={"GEMINI_API_KEY": "fake-key"},
        ).generate(AIRequest(prompt="hello"))

        assert response.is_error is True
        assert "fake-key" not in response.text


def test_malformed_json_returns_safe_error():
    response = GeminiProvider(
        config=enabled_config(),
        http_client=FakeHTTPClient(response="{not json"),
        allow_network=True,
        environ={"GEMINI_API_KEY": "fake-key"},
    ).generate(AIRequest(prompt="hello"))

    assert response.is_error is True
    assert response.text == "Gemini response was not valid JSON."


def test_response_text_and_errors_never_contain_api_key_value():
    secret = "fake-gemini-key-that-must-not-leak"
    response = GeminiProvider(
        config=enabled_config(),
        http_client=FakeHTTPClient(error=OSError(f"boom {secret}")),
        allow_network=True,
        environ={"GEMINI_API_KEY": secret},
    ).generate(AIRequest(prompt="hello"))

    assert response.is_error is True
    assert secret not in response.text
    assert secret not in response.error_message
