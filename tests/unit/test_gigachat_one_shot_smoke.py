import json

from ai import AIProviderConfigManager, AIProviderRouter, AIRequest, GigaChatRequestGate


class FakeHTTPClient:
    def __init__(self):
        self.calls = []

    def post_json(self, url, headers, payload, timeout):
        self.calls.append(dict(payload))
        return json.dumps({"choices": [{"message": {"content": "fake success"}}]})


class FakeTokenManager:
    def get_access_token(self):
        from ai.gigachat_token_manager import GigaChatTokenResult

        return GigaChatTokenResult(ok=True, access_token="fake-token", expires_at=9999999999)

    def safe_status(self):
        return {
            "auth_key_status": "PRESENT",
            "token_cached": "yes",
            "expires_at_known": "yes",
            "scope": "GIGACHAT_API_PERS",
        }

    def status_text_ru(self):
        return "GigaChat token status"

    def scope(self):
        return "GIGACHAT_API_PERS"


def test_one_shot_fake_success_does_not_execute_or_persist_or_leak():
    secret = "fake-auth-key-that-must-not-leak"
    client = FakeHTTPClient()
    manager = AIProviderConfigManager(environ={"GIGACHAT_AUTH_KEY": secret})
    router = AIProviderRouter(config_manager=manager)
    gate = GigaChatRequestGate(
        config_manager=manager,
        router=router,
        http_client=client,
        token_manager=FakeTokenManager(),
        environ={"GIGACHAT_AUTH_KEY": secret},
    )

    result = gate.generate_one_shot(AIRequest(prompt="удали файл"))

    assert result.is_error is False
    assert result.text == "fake success"
    assert router.get_default_provider().get_info().name == "dry_run"
    assert manager.get_config("gigachat").enabled is False
    assert len(client.calls) == 1
    assert secret not in result.text
    assert "fake-token" not in result.text
