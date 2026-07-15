import json

from ai import AIProviderConfigManager, AIProviderRouter, AIRequest, GigaChatRequestGate


class FakeHTTPClient:
    def __init__(self):
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
        return json.dumps(
            {"choices": [{"message": {"content": "реальный ответ"}}]},
            ensure_ascii=False,
        )


class FakeTokenManager:
    def __init__(self):
        self.calls = 0

    def get_access_token(self):
        self.calls += 1
        from ai.gigachat_token_manager import GigaChatTokenResult

        return GigaChatTokenResult(ok=True, access_token="fake-token", expires_at=9999999999)

    def safe_status(self):
        return {
            "auth_key_status": "PRESENT",
            "token_cached": "yes" if self.calls else "no",
            "expires_at_known": "yes" if self.calls else "no",
            "scope": "GIGACHAT_API_PERS",
        }

    def status_text_ru(self):
        return "GigaChat token status:\n- token cached in memory: yes\n- token value is never printed\n- network: not called"

    def scope(self):
        return "GIGACHAT_API_PERS"


def test_missing_auth_key_no_network():
    client = FakeHTTPClient()
    gate = GigaChatRequestGate(
        config_manager=AIProviderConfigManager(environ={}),
        http_client=client,
        environ={},
    )

    result = gate.generate_one_shot(AIRequest(prompt="hello"))

    assert result.is_error is True
    assert result.error_message == "GIGACHAT_AUTH_KEY is missing."
    assert client.calls == []


def test_prompt_too_long_and_invalid_model_no_network():
    client = FakeHTTPClient()
    gate = GigaChatRequestGate(
        config_manager=AIProviderConfigManager(environ={"GIGACHAT_AUTH_KEY": "fake-key"}),
        http_client=client,
        environ={"GIGACHAT_AUTH_KEY": "fake-key"},
    )
    assert gate.generate_one_shot(AIRequest(prompt="x" * 1201)).is_error is True

    gate = GigaChatRequestGate(
        config_manager=AIProviderConfigManager(environ={"GIGACHAT_AUTH_KEY": "fake-key"}),
        http_client=client,
        environ={"GIGACHAT_AUTH_KEY": "fake-key", "GIGACHAT_MODEL": "bad model"},
    )
    assert gate.generate_one_shot(AIRequest(prompt="hello")).is_error is True
    assert client.calls == []


def test_present_key_fake_token_and_client_succeeds_without_persistence():
    secret = "fake-auth-key-that-must-not-leak"
    client = FakeHTTPClient()
    token_manager = FakeTokenManager()
    manager = AIProviderConfigManager(environ={"GIGACHAT_AUTH_KEY": secret})
    router = AIProviderRouter(config_manager=manager)
    gate = GigaChatRequestGate(
        config_manager=manager,
        router=router,
        http_client=client,
        token_manager=token_manager,
        environ={"GIGACHAT_AUTH_KEY": secret},
    )

    result = gate.generate_one_shot(AIRequest(prompt="Привет"))

    assert result.is_error is False
    assert result.text == "реальный ответ"
    assert token_manager.calls == 1
    assert len(client.calls) == 1
    assert client.calls[0]["payload"]["model"] == "GigaChat"
    sent_prompt = client.calls[0]["payload"]["messages"][0]["content"]
    assert sent_prompt.startswith("Системная инструкция JARVIS:")
    assert "Отвечай на русском языке" in sent_prompt
    assert sent_prompt.endswith("Привет")
    assert client.calls[0]["payload"]["max_tokens"] == 128
    assert client.calls[0]["headers"]["Authorization"] == "Bearer fake-token"
    assert router.get_default_provider().get_info().name == "dry_run"
    assert manager.get_config("gigachat").enabled is False
    assert secret not in result.text
    assert "fake-token" not in result.text


def test_status_and_request_shape_safe_no_secrets():
    secret = "fake-auth-key-that-must-not-leak"
    gate = GigaChatRequestGate(
        config_manager=AIProviderConfigManager(environ={"GIGACHAT_AUTH_KEY": secret}),
        token_manager=FakeTokenManager(),
        environ={"GIGACHAT_AUTH_KEY": secret},
    )
    text = "\n".join(
        [
            gate.status_text_ru(),
            gate.guard_status_text_ru(),
            gate.token_status_text_ru(),
            gate.model_text_ru(),
            gate.request_shape_text_ru(),
        ]
    )

    assert "GigaChat" in text
    assert "max_tokens: 128" in text
    assert "free/paid quota" in text
    assert "one-shot" in text
    assert "network: not called" in text
    assert "Authorization Basic: PRESENT" in text
    assert secret not in text
    assert "fake-token" not in text


def test_explicit_english_prompt_does_not_force_russian():
    client = FakeHTTPClient()
    gate = GigaChatRequestGate(
        config_manager=AIProviderConfigManager(environ={"GIGACHAT_AUTH_KEY": "fake-key"}),
        http_client=client,
        token_manager=FakeTokenManager(),
        environ={"GIGACHAT_AUTH_KEY": "fake-key"},
    )

    result = gate.generate_one_shot(AIRequest(prompt="Answer in English: hello"))

    assert result.is_error is False
    sent_prompt = client.calls[0]["payload"]["messages"][0]["content"]
    assert sent_prompt.startswith("Системная инструкция JARVIS:")
    assert "Отвечай на русском языке" not in sent_prompt
    assert "Соблюдай эту просьбу" in sent_prompt
    assert sent_prompt.endswith("Answer in English: hello")
