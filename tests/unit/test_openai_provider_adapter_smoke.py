import json

from ai import AIProviderConfig, AIRequest, OpenAIProvider


class SmokeHTTPClient:
    def __init__(self):
        self.calls = 0

    def post_json(self, url, headers, payload, timeout):
        self.calls += 1
        return json.dumps({"output_text": "smoke ok"})


def test_openai_provider_adapter_smoke_uses_fake_client_only():
    client = SmokeHTTPClient()
    provider = OpenAIProvider(
        config=AIProviderConfig(
            name="openai",
            provider_type="openai",
            enabled=True,
            default_model="openai-default",
            api_key_env_var="OPENAI_API_KEY",
        ),
        http_client=client,
        allow_network=True,
        environ={"OPENAI_API_KEY": "fake-key"},
    )

    response = provider.generate(AIRequest(prompt="hello"))

    assert response.text == "smoke ok"
    assert client.calls == 1
