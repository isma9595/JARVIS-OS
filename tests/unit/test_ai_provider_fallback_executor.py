from ai import (
    AIProviderConfigManager,
    AIProviderFallbackExecutor,
    AIProviderSessionState,
)
from ai.provider_contracts import AIResponse


class FakeGate:
    def __init__(self, provider, model="fake-model", ok=True, error="failed"):
        self.provider = provider
        self.model = model
        self.ok = ok
        self.error = error
        self.calls = []

    def generate_one_shot(self, request, capability, model_override=None):
        self.calls.append((request.prompt, capability.value, model_override))
        model = model_override or self.model
        if not self.ok:
            return AIResponse(
                text=self.error,
                provider_name=f"{self.provider}_request_gate",
                model_name=model,
                capability=capability.value,
                safety_level="external_api",
                is_error=True,
                error_message=self.error,
            )
        return AIResponse(
            text=f"{self.provider} answer",
            provider_name=self.provider,
            model_name=model,
            capability=capability.value,
            safety_level="external_api",
        )


def executor(environ=None, gates=None):
    manager = AIProviderConfigManager(environ=environ or {})
    return AIProviderFallbackExecutor(
        config_manager=manager,
        request_gates=gates or {},
    )


def test_status_text_safe_no_network():
    text = executor().status_text_ru()

    assert "enabled: yes" in text
    assert "explicit only" in text
    assert "ordinary provider commands: no automatic retry" in text
    assert "network: not called" in text


def test_plan_text_safe_no_network_and_general_chain_deterministic():
    text = executor().plan_text_ru("ordinary short question")

    assert "network: not called" in text
    assert "groq -> gigachat -> openai -> gemini -> ollama -> dry_run" in text
    assert "key MISSING" in text


def test_private_prompt_chain_ollama_then_dry_run():
    plan = executor({"GROQ_API_KEY": "fake"}).build_plan(
        "private file, do not send to internet"
    )

    assert plan.chain == ("ollama", "dry_run")


def test_secret_like_prompt_blocks_real_providers_and_redacts_secret():
    secret = "sk-test-1234567890secret"
    gate = FakeGate("groq")
    result = executor({"GROQ_API_KEY": "fake"}, {"groq": gate}).execute(
        f"my api key {secret}"
    )
    text = executor({"GROQ_API_KEY": "fake"}, {"groq": gate}).result_text_ru(result)

    assert gate.calls == []
    assert "BLOCKED_BY_PRIVACY" in [attempt.status for attempt in result.attempts]
    assert secret not in text
    assert "[REDACTED]" in text


def test_manual_session_provider_first_and_does_not_bypass_privacy():
    session = AIProviderSessionState()
    session.select_manual("openai", "manual-model")

    private_plan = executor().build_plan(
        "private file, do not send to internet",
        session_snapshot=session.snapshot(),
    )
    result = executor({"OPENAI_API_KEY": "fake"}).execute(
        "private file, do not send to internet",
        session_snapshot=session.snapshot(),
    )

    assert private_plan.chain[:3] == ("openai", "ollama", "dry_run")
    assert result.attempts[0].provider == "openai"
    assert result.attempts[0].status == "BLOCKED_BY_PRIVACY"


def test_missing_keys_skipped_safely_and_dry_run_terminal_fallback_works():
    ollama = FakeGate("ollama", ok=False, error="Ollama localhost server is unavailable.")
    result = executor(gates={"ollama": ollama}).execute("ordinary short question")

    statuses = {attempt.provider: attempt.status for attempt in result.attempts}
    assert statuses["groq"] == "MISSING_KEY"
    assert statuses["openai"] == "MISSING_KEY"
    assert result.final_provider == "dry_run"
    assert result.ok is True
    assert result.network_called is True
    assert result.dry_run_default_unchanged is True
    assert result.response_executed is False


def test_ollama_unavailable_skipped_safely():
    ollama = FakeGate("ollama", ok=False, error="Ollama localhost server is unavailable.")
    result = executor(gates={"ollama": ollama}).execute("ordinary short question")

    ollama_attempt = [a for a in result.attempts if a.provider == "ollama"][0]
    assert ollama_attempt.status == "UNAVAILABLE"
    assert result.final_provider == "dry_run"


def test_stops_after_first_success_and_does_not_call_same_provider_twice():
    groq = FakeGate("groq")
    openai = FakeGate("openai")
    result = executor(
        {"GROQ_API_KEY": "fake", "OPENAI_API_KEY": "fake"},
        {"groq": groq, "openai": openai},
    ).execute("ordinary short question")

    assert result.final_provider == "groq"
    assert len(groq.calls) == 1
    assert openai.calls == []
    assert len({attempt.provider for attempt in result.attempts}) == len(result.attempts)


def test_no_prompts_responses_persisted_and_consensus_not_invoked():
    item = executor()
    result = item.execute("ordinary short question")

    assert not hasattr(item, "prompt")
    assert not hasattr(item, "response")
    assert not hasattr(item, "consensus")
    assert result.response_executed is False
