from ai import AIProviderRouter, AIRequest


def test_ai_provider_router_smoke():
    response = AIProviderRouter().generate(AIRequest(prompt="привет"))

    assert response.provider_name == "dry_run"
    assert "AI dry-run" in response.text
