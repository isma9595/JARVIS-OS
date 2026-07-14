import json

from ai import AIProviderConfigManager, AIProviderRouter, AIRequest, GroqRequestGate


class FakeHTTPClient:
    def __init__(self):
        self.calls = []

    def post_json(self, url, headers, payload, timeout):
        self.calls.append((url, headers, payload, timeout))
        return json.dumps({"choices": [{"message": {"content": "do not execute me"}}]})


def test_groq_one_shot_fake_success_does_not_persist_or_execute():
    manager = AIProviderConfigManager(environ={"GROQ_API_KEY": "fake-key"})
    router = AIProviderRouter(config_manager=manager)
    client = FakeHTTPClient()
    gate = GroqRequestGate(
        config_manager=manager,
        router=router,
        http_client=client,
        environ={"GROQ_API_KEY": "fake-key"},
    )

    response = gate.generate_one_shot(AIRequest(prompt="hello"))

    assert response.is_error is False
    assert response.text == "do not execute me"
    assert len(client.calls) == 1
    assert router.get_default_provider().get_info().name == "dry_run"
    assert manager.get_config("groq").enabled is False
