from ai.ollama_request_gate import OllamaRequestGate
from ai.ollama_runtime import OllamaRuntime
from ai.provider_contracts import AIProviderCapability, AIRequest


class FakeOllamaClient:
    def __init__(self, models=None, answer="локальный ответ", fail_tags=False):
        self.models = models if models is not None else ["qwen2.5:1.5b"]
        self.answer = answer
        self.fail_tags = fail_tags
        self.get_calls = []
        self.post_calls = []

    def get_json(self, url, timeout):
        self.get_calls.append((url, timeout))
        if self.fail_tags:
            raise OSError("server down")
        return {"models": [{"name": model} for model in self.models]}

    def post_json(self, url, payload, timeout):
        self.post_calls.append({"url": url, "payload": dict(payload), "timeout": timeout})
        return {"message": {"content": self.answer}}


def gate(client):
    return OllamaRequestGate(runtime=OllamaRuntime(http_client=client, environ={}))


def test_status_and_model_text_are_safe_no_external_network():
    client = FakeOllamaClient()
    request_gate = gate(client)

    status = request_gate.status_text()
    model = request_gate.model_text()

    assert "provider: ollama" in status
    assert "network: not called" in status
    assert "key: not required" in status
    assert "dry_run remains default" in status
    assert "default model: qwen2.5:1.5b" in model
    assert client.get_calls == []
    assert client.post_calls == []


def test_runtime_status_handles_unavailable_server():
    text = gate(FakeOllamaClient(fail_tags=True)).runtime_status_text()

    assert "localhost-only /api/tags" in text
    assert "server reachable: False" in text
    assert "chat request was not sent" in text


def test_one_shot_with_unavailable_server_refuses_safely():
    request_gate = gate(FakeOllamaClient(fail_tags=True))

    response = request_gate.generate_one_shot(AIRequest(prompt="hello"))

    assert response.is_error is True
    assert "unavailable" in response.text
    assert response.safety_level == "local_only"


def test_one_shot_success_applies_language_policy_and_stream_false():
    client = FakeOllamaClient()
    request_gate = gate(client)

    response = request_gate.generate_one_shot(
        AIRequest(prompt="Скажи коротко: работает?"),
        capability=AIProviderCapability.CHAT,
    )

    assert response.is_error is False
    assert response.text == "локальный ответ"
    assert client.post_calls[0]["payload"]["stream"] is False
    assert "JARVIS" in client.post_calls[0]["payload"]["messages"][0]["content"]


def test_ollama_allows_private_typed_prompt_for_local_call():
    client = FakeOllamaClient()
    request_gate = gate(client)

    response = request_gate.generate_one_shot(
        AIRequest(prompt="это приватный файл, не отправляй в интернет"),
        capability=AIProviderCapability.CHAT,
    )

    assert response.is_error is False
    assert len(client.post_calls) == 1


def test_ollama_blocks_secret_like_prompt_before_local_call():
    secret = "sk-test-1234567890secret"
    client = FakeOllamaClient()
    request_gate = gate(client)

    response = request_gate.generate_one_shot(AIRequest(prompt=f"my api key {secret}"))

    assert response.is_error is True
    assert secret not in response.error_message
    assert "[REDACTED]" in response.error_message
    assert client.get_calls == []
    assert client.post_calls == []


def test_unsafe_model_override_rejected_before_network():
    client = FakeOllamaClient()
    request_gate = gate(client)

    response = request_gate.generate_one_shot(
        AIRequest(prompt="hello"),
        model_override="sk-secret-token",
    )

    assert response.is_error is True
    assert client.get_calls == []
    assert client.post_calls == []


def test_safe_model_examples_accepted():
    request_gate = gate(FakeOllamaClient())

    for model in ("qwen2.5:1.5b", "llama3.2:1b", "gemma3:1b", "mistral:7b"):
        assert request_gate.validate_model(model) is None


def test_model_missing_refuses_without_chat_or_pull():
    client = FakeOllamaClient(models=["llama3.2:1b"])
    request_gate = gate(client)

    response = request_gate.generate_one_shot(AIRequest(prompt="hello"))

    assert response.is_error is True
    assert "not installed locally" in response.text
    assert client.post_calls == []


def test_safety_footer_and_no_key_token_leak():
    text = gate(FakeOllamaClient()).runtime_status_text()

    assert "key/token: not required" in text
    assert "memory/profile/files/logs not sent" in text
    assert "response was not executed as a command" in text
