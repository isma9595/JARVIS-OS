from ai import (
    AIProviderConfigManager,
    AIProviderSelectionPolicy,
    AIProviderSessionState,
)


def policy(environ=None):
    env = environ or {}
    return AIProviderSelectionPolicy(
        config_manager=AIProviderConfigManager(environ=env),
        environ=env,
    )


def test_status_text_safe_no_network_and_no_secret_values():
    secret = "secret-value-that-must-not-print"
    text = policy({"GROQ_API_KEY": secret}).status_text_ru()

    assert "enabled: yes" in text
    assert "recommendation only" in text
    assert "network: not called" in text
    assert "dry_run remains default" in text
    assert "manual session selection wins" in text
    assert "consensus remains explicit-only" in text
    assert secret not in text


def test_matrix_includes_all_providers_implemented_ollama_and_no_secret_values():
    secret = "secret-value-that-must-not-print"
    text = policy({"GIGACHAT_AUTH_KEY": secret}).matrix_text_ru()

    for provider_name in ("dry_run", "groq", "gigachat", "openai", "gemini", "ollama"):
        assert provider_name in text
    assert "ollama" in text
    assert "implemented=yes" in text
    assert "local-only" in text
    assert "GIGACHAT_AUTH_KEY" in text
    assert "PRESENT" in text
    assert "network: not called" in text
    assert secret not in text


def test_provider_order_deterministic():
    roles = policy().roles()

    assert [role.provider for role in roles] == [
        "dry_run",
        "groq",
        "gigachat",
        "openai",
        "gemini",
        "ollama",
    ]


def test_no_keys_default_recommendation_dry_run_no_external_available():
    recommendation = policy().recommend("быстро ответь на простой вопрос")

    assert recommendation.recommended_provider == "dry_run"
    assert recommendation.network_called is False
    assert recommendation.dry_run_default_unchanged is True
    assert "groq: key MISSING" in recommendation.skipped


def test_groq_key_present_fast_general_recommends_groq():
    recommendation = policy({"GROQ_API_KEY": "fake-test-key"}).recommend(
        "быстро ответь на простой вопрос"
    )

    assert recommendation.recommended_provider == "groq"
    assert recommendation.recommended_model == "llama-3.1-8b-instant"
    assert recommendation.fallback_chain[0] == "groq"
    assert recommendation.network_called is False


def test_gigachat_key_present_russian_prompt_recommends_gigachat():
    recommendation = policy({"GIGACHAT_AUTH_KEY": "fake-test-key"}).recommend(
        "ответь на русском про Россию"
    )

    assert recommendation.recommended_provider == "gigachat"
    assert recommendation.recommended_model == "GigaChat"
    assert recommendation.fallback_chain[0] == "gigachat"


def test_openai_key_present_code_reasoning_prompt_recommends_openai():
    recommendation = policy({"OPENAI_API_KEY": "fake-test-key"}).recommend(
        "напиши код на python и объясни архитектуру"
    )

    assert recommendation.recommended_provider == "openai"
    assert recommendation.fallback_chain[0] == "openai"


def test_gemini_key_present_fallback_included_for_code_prompt():
    recommendation = policy({"GEMINI_API_KEY": "fake-test-key"}).recommend(
        "debug python code"
    )

    assert "gemini" in recommendation.fallback_chain
    assert recommendation.fallback_chain[0] == "gemini"
    assert recommendation.network_called is False


def test_privacy_offline_prompt_recommends_ollama_then_dry_run():
    recommendation = policy({"GROQ_API_KEY": "fake-test-key"}).recommend(
        "это приватный файл, не отправляй в интернет"
    )

    assert recommendation.recommended_provider == "ollama"
    assert recommendation.recommended_model == "qwen2.5:1.5b"
    assert recommendation.fallback_chain == ["ollama", "dry_run"]
    assert any("runtime" in warning for warning in recommendation.warnings)
    assert recommendation.network_called is False


def test_secret_like_prompt_recommends_redaction_manual_handling():
    secret = "sk-test-1234567890secret"
    recommendation = policy({"GROQ_API_KEY": "fake-test-key"}).recommend(
        f"my api key {secret}"
    )
    text = policy({"GROQ_API_KEY": "fake-test-key"}).recommendation_text_ru(
        f"my api key {secret}"
    )

    assert recommendation.ok is False
    assert recommendation.recommended_provider == "dry_run"
    assert "redact" in recommendation.reason
    assert "all AI providers skipped" in recommendation.skipped[0]
    assert recommendation.network_called is False
    assert secret not in text


def test_raw_context_prompt_does_not_recommend_external_provider():
    for prompt in (
        "содержимое файла ниже",
        "скриншот экрана",
        "моя память",
        "debug log traceback",
    ):
        recommendation = policy({"GROQ_API_KEY": "fake-test-key"}).recommend(prompt)

        assert recommendation.recommended_provider == "dry_run"
        assert "groq" not in recommendation.fallback_chain
        assert "external providers skipped" in recommendation.skipped[0]
        assert recommendation.network_called is False


def test_consensus_compare_prompt_recommends_explicit_consensus_no_network():
    recommendation = policy({"GROQ_API_KEY": "fake-test-key"}).recommend(
        "сравни ответы нескольких ии"
    )

    assert recommendation.recommended_provider == "consensus"
    assert "groq" in recommendation.fallback_chain
    assert recommendation.network_called is False
    assert any("консенсус ai" in warning for warning in recommendation.warnings)


def test_manual_session_selection_wins_over_policy():
    session = AIProviderSessionState()
    session.select_manual("gigachat", "GigaChat")

    recommendation = policy({"OPENAI_API_KEY": "fake-test-key"}).recommend(
        "напиши код на python",
        session_snapshot=session.snapshot(),
    )

    assert recommendation.recommended_provider == "gigachat"
    assert recommendation.recommended_model == "GigaChat"
    assert "manual runtime selection wins" in recommendation.reason


def test_ollama_role_is_implemented_no_key_and_local_only():
    roles = {role.provider: role for role in policy().roles()}
    ollama = roles["ollama"]

    assert ollama.implemented is True
    assert ollama.requires_key is False
    assert ollama.network_capable is False
    assert ollama.default_model == "qwen2.5:1.5b"


def test_recommendation_text_includes_safe_next_command_and_does_not_execute_or_store_prompt():
    prompt = "быстро ответь"
    selector = policy({"GROQ_API_KEY": "fake-test-key"})
    text = selector.recommendation_text_ru(prompt)

    assert "groq реальный запрос: <text>" in text
    assert "network_called: False" in text
    assert "not executed" in text
    assert "was not stored" in text
    assert not hasattr(selector, "prompt")
    assert not hasattr(selector, "response")


def test_privacy_recommendation_text_mentions_ollama_commands_without_runtime_call():
    selector = policy({"GROQ_API_KEY": "fake-test-key"})
    text = selector.recommendation_text_ru("private offline file, no internet")

    assert "recommended provider: ollama" in text
    assert "список ollama моделей" in text
    assert "ollama реальный запрос: <text>" in text
    assert "network_called: False" in text
    assert "provider response execution: not applicable" in text
