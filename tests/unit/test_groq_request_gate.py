import json

from ai import AIProviderConfig, AIProviderConfigManager, AIProviderRouter, AIRequest, GroqRequestGate


class FakeHTTPClient:
    def __init__(self, response=None, error=None):
        self.response = response or json.dumps(
            {"choices": [{"message": {"content": "fake answer"}}]}
        )
        self.error = error
        self.calls = []

    def post_json(self, url, headers, payload, timeout):
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
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


def test_missing_key_returns_safe_error_without_request():
    client = FakeHTTPClient()
    gate = GroqRequestGate(
        config_manager=AIProviderConfigManager(environ={}),
        http_client=client,
        environ={},
    )

    response = gate.generate_one_shot(AIRequest(prompt="hello"))

    assert response.is_error is True
    assert response.error_message == "GROQ_API_KEY is missing."
    assert client.calls == []


def test_too_long_prompt_safe_error_without_request():
    client = FakeHTTPClient()
    gate = GroqRequestGate(
        config_manager=AIProviderConfigManager(environ={"GROQ_API_KEY": "fake-key"}),
        http_client=client,
        environ={"GROQ_API_KEY": "fake-key"},
    )

    response = gate.generate_one_shot(AIRequest(prompt="x" * 1201))

    assert response.is_error is True
    assert "limit is 1200" in response.error_message
    assert client.calls == []


def test_invalid_model_safe_error_without_request():
    client = FakeHTTPClient()
    environ = {"GROQ_API_KEY": "fake-key", "GROQ_MODEL": "bad model"}
    gate = GroqRequestGate(
        config_manager=AIProviderConfigManager(environ=environ),
        http_client=client,
        environ=environ,
    )

    response = gate.generate_one_shot(AIRequest(prompt="hello"))

    assert response.is_error is True
    assert "model" in response.error_message.lower()
    assert client.calls == []


def test_present_key_fake_client_succeeds_with_cyrillic_prompt():
    secret = "fake-groq-key-that-must-not-leak"
    client = FakeHTTPClient(
        response=json.dumps(
            {"choices": [{"message": {"content": "реальный ответ"}}]},
            ensure_ascii=False,
        )
    )
    manager = AIProviderConfigManager(environ={"GROQ_API_KEY": secret})
    router = AIProviderRouter(config_manager=manager)
    gate = GroqRequestGate(
        config_manager=manager,
        router=router,
        http_client=client,
        environ={"GROQ_API_KEY": secret},
    )

    response = gate.generate_one_shot(AIRequest(prompt="Привет, проверь связь"))

    assert response.is_error is False
    assert response.text == "реальный ответ"
    assert len(client.calls) == 1
    assert client.calls[0]["payload"]["model"] == "llama-3.1-8b-instant"
    assert client.calls[0]["payload"]["messages"] == [
        {"role": "user", "content": "Привет, проверь связь"}
    ]
    assert client.calls[0]["payload"]["max_tokens"] == 128
    assert client.calls[0]["headers"]["Authorization"] == f"Bearer {secret}"
    assert client.calls[0]["headers"]["User-Agent"] == "JARVIS-OS/0.2"
    assert "Groq is not enabled permanently" in gate.status_text_ru()
    assert router.get_default_provider().get_info().name == "dry_run"
    assert manager.get_config("groq").enabled is False
    assert secret not in response.text
    assert secret not in gate.status_text_ru()


def test_success_status_mentions_limits_quota_and_no_key():
    secret = "fake-groq-key-that-must-not-leak"
    gate = GroqRequestGate(
        config_manager=AIProviderConfigManager(environ={"GROQ_API_KEY": secret}),
        http_client=FakeHTTPClient(),
        environ={"GROQ_API_KEY": secret},
    )

    text = "\n".join([gate.status_text_ru(), gate.guard_status_text_ru()])

    assert "PRESENT" in text
    assert "llama-3.1-8b-instant" in text
    assert "max_tokens: 128" in text
    assert "free/developer" in text
    assert secret not in text


def test_one_shot_does_not_change_router_default_or_persist_enabled_state():
    manager = AIProviderConfigManager(environ={"GROQ_API_KEY": "fake-key"})
    router = AIProviderRouter(config_manager=manager)
    gate = GroqRequestGate(
        config_manager=manager,
        router=router,
        http_client=FakeHTTPClient(),
        environ={"GROQ_API_KEY": "fake-key"},
    )

    gate.generate_one_shot(AIRequest(prompt="hello"))

    assert router.get_default_provider().get_info().name == "dry_run"
    assert manager.get_config("groq").enabled is False
    assert manager.status_for("groq").enabled is False


def test_one_shot_config_keeps_real_groq_env_var_and_never_masked_key():
    secret = "fake-groq-key-that-must-not-leak"
    configs = [
        AIProviderConfig(
            name="groq",
            provider_type="groq",
            enabled=False,
            default_model="masked-model",
            api_key_env_var="MASKED_GROQ_KEY",
        )
    ]
    manager = AIProviderConfigManager(
        configs=configs,
        environ={"GROQ_API_KEY": secret, "MASKED_GROQ_KEY": "********"},
    )
    client = FakeHTTPClient()
    gate = GroqRequestGate(
        config_manager=manager,
        http_client=client,
        environ={"GROQ_API_KEY": secret, "MASKED_GROQ_KEY": "********"},
    )

    response = gate.generate_one_shot(AIRequest(prompt="Привет"))

    assert response.is_error is False
    assert len(client.calls) == 1
    assert client.calls[0]["headers"]["Authorization"] == f"Bearer {secret}"
    assert "********" not in client.calls[0]["headers"]["Authorization"]
    assert client.calls[0]["payload"]["model"] == "llama-3.1-8b-instant"
    assert manager.get_config("groq").api_key_env_var == "MASKED_GROQ_KEY"
    assert manager.get_config("groq").enabled is False
    assert secret not in gate.request_shape_text_ru()
