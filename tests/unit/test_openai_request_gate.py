import json

from ai import (
    AIProviderConfigManager,
    AIProviderKeyStatus,
    AIProviderRouter,
    AIRequest,
    OpenAIRequestGate,
)


class FakeHTTPClient:
    def __init__(self, response=None, error=None):
        self.response = response or json.dumps({"output_text": "fake answer"})
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


def test_missing_key_returns_safe_error_without_request():
    client = FakeHTTPClient()
    gate = OpenAIRequestGate(
        config_manager=AIProviderConfigManager(environ={}),
        http_client=client,
        environ={},
    )

    response = gate.generate_one_shot(AIRequest(prompt="hello"))

    assert response.is_error is True
    assert response.error_message == "OPENAI_API_KEY is missing."
    assert client.calls == []


def test_present_key_fake_client_calls_provider_once():
    secret = "fake-openai-key-that-must-not-leak"
    client = FakeHTTPClient()
    gate = OpenAIRequestGate(
        config_manager=AIProviderConfigManager(environ={"OPENAI_API_KEY": secret}),
        http_client=client,
        environ={"OPENAI_API_KEY": secret},
    )

    response = gate.generate_one_shot(AIRequest(prompt="hello"))

    assert response.is_error is False
    assert response.text == "fake answer"
    assert len(client.calls) == 1
    assert client.calls[0]["payload"] == {
        "model": "gpt-5.6",
        "input": "hello",
        "max_output_tokens": 128,
    }
    assert secret not in response.text
    assert response.model_name == "gpt-5.6"


def test_one_shot_does_not_change_router_default():
    router = AIProviderRouter()
    client = FakeHTTPClient()
    gate = OpenAIRequestGate(
        config_manager=AIProviderConfigManager(environ={"OPENAI_API_KEY": "fake-key"}),
        router=router,
        http_client=client,
        environ={"OPENAI_API_KEY": "fake-key"},
    )

    gate.generate_one_shot(AIRequest(prompt="hello"))

    assert router.get_default_provider().get_info().name == "dry_run"


def test_one_shot_does_not_persist_enabled_state():
    manager = AIProviderConfigManager(environ={"OPENAI_API_KEY": "fake-key"})
    gate = OpenAIRequestGate(
        config_manager=manager,
        http_client=FakeHTTPClient(),
        environ={"OPENAI_API_KEY": "fake-key"},
    )

    gate.generate_one_shot(AIRequest(prompt="hello"))

    assert manager.get_config("openai").enabled is False
    assert manager.status_for("openai").enabled is False


def test_empty_prompt_safe_error_without_request():
    client = FakeHTTPClient()
    gate = OpenAIRequestGate(
        config_manager=AIProviderConfigManager(environ={"OPENAI_API_KEY": "fake-key"}),
        http_client=client,
        environ={"OPENAI_API_KEY": "fake-key"},
    )

    response = gate.generate_one_shot(AIRequest(prompt=""))

    assert response.is_error is True
    assert response.error_message == "AI prompt is empty."
    assert client.calls == []


def test_too_long_prompt_safe_error_without_request():
    client = FakeHTTPClient()
    gate = OpenAIRequestGate(
        config_manager=AIProviderConfigManager(environ={"OPENAI_API_KEY": "fake-key"}),
        http_client=client,
        environ={"OPENAI_API_KEY": "fake-key"},
    )

    response = gate.generate_one_shot(AIRequest(prompt="x" * 1201))

    assert response.is_error is True
    assert "limit is 1200" in response.error_message
    assert client.calls == []


def test_invalid_model_safe_error_without_request():
    client = FakeHTTPClient()
    environ = {
        "OPENAI_API_KEY": "fake-key",
        "OPENAI_MODEL": "bad model",
    }
    gate = OpenAIRequestGate(
        config_manager=AIProviderConfigManager(environ=environ),
        http_client=client,
        environ=environ,
    )

    response = gate.generate_one_shot(AIRequest(prompt="hello"))

    assert response.is_error is True
    assert "model" in response.error_message.lower()
    assert client.calls == []


def test_network_or_provider_error_is_safe():
    secret = "fake-openai-key-that-must-not-leak"
    client = FakeHTTPClient(error=OSError(f"boom {secret}"))
    gate = OpenAIRequestGate(
        config_manager=AIProviderConfigManager(environ={"OPENAI_API_KEY": secret}),
        http_client=client,
        environ={"OPENAI_API_KEY": secret},
    )

    response = gate.generate_one_shot(AIRequest(prompt="hello"))

    assert response.is_error is True
    assert response.error_message == "OpenAI network error."
    assert secret not in response.text
    assert secret not in response.error_message


def test_status_text_mentions_missing_or_present_without_key_value():
    missing_gate = OpenAIRequestGate(
        config_manager=AIProviderConfigManager(environ={}),
        environ={},
    )
    secret = "fake-openai-key-that-must-not-leak"
    present_gate = OpenAIRequestGate(
        config_manager=AIProviderConfigManager(environ={"OPENAI_API_KEY": secret}),
        environ={"OPENAI_API_KEY": secret},
    )

    missing_text = missing_gate.status_text_ru()
    present_text = present_gate.status_text_ru()

    assert "MISSING" in missing_text
    assert "PRESENT" in present_text
    assert "key value is never printed" in present_text
    assert secret not in present_text
    assert present_gate.can_make_real_request().key_status == AIProviderKeyStatus.PRESENT


def test_guard_status_mentions_limits_and_cost_warning():
    text = OpenAIRequestGate(
        config_manager=AIProviderConfigManager(environ={}),
        environ={},
    ).guard_status_text_ru()

    assert "model source" in text
    assert "max prompt chars: 1200" in text
    assert "max_output_tokens: 128" in text
    assert "account credits/limits" in text
