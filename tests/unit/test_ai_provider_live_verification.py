from ai import (
    AIContextPrivacyPolicy,
    AIProviderConfigManager,
    AIProviderLiveVerification,
    OllamaRuntimeStatus,
)


class FakeOllamaRuntime:
    def __init__(self):
        self.calls = []
        self.config = type("Config", (), {"model": "qwen2.5:1.5b"})()

    def status(self, check_models=True):
        self.calls.append(check_models)
        return OllamaRuntimeStatus(
            ok=False,
            base_url="http://127.0.0.1:11434",
            model="qwen2.5:1.5b",
            server_reachable=False,
            model_installed=None,
            installed_models=(),
            safe_message="Ollama localhost server is unavailable.",
        )


def make_verifier(environ=None, runtime=None):
    return AIProviderLiveVerification(
        config_manager=AIProviderConfigManager(environ=environ or {}),
        context_privacy_policy=AIContextPrivacyPolicy(),
        ollama_runtime=runtime or FakeOllamaRuntime(),
    )


def test_status_text_safe_no_network():
    runtime = FakeOllamaRuntime()
    text = make_verifier(runtime=runtime).status_text_ru()

    assert "enabled: yes" in text
    assert "network: not called" in text
    assert "dry_run default: yes" in text
    assert "no secrets printed" in text
    assert "not executed as commands" in text
    assert runtime.calls == []


def test_checklist_text_safe_no_network():
    runtime = FakeOllamaRuntime()
    text = make_verifier(runtime=runtime).checklist_text_ru()

    assert "no-key safe mode" in text
    assert "Ollama local checklist" in text
    assert "Groq live checklist" in text
    assert "GigaChat live checklist" in text
    assert "voice safety checklist" in text
    assert "network: not called" in text
    assert runtime.calls == []


def test_no_key_check_safe_no_network_and_presence_only():
    runtime = FakeOllamaRuntime()
    text = make_verifier(environ={"GROQ_API_KEY": "fake-key"}, runtime=runtime).no_key_check_text_ru()

    assert "openai: MISSING" in text
    assert "gemini: MISSING" in text
    assert "groq: PRESENT" in text
    assert "gigachat: MISSING" in text
    assert "fake-key" not in text
    assert "network: not called" in text
    assert "fallback explicit command required" in text
    assert runtime.calls == []


def test_privacy_verification_safe_no_network_no_raw_secret():
    runtime = FakeOllamaRuntime()
    text = make_verifier(runtime=runtime).privacy_check_text_ru()

    assert "network: not called" in text
    assert "uses canned safe examples only" in text
    assert "secret-like example external allowed: False" in text
    assert "private example external allowed: False" in text
    assert "consensus private example allowed: False" in text
    assert "[REDACTED]" in text
    assert "sk-test-secret-value-1234567890abcdef" not in text
    assert "no real provider called" in text
    assert runtime.calls == []


def test_live_readiness_no_network_and_key_presence_only():
    runtime = FakeOllamaRuntime()
    text = make_verifier(
        environ={"GROQ_API_KEY": "gsk_secret_value", "GIGACHAT_AUTH_KEY": "gigachat_secret"},
        runtime=runtime,
    ).live_readiness_text_ru()

    assert "network: not called" in text
    assert "groq: PRESENT" in text
    assert "gigachat: PRESENT" in text
    assert "openai: MISSING" in text
    assert "gemini: MISSING" in text
    assert "gsk_secret_value" not in text
    assert "gigachat_secret" not in text
    assert "groq реальный запрос:" in text
    assert "gigachat реальный запрос:" in text
    assert "fallback ai запрос:" in text
    assert runtime.calls == []


def test_local_ollama_readiness_uses_local_only_runtime_and_handles_unavailable():
    runtime = FakeOllamaRuntime()
    text = make_verifier(runtime=runtime).local_check_text_ru()

    assert runtime.calls == [True]
    assert "network scope: localhost-only /api/tags" in text
    assert "external network called: False" in text
    assert "Ollama localhost server is unavailable" in text
    assert "no pull/download/install" in text
    assert "no cloud" in text
    assert "no keys" in text


def test_verification_texts_do_not_persist_or_execute_responses():
    verifier = make_verifier()

    for text in (
        verifier.status_text_ru(),
        verifier.checklist_text_ru(),
        verifier.no_key_check_text_ru(),
        verifier.privacy_check_text_ru(),
        verifier.live_readiness_text_ru(),
        verifier.local_check_text_ru(),
    ):
        assert "no prompt/response storage" in text or "prompt/response storage" in text
        assert "not executed as commands" in text
