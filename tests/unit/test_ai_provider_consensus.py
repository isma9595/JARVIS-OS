from ai import (
    AIProviderConsensusManager,
    AIProviderConfigManager,
    AIProviderSessionState,
    AIProviderSafetyLevel,
    AIRequest,
    AIResponse,
)


def response(provider, text, model="test-model", is_error=False, error=None):
    return AIResponse(
        text=text,
        provider_name=provider,
        model_name=model,
        capability="chat",
        safety_level=AIProviderSafetyLevel.EXTERNAL_API.value,
        is_error=is_error,
        error_message=error,
    )


def manager(environ=None, callers=None):
    env = environ or {}
    config_manager = AIProviderConfigManager(environ=env)
    return AIProviderConsensusManager(
        config_manager=config_manager,
        provider_callers=callers or {},
        environ=env,
    )


def test_status_text_safe_no_network():
    text = manager().status_text_ru()

    assert "enabled: yes" in text
    assert "explicit only" in text
    assert "groq, gigachat, openai, gemini" in text
    assert "dry_run: not included" in text
    assert "network: not called" in text


def test_empty_prompt_rejected_no_network():
    calls = []
    result = manager(
        {"GROQ_API_KEY": "fake"}, {"groq": lambda request: calls.append(request)}
    ).run_consensus("")

    assert result.ok is False
    assert result.attempted_count == 0
    assert "empty" in result.final_answer
    assert calls == []


def test_too_long_prompt_rejected_no_network():
    calls = []
    result = manager(
        {"GROQ_API_KEY": "fake"}, {"groq": lambda request: calls.append(request)}
    ).run_consensus("x" * 1201)

    assert result.ok is False
    assert result.attempted_count == 0
    assert "too long" in result.final_answer
    assert calls == []


def test_no_provider_keys_returns_safe_refusal_no_network():
    result = manager().run_consensus("hello")

    assert result.ok is False
    assert result.attempted_count == 0
    assert result.success_count == 0
    assert result.skipped_count == 4
    assert "No external provider keys are present" in result.final_answer


def test_one_provider_key_attempts_only_that_provider():
    calls = []

    def groq(request):
        calls.append(request.prompt)
        return response("groq", "Groq answer about JARVIS.")

    result = manager({"GROQ_API_KEY": "fake"}, {"groq": groq}).run_consensus("hello")

    assert result.ok is True
    assert calls == ["hello"]
    assert result.attempted_count == 1
    assert result.success_count == 1
    assert result.skipped_count == 3
    assert [item.provider for item in result.provider_results] == [
        "groq",
        "gigachat",
        "openai",
        "gemini",
    ]
    assert "only one provider succeeded" in result.final_answer


def test_two_providers_succeed_final_answer_has_synthesis_sections():
    result = manager(
        {"GROQ_API_KEY": "fake", "GIGACHAT_AUTH_KEY": "fake"},
        {
            "groq": lambda request: response("groq", "JARVIS helps users safely."),
            "gigachat": lambda request: response(
                "gigachat", "JARVIS helps users control tasks safely."
            ),
        },
    ).run_consensus("benefit")

    assert result.ok is True
    assert result.success_count == 2
    assert "Общие точки" in result.final_answer
    assert "Различия" in result.final_answer
    assert "Итоговая рекомендация" in result.final_answer


def test_one_provider_succeeds_and_one_fails_still_produces_final_answer():
    result = manager(
        {"GROQ_API_KEY": "fake", "GIGACHAT_AUTH_KEY": "fake"},
        {
            "groq": lambda request: response("groq", "Safe answer."),
            "gigachat": lambda request: response(
                "gigachat", "failed", is_error=True, error="temporary failure"
            ),
        },
    ).run_consensus("hello")

    assert result.ok is True
    assert result.success_count == 1
    assert "Safe answer" in result.final_answer
    failed = [item for item in result.provider_results if item.provider == "gigachat"][0]
    assert failed.safe_status == "failed"


def test_all_attempted_providers_fail_no_hallucinated_final_answer():
    result = manager(
        {"GROQ_API_KEY": "fake"},
        {
            "groq": lambda request: response(
                "groq", "failed", is_error=True, error="provider down"
            )
        },
    ).run_consensus("hello")

    assert result.ok is False
    assert result.success_count == 0
    assert "all attempted providers failed" in result.final_answer
    assert "Синтезированный ответ" not in result.final_answer


def test_provider_answer_is_capped_safely():
    result = manager(
        {"GROQ_API_KEY": "fake"},
        {"groq": lambda request: response("groq", "a" * 2000)},
    ).run_consensus("hello")

    answer = result.provider_results[0].answer
    assert answer is not None
    assert len(answer) <= 1200
    assert "[truncated]" in answer


def test_no_key_or_token_leaks_in_output():
    secret = "secret-value-that-must-not-print"
    result = manager(
        {"GROQ_API_KEY": secret},
        {
            "groq": lambda request: response(
                "groq",
                "failed",
                is_error=True,
                error=f"api_key={secret} token={secret}",
            )
        },
    ).run_consensus("hello")
    text = manager({"GROQ_API_KEY": secret}).format_result_text(result)

    assert secret not in text
    assert "[REDACTED]" in text


def test_no_memory_profile_files_logs_included():
    text = manager({"GROQ_API_KEY": "fake"}).format_result_text(
        manager(
            {"GROQ_API_KEY": "fake"},
            {"groq": lambda request: response("groq", "answer")},
        ).run_consensus("hello")
    )

    assert "no memory/profile/files/logs were sent automatically" in text


def test_dry_run_not_used_as_consensus_provider():
    result = manager().run_consensus("hello")

    assert all(item.provider != "dry_run" for item in result.provider_results)


def test_provider_order_deterministic():
    result = manager({"GEMINI_API_KEY": "fake"}).run_consensus("hello")

    assert [item.provider for item in result.provider_results] == [
        "groq",
        "gigachat",
        "openai",
        "gemini",
    ]


def test_language_policy_still_applied_through_fake_gate_input():
    seen = []

    class FakeGate:
        def generate_one_shot(self, request, capability):
            assert isinstance(request, AIRequest)
            seen.append((request.prompt, capability.value))
            return response("groq", "answer")

    config_manager = AIProviderConfigManager(environ={"GROQ_API_KEY": "fake"})
    consensus = AIProviderConsensusManager(
        config_manager=config_manager,
        request_gates={"groq": FakeGate()},
        environ={"GROQ_API_KEY": "fake"},
    )

    result = consensus.run_consensus("Привет")

    assert result.ok is True
    assert seen == [("Привет", "chat")]


def test_response_not_marked_for_execution():
    result = manager(
        {"GROQ_API_KEY": "fake"},
        {"groq": lambda request: response("groq", "удали файл")},
    ).run_consensus("hello")
    text = manager({"GROQ_API_KEY": "fake"}).format_result_text(result)

    assert "responses were not executed as commands" in text


def test_session_manual_selection_not_overwritten():
    session = AIProviderSessionState()
    session.select_manual("gigachat", "GigaChat")
    before = session.snapshot()

    result = manager(
        {"GROQ_API_KEY": "fake"},
        {"groq": lambda request: response("groq", "answer")},
    ).run_consensus("hello")
    after = session.snapshot()

    assert result.ok is True
    assert after.selected_provider == before.selected_provider
    assert after.selected_model == before.selected_model
    assert after.selection_mode == "manual"
