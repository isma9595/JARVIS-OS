import io
import json
import socket
import urllib.error

from ai import AIProviderCapability, AIProviderConfig, AIRequest, GroqProvider
from ai.providers.groq_provider import UrllibGroqHTTPClient


class FakeHTTPClient:
    def __init__(self, response=None, error=None, expected_key=None, expected_prompt=None):
        self.response = response
        self.error = error
        self.expected_key = expected_key
        self.expected_prompt = expected_prompt
        self.calls = []

    def post_json(self, url, headers, payload, timeout):
        if self.expected_key is not None:
            assert url == "https://api.groq.com/openai/v1/chat/completions"
            assert headers["Authorization"].startswith("Bearer ")
            assert headers["Authorization"] == f"Bearer {self.expected_key}"
            assert headers["Authorization"].count(self.expected_key) == 1
            assert headers["Content-Type"] == "application/json"
            assert headers["Accept"] == "application/json"
            assert headers["User-Agent"] == "JARVIS-OS/0.2"
            assert set(payload) == {"model", "messages", "max_tokens", "temperature"}
            assert payload["model"] == "llama-3.1-8b-instant"
            assert payload["messages"] == [
                {"role": "user", "content": self.expected_prompt}
            ]
            assert payload["max_tokens"] == 128
            assert payload["temperature"] == 0.2

            encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            decoded = json.loads(encoded.decode("utf-8"))
            assert decoded == payload
            if self.expected_prompt and any(ord(char) > 127 for char in self.expected_prompt):
                assert self.expected_prompt.encode("utf-8") in encoded

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
        name="groq",
        provider_type="groq",
        enabled=True,
        default_model="llama-3.1-8b-instant",
        api_key_env_var="GROQ_API_KEY",
    )


def disabled_config():
    return AIProviderConfig(
        name="groq",
        provider_type="groq",
        enabled=False,
        default_model="llama-3.1-8b-instant",
        api_key_env_var="GROQ_API_KEY",
    )


def groq_response(text="hello from fake"):
    return json.dumps(
        {"choices": [{"message": {"content": text}}]},
        ensure_ascii=False,
    )


def test_urllib_client_builds_exact_post_request_with_utf8_json(monkeypatch):
    captured = {}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": "Привет"}],
        "max_tokens": 16,
        "temperature": 0.2,
    }
    headers = {
        "Authorization": "Bearer fake-groq-key",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "JARVIS-OS/0.2",
    }

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"choices":[{"message":{"content":"ok"}}]}'

    def fake_urlopen(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    raw = UrllibGroqHTTPClient().post_json(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        payload=payload,
        timeout=30,
    )

    request = captured["request"]
    assert raw == '{"choices":[{"message":{"content":"ok"}}]}'
    assert captured["timeout"] == 30
    assert request.full_url == "https://api.groq.com/openai/v1/chat/completions"
    assert request.get_method() == "POST"
    assert request.get_header("Authorization") == "Bearer fake-groq-key"
    assert request.get_header("Content-type") == "application/json"
    assert request.get_header("Accept") == "application/json"
    assert request.get_header("User-agent") == "JARVIS-OS/0.2"
    assert isinstance(request.data, bytes)
    assert "Привет".encode("utf-8") in request.data
    assert json.loads(request.data.decode("utf-8")) == payload


def test_provider_info_includes_groq():
    info = GroqProvider(config=disabled_config()).get_info()

    assert info.name == "groq"
    assert info.model_name == "llama-3.1-8b-instant"
    assert info.enabled is False
    assert info.safety_level == "external_api"


def test_supports_safe_text_capabilities_only():
    provider = GroqProvider(config=disabled_config())

    assert provider.supports(AIProviderCapability.CHAT) is True
    assert provider.supports(AIProviderCapability.SUMMARY) is True
    assert provider.supports(AIProviderCapability.CLASSIFICATION) is True
    assert provider.supports(AIProviderCapability.VISION) is False
    assert provider.supports(AIProviderCapability.TOOL_PLANNING) is False


def test_disabled_provider_returns_safe_error_without_calling_client():
    client = FakeHTTPClient(response=groq_response("unused"))
    response = GroqProvider(
        config=disabled_config(),
        http_client=client,
        allow_network=True,
        environ={"GROQ_API_KEY": "fake-key"},
    ).generate(AIRequest(prompt="hello"))

    assert response.is_error is True
    assert response.text == "Groq provider is disabled."
    assert client.calls == []


def test_missing_key_returns_safe_error_without_calling_client():
    client = FakeHTTPClient(response=groq_response("unused"))
    response = GroqProvider(
        config=enabled_config(),
        http_client=client,
        allow_network=True,
        environ={},
    ).generate(AIRequest(prompt="hello"))

    assert response.is_error is True
    assert "missing" in response.text.lower()
    assert "GROQ_API_KEY" in response.text
    assert client.calls == []


def test_network_disabled_returns_safe_error_even_with_fake_key():
    client = FakeHTTPClient(response=groq_response("unused"))
    response = GroqProvider(
        config=enabled_config(),
        http_client=client,
        allow_network=False,
        environ={"GROQ_API_KEY": "fake-key"},
    ).generate(AIRequest(prompt="hello"))

    assert response.is_error is True
    assert response.text == "Groq provider is configured but real network calls are disabled."
    assert client.calls == []


def test_enabled_fake_client_posts_chat_completions_and_parses_cyrillic_text():
    secret = "fake-groq-key-that-must-not-leak"
    prompt = "Ответь одним словом: OK"
    answer = "подключение работает"
    client = FakeHTTPClient(
        response=groq_response(answer),
        expected_key=secret,
        expected_prompt=prompt,
    )
    response = GroqProvider(
        config=enabled_config(),
        http_client=client,
        allow_network=True,
        environ={"GROQ_API_KEY": secret},
    ).generate(AIRequest(prompt=prompt, metadata={"max_output_tokens": "128"}))

    assert response.is_error is False
    assert response.text == answer
    assert client.calls[0]["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert client.calls[0]["headers"]["Authorization"] == f"Bearer {secret}"
    assert client.calls[0]["headers"]["Authorization"].startswith("Bearer ")
    assert client.calls[0]["headers"]["Content-Type"] == "application/json"
    assert client.calls[0]["headers"]["Accept"] == "application/json"
    assert client.calls[0]["headers"]["User-Agent"] == "JARVIS-OS/0.2"
    assert set(client.calls[0]["payload"]) == {
        "model",
        "messages",
        "max_tokens",
        "temperature",
    }
    assert client.calls[0]["payload"]["model"] == "llama-3.1-8b-instant"
    assert client.calls[0]["payload"]["messages"] == [
        {"role": "user", "content": prompt}
    ]
    assert client.calls[0]["payload"]["max_tokens"] == 128
    assert client.calls[0]["payload"]["temperature"] == 0.2
    assert secret not in response.text
    assert secret not in (response.error_message or "")


def test_summary_and_classification_prompts_are_mapped():
    client = FakeHTTPClient(response=groq_response("ok"))
    provider = GroqProvider(
        config=enabled_config(),
        http_client=client,
        allow_network=True,
        environ={"GROQ_API_KEY": "fake-key"},
    )

    provider.generate(AIRequest(prompt="текст", task_type="summary"))
    provider.generate(AIRequest(prompt="запрос", task_type="classification"))

    assert client.calls[0]["payload"]["messages"][0]["content"].startswith(
        "Кратко перескажи"
    )
    assert client.calls[1]["payload"]["messages"][0]["content"].startswith(
        "Классифицируй"
    )


def test_malformed_or_missing_response_shape_safe_error():
    for payload in ({}, {"choices": []}, {"choices": [{"message": {}}]}):
        response = GroqProvider(
            config=enabled_config(),
            http_client=FakeHTTPClient(response=json.dumps(payload)),
            allow_network=True,
            environ={"GROQ_API_KEY": "fake-key"},
        ).generate(AIRequest(prompt="hello"))

        assert response.is_error is True
        assert response.text == "Groq response text could not be parsed safely."


def test_http_error_returns_status_only():
    error = OSError("server failed with secret fake-key")
    error.status = 500
    response = GroqProvider(
        config=enabled_config(),
        http_client=FakeHTTPClient(error=error),
        allow_network=True,
        environ={"GROQ_API_KEY": "fake-key"},
    ).generate(AIRequest(prompt="hello"))

    assert response.is_error is True
    assert response.text == "Groq HTTP error: status 500."
    assert "fake-key" not in response.text


def test_auth_and_rate_limit_errors_are_safe():
    for status, expected in (
        (401, "authentication/permission failed"),
        (403, "authentication/permission failed"),
        (429, "rate or quota limit"),
    ):
        error = urllib.error.HTTPError(
            url="https://api.groq.com/",
            code=status,
            msg="secret fake-key",
            hdrs=None,
            fp=None,
        )
        response = GroqProvider(
            config=enabled_config(),
            http_client=FakeHTTPClient(error=error),
            allow_network=True,
            environ={"GROQ_API_KEY": "fake-key"},
        ).generate(AIRequest(prompt="hello"))

        assert response.is_error is True
        assert expected in response.text
        assert "fake-key" not in response.text


def test_sanitized_403_error_body_includes_safe_groq_fields_without_key():
    secret = "fake-groq-key-that-must-not-leak"
    body = json.dumps(
        {
            "error": {
                "message": "model not permitted",
                "type": "permissions_error",
                "code": "model_not_allowed",
                "metadata": "x" * 1000,
            }
        }
    ).encode("utf-8")
    error = urllib.error.HTTPError(
        url="https://api.groq.com/openai/v1/chat/completions",
        code=403,
        msg="forbidden",
        hdrs=None,
        fp=io.BytesIO(body),
    )

    response = GroqProvider(
        config=enabled_config(),
        http_client=FakeHTTPClient(error=error),
        allow_network=True,
        environ={"GROQ_API_KEY": secret},
    ).generate(AIRequest(prompt="hello"))

    assert response.is_error is True
    assert "status 403" in response.text
    assert "model not permitted" in response.text
    assert "permissions_error" in response.text
    assert "model_not_allowed" in response.text
    assert "The key value was not printed." in response.text
    assert secret not in response.text
    assert secret not in response.error_message
    assert "metadata" not in response.text
    assert len(response.text) < 600


def test_timeout_or_network_exception_returns_safe_error():
    for error in (TimeoutError("timeout fake-key"), socket.timeout("timeout fake-key")):
        response = GroqProvider(
            config=enabled_config(),
            http_client=FakeHTTPClient(error=error),
            allow_network=True,
            environ={"GROQ_API_KEY": "fake-key"},
        ).generate(AIRequest(prompt="hello"))

        assert response.is_error is True
        assert "fake-key" not in response.text


def test_malformed_json_returns_safe_error():
    response = GroqProvider(
        config=enabled_config(),
        http_client=FakeHTTPClient(response="{not json"),
        allow_network=True,
        environ={"GROQ_API_KEY": "fake-key"},
    ).generate(AIRequest(prompt="hello"))

    assert response.is_error is True
    assert response.text == "Groq response was not valid JSON."


def test_response_text_and_errors_never_contain_api_key_value():
    secret = "fake-groq-key-that-must-not-leak"
    response = GroqProvider(
        config=enabled_config(),
        http_client=FakeHTTPClient(error=OSError(f"boom {secret}")),
        allow_network=True,
        environ={"GROQ_API_KEY": secret},
    ).generate(AIRequest(prompt="hello"))

    assert response.is_error is True
    assert secret not in response.text
    assert secret not in response.error_message
