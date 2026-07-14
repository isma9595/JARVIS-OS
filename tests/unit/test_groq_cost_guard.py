from ai import GroqRequestCostGuard, GroqRequestGuardConfig


def test_default_model_resolves_safely():
    guard = GroqRequestCostGuard(environ={})

    result = guard.guard_request("hello")

    assert result.allowed is True
    assert result.model == "llama-3.1-8b-instant"
    assert guard.model_source() == "default"


def test_groq_model_env_var_overrides_model():
    guard = GroqRequestCostGuard(environ={"GROQ_MODEL": "llama-3.3-70b-versatile"})

    result = guard.guard_request("hello")

    assert result.allowed is True
    assert result.model == "llama-3.3-70b-versatile"
    assert guard.model_source() == "GROQ_MODEL"


def test_invalid_model_rejected():
    too_long = "m" * 121
    for model in (
        "",
        "bad model",
        "../model",
        "bad\\model",
        "gsk_secret_value",
        "sk-secret-value",
        "abcdefghijklmnopqrstuvwxyzABCDEFGH123456",
        too_long,
    ):
        guard = GroqRequestCostGuard(environ={"GROQ_MODEL": model})

        result = guard.guard_request("hello")

        assert result.allowed is False
        assert "model" in result.safe_message.lower()


def test_slash_containing_safe_model_id_is_accepted():
    guard = GroqRequestCostGuard(environ={"GROQ_MODEL": "provider/model-id"})

    result = guard.guard_request("hello")

    assert result.allowed is True
    assert result.model == "provider/model-id"


def test_prompt_empty_rejected():
    result = GroqRequestCostGuard(environ={}).guard_request(" ")

    assert result.allowed is False
    assert result.safe_message == "AI prompt is empty."


def test_prompt_over_max_chars_rejected():
    guard = GroqRequestCostGuard(
        GroqRequestGuardConfig(max_prompt_chars=5),
        environ={},
    )

    result = guard.guard_request("123456")

    assert result.allowed is False
    assert "limit is 5" in result.safe_message


def test_prompt_at_limit_accepted():
    guard = GroqRequestCostGuard(
        GroqRequestGuardConfig(max_prompt_chars=5),
        environ={},
    )

    result = guard.guard_request("12345")

    assert result.allowed is True


def test_max_output_tokens_bounded():
    guard = GroqRequestCostGuard(environ={})

    assert guard.guard_request("hello").max_output_tokens == 128
    assert guard.guard_request("hello", max_output_tokens=16).allowed is True
    assert guard.guard_request("hello", max_output_tokens=15).allowed is False
    too_high = guard.guard_request("hello", max_output_tokens=513)
    assert too_high.allowed is False
    assert "hard cap 512" in too_high.safe_message


def test_warning_mentions_free_developer_quota_rate_limits_without_key_leakage():
    secret = "fake-groq-key-that-must-not-appear"
    guard = GroqRequestCostGuard(environ={"GROQ_API_KEY": secret})

    result = guard.guard_request("hello")

    assert result.warning_text is not None
    assert "free/developer" in result.warning_text
    assert "quota" in result.warning_text
    assert "rate limit" in result.warning_text.lower()
    assert secret not in result.warning_text


def test_invalid_model_value_is_not_printed_in_status_or_model_text():
    secret_like_model = "gsk_secret_that_must_not_appear"
    guard = GroqRequestCostGuard(environ={"GROQ_MODEL": secret_like_model})

    assert secret_like_model not in guard.status_text_ru()
    assert secret_like_model not in guard.model_text_ru()
    assert "<invalid model value>" in guard.status_text_ru()
