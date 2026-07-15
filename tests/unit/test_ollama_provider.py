from ai.ollama_runtime import OllamaRuntime
from ai.provider_contracts import AIProviderCapability, AIRequest
from ai.providers.ollama_provider import OllamaProvider


class FakeOllamaClient:
    def __init__(self, response=None, error=None):
        self.response = response or {"message": {"content": "local answer"}}
        self.error = error
        self.posts = []

    def post_json(self, url, payload, timeout):
        self.posts.append({"url": url, "payload": dict(payload), "timeout": timeout})
        if self.error:
            raise self.error
        return self.response

    def get_json(self, url, timeout):
        return {"models": [{"name": "qwen2.5:1.5b"}]}


def test_provider_metadata_name_and_local_only_safety():
    provider = OllamaProvider()
    info = provider.get_info()

    assert info.name == "ollama"
    assert info.safety_level == "local_only"
    assert "chat" in info.capabilities
    assert info.enabled is False


def test_chat_uses_stream_false_and_parses_answer():
    client = FakeOllamaClient()
    runtime = OllamaRuntime(http_client=client, environ={})
    provider = OllamaProvider(runtime=runtime, enabled=True)

    response = provider.generate(AIRequest(prompt="hello"))

    assert response.is_error is False
    assert response.text == "local answer"
    assert client.posts[0]["payload"]["stream"] is False
    assert client.posts[0]["payload"]["messages"] == [{"role": "user", "content": "hello"}]


def test_errors_are_sanitized_and_not_executed():
    client = FakeOllamaClient(error=OSError("token=secret-value-that-must-not-print"))
    runtime = OllamaRuntime(http_client=client, environ={})
    provider = OllamaProvider(runtime=runtime, enabled=True)

    response = provider.generate(AIRequest(prompt="hello"))

    assert response.is_error is True
    assert "secret-value" not in response.text
    assert response.provider_name == "ollama"
    assert response.capability == AIProviderCapability.CHAT.value
