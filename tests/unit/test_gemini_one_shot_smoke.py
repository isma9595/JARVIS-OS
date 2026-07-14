import json

from ai import AIProviderConfigManager, AIProviderRouter, GeminiRequestGate
from core.command_processor import CommandProcessor


class FakeHTTPClient:
    def __init__(self):
        self.calls = []

    def post_json(self, url, headers, payload, timeout):
        self.calls.append(payload)
        return json.dumps(
            {"candidates": [{"content": {"parts": [{"text": "fake success"}]}}]}
        )


def test_one_shot_fake_success_keeps_dry_run_default_and_no_execution():
    class FailingActionRouter:
        calls = 0

        def route(self, command):
            self.calls += 1
            raise AssertionError("Gemini output must not route to ActionRouter")

    client = FakeHTTPClient()
    manager = AIProviderConfigManager(environ={"GEMINI_API_KEY": "fake-key"})
    router = AIProviderRouter(config_manager=manager)
    processor = CommandProcessor(
        ai_provider_router=router,
        ai_provider_config_manager=manager,
        gemini_request_gate=GeminiRequestGate(
            config_manager=manager,
            router=router,
            http_client=client,
            environ={"GEMINI_API_KEY": "fake-key"},
        ),
    )
    processor.action_router = FailingActionRouter()

    result = processor.process("gemini one shot: hello")

    assert result["intent"] == "ai.gemini.one_shot"
    assert "Gemini real response:" in result["response"]
    assert "fake success" in result["response"]
    assert "response was not executed as a command" in result["response"]
    assert router.get_default_provider().get_info().name == "dry_run"
    assert manager.get_config("gemini").enabled is False
    assert processor.action_router.calls == 0
    assert len(client.calls) == 1
