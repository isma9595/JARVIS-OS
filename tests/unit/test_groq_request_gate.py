import json

from ai import AIProviderConfigManager, AIProviderRouter, AIRequest, GroqRequestGate


class FakeHTTPClient:
    def __init__(self, response=None, error=None):
        self.response = response or json.dumps(
            {"choices": [{"message": {"content": "fake answer"}}]}
        )
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


def test_present_key_fake_client_succeeds():
    secret = "fake-groq-key-that-must-not-leak"
    client = FakeHTTPClient()
    gate = GroqRequestGate(
        config_manager=AIProviderConfigManager(environ={"GROQ_API_KEY": secret}),
        http_client=client,
        environ={"GROQ_API_KEY": secret},
    )

    response = gate.generate_one_shot(AIRequest(prompt="hello"))

    assert response.is_error is False
    assert response.text == "fake answer"
    assert len(client.calls) == 1
    assert client.calls[0]["payload"]["model"] == "llama-3.1-8b-instant"
    assert client.calls[0]["payload"]["messages"][1]["content"] == "hello"
    assert client.calls[0]["payload"]["max_tokens"] == 128
    assert secret not in response.text


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
