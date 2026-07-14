import json

from ai import AIProviderConfigManager, AIProviderRouter, AIRequest, OpenAIRequestGate
from core.command_processor import CommandProcessor


class FakeHTTPClient:
    def __init__(self):
        self.calls = []

    def post_json(self, url, headers, payload, timeout):
        self.calls.append(dict(payload))
        return json.dumps({"output_text": "fake one-shot response"})


class FailingActionRouter:
    calls = 0

    def route(self, command):
        self.calls += 1
        raise AssertionError("OpenAI response must not route to ActionRouter")


def test_one_shot_smoke_keeps_dry_run_default_and_no_action_execution():
    router = AIProviderRouter()
    client = FakeHTTPClient()
    gate = OpenAIRequestGate(
        config_manager=AIProviderConfigManager(environ={"OPENAI_API_KEY": "fake-key"}),
        router=router,
        http_client=client,
        environ={"OPENAI_API_KEY": "fake-key"},
    )
    processor = CommandProcessor(
        ai_provider_router=router,
        ai_provider_config_manager=gate.config_manager,
        openai_request_gate=gate,
    )
    processor.action_router = FailingActionRouter()

    response = gate.generate_one_shot(AIRequest(prompt="hello"))
    result = processor.process("openai one shot: hello")

    assert response.text == "fake one-shot response"
    assert "fake one-shot response" in result["response"]
    assert router.get_default_provider().get_info().name == "dry_run"
    assert processor.action_router.calls == 0
    assert len(client.calls) == 2
