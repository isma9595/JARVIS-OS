import io
import json
import socket
import urllib.error

from ai import AIProviderCapability, AIProviderConfig, AIRequest, GigaChatProvider


class FakeTokenManager:
    def __init__(self, token="fake-token", error=None):
        self.token = token
        self.error = error
        self.calls = 0

    def get_access_token(self):
        self.calls += 1
        from ai.gigachat_token_manager import GigaChatTokenResult

        if self.error:
            return GigaChatTokenResult(ok=False, error_message=self.error)
        return GigaChatTokenResult(ok=True, access_token=self.token, expires_at=9999999999)


class FakeHTTPClient:
    def __init__(self, response=None, error=None, expected_token=None, expected_prompt=None):
        self.response = response
        self.error = error
        self.expected_token = expected_token
        self.expected_prompt = expected_prompt
        self.calls = []

    def post_json(self, url, headers, payload, timeout):
        if self.expected_token is not None:
            assert url == "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
            assert headers["Authorization"] == f"Bearer {self.expected_token}"
            assert headers["Content-Type"] == "application/json"
            assert headers["Accept"] == "application/json"
            assert headers["User-Agent"] == "JARVIS-OS/0.2"
            assert set(payload) == {"model", "messages", "max_tokens", "temperature"}
            assert payload["model"] == "GigaChat"
            assert payload["messages"] == [{"role": "user", "content": self.expected_prompt}]
            assert payload["max_tokens"] == 128
            assert payload["temperature"] == 0.2
            encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            assert self.expected_prompt.encode("utf-8") in encoded
            assert json.loads(encoded.decode("utf-8")) == payload
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


def config(enabled=True):
    return AIProviderConfig(
        name="gigachat",
        provider_type="gigachat",
        enabled=enabled,
        default_model="GigaChat",
        api_key_env_var="GIGACHAT_AUTH_KEY",
    )


def response(text="fake answer"):
    return json.dumps({"choices": [{"message": {"content": text}}]}, ensure_ascii=False)


def test_info_and_capabilities():
    provider = GigaChatProvider(config=config(False))
    info = provider.get_info()

    assert info.name == "gigachat"
    assert info.enabled is False
    assert provider.supports(AIProviderCapability.CHAT)
    assert provider.supports(AIProviderCapability.SUMMARY)
    assert provider.supports(AIProviderCapability.CLASSIFICATION)
    assert not provider.supports(AIProviderCapability.VISION)
    assert not provider.supports(AIProviderCapability.TOOL_PLANNING)


def test_disabled_missing_key_and_network_disabled_block():
    client = FakeHTTPClient(response=response())

    assert GigaChatProvider(
        config=config(False),
        http_client=client,
        allow_network=True,
        environ={"GIGACHAT_AUTH_KEY": "fake-key"},
    ).generate(AIRequest(prompt="hello")).is_error
    assert client.calls == []

    assert GigaChatProvider(
        config=config(True),
        http_client=client,
        allow_network=True,
        environ={},
    ).generate(AIRequest(prompt="hello")).is_error
    assert client.calls == []

    assert GigaChatProvider(
        config=config(True),
        http_client=client,
        allow_network=False,
        environ={"GIGACHAT_AUTH_KEY": "fake-key"},
    ).generate(AIRequest(prompt="hello")).is_error
    assert client.calls == []


def test_enabled_fake_client_posts_chat_completions_and_parses_cyrillic_text():
    token = "fake-token-that-must-not-leak"
    auth_key = "fake-auth-key-that-must-not-leak"
    prompt = "Ответь одним словом: да"
    answer = "подключение работает"
    client = FakeHTTPClient(
        response=response(answer),
        expected_token=token,
        expected_prompt=prompt,
    )
    token_manager = FakeTokenManager(token=token)

    result = GigaChatProvider(
        config=config(True),
        token_manager=token_manager,
        http_client=client,
        allow_network=True,
        environ={"GIGACHAT_AUTH_KEY": auth_key},
    ).generate(AIRequest(prompt=prompt, metadata={"max_output_tokens": "128"}))

    assert result.is_error is False
    assert result.text == answer
    assert token_manager.calls == 1
    assert client.calls[0]["headers"]["Authorization"] == f"Bearer {token}"
    assert token not in result.text
    assert auth_key not in result.text


def test_summary_and_classification_prompts_are_mapped():
    client = FakeHTTPClient(response=response("ok"))
    provider = GigaChatProvider(
        config=config(True),
        token_manager=FakeTokenManager(),
        http_client=client,
        allow_network=True,
        environ={"GIGACHAT_AUTH_KEY": "fake-key"},
    )

    provider.generate(AIRequest(prompt="текст", task_type="summary"))
    provider.generate(AIRequest(prompt="запрос", task_type="classification"))

    assert client.calls[0]["payload"]["messages"][0]["content"].startswith("Кратко")
    assert client.calls[1]["payload"]["messages"][0]["content"].startswith("Классифицируй")


def test_malformed_missing_response_and_json_safe_errors():
    for payload in ({}, {"choices": []}, {"choices": [{"message": {}}]}):
        result = GigaChatProvider(
            config=config(True),
            token_manager=FakeTokenManager(),
            http_client=FakeHTTPClient(response=json.dumps(payload)),
            allow_network=True,
            environ={"GIGACHAT_AUTH_KEY": "fake-key"},
        ).generate(AIRequest(prompt="hello"))
        assert result.is_error is True
        assert "parsed safely" in result.text

    result = GigaChatProvider(
        config=config(True),
        token_manager=FakeTokenManager(),
        http_client=FakeHTTPClient(response="{bad"),
        allow_network=True,
        environ={"GIGACHAT_AUTH_KEY": "fake-key"},
    ).generate(AIRequest(prompt="hello"))
    assert result.is_error is True
    assert "valid JSON" in result.text


def test_http_errors_are_safe_and_mapped():
    for status, expected in (
        (401, "authentication/permission"),
        (403, "authentication/permission"),
        (404, "model"),
        (422, "validation/context"),
        (429, "rate or quota"),
    ):
        error = urllib.error.HTTPError(
            url="https://gigachat.devices.sberbank.ru",
            code=status,
            msg="fake-token",
            hdrs=None,
            fp=None,
        )
        result = GigaChatProvider(
            config=config(True),
            token_manager=FakeTokenManager(token="fake-token"),
            http_client=FakeHTTPClient(error=error),
            allow_network=True,
            environ={"GIGACHAT_AUTH_KEY": "fake-key"},
        ).generate(AIRequest(prompt="hello"))
        assert result.is_error is True
        assert expected in result.text
        assert "fake-token" not in result.text
        assert "fake-key" not in result.text


def test_safe_error_body_without_token_leak():
    token = "fake-token-that-must-not-leak"
    body = json.dumps(
        {"error": {"message": f"bad token {token}", "type": "auth", "code": "bad"}}
    ).encode("utf-8")
    error = urllib.error.HTTPError(
        url="https://gigachat.devices.sberbank.ru",
        code=403,
        msg="forbidden",
        hdrs=None,
        fp=io.BytesIO(body),
    )

    result = GigaChatProvider(
        config=config(True),
        token_manager=FakeTokenManager(token=token),
        http_client=FakeHTTPClient(error=error),
        allow_network=True,
        environ={"GIGACHAT_AUTH_KEY": "fake-key"},
    ).generate(AIRequest(prompt="hello"))

    assert result.is_error is True
    assert "bad token <redacted>" in result.text
    assert token not in result.text


def test_network_exception_safe_error_no_secret_leak():
    for error in (TimeoutError("fake-token"), socket.timeout("fake-token"), OSError("fake-token")):
        result = GigaChatProvider(
            config=config(True),
            token_manager=FakeTokenManager(token="fake-token"),
            http_client=FakeHTTPClient(error=error),
            allow_network=True,
            environ={"GIGACHAT_AUTH_KEY": "fake-key"},
        ).generate(AIRequest(prompt="hello"))
        assert result.is_error is True
        assert "fake-token" not in result.text
        assert "fake-key" not in result.text
