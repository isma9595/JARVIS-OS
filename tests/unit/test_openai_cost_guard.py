from ai import OpenAIRequestCostGuard, OpenAIRequestGuardConfig


def test_default_model_resolves_safely():
    guard = OpenAIRequestCostGuard(environ={})

    result = guard.guard_request("hello")

    assert result.allowed is True
    assert result.model == "gpt-5.6"
    assert guard.model_source() == "default"


def test_openai_model_env_var_overrides_model():
    guard = OpenAIRequestCostGuard(environ={"OPENAI_MODEL": "gpt-5-mini"})

    result = guard.guard_request("hello")

    assert result.allowed is True
    assert result.model == "gpt-5-mini"
    assert guard.model_source() == "OPENAI_MODEL"


def test_invalid_model_rejected():
    too_long = "m" * 81
    for model in ("", "bad model", "bad/model", "bad\\model", "sk-secret", too_long):
        guard = OpenAIRequestCostGuard(environ={"OPENAI_MODEL": model})

        result = guard.guard_request("hello")

        assert result.allowed is False
        assert "model" in result.safe_message.lower()


def test_prompt_empty_rejected():
    result = OpenAIRequestCostGuard(environ={}).guard_request(" ")

    assert result.allowed is False
    assert result.safe_message == "AI prompt is empty."


def test_prompt_over_max_chars_rejected():
    guard = OpenAIRequestCostGuard(
        OpenAIRequestGuardConfig(max_prompt_chars=5),
        environ={},
    )

    result = guard.guard_request("123456")

    assert result.allowed is False
    assert "limit is 5" in result.safe_message


def test_prompt_at_limit_accepted():
    guard = OpenAIRequestCostGuard(
        OpenAIRequestGuardConfig(max_prompt_chars=5),
        environ={},
    )

    result = guard.guard_request("12345")

    assert result.allowed is True


def test_max_output_tokens_default_is_128():
    result = OpenAIRequestCostGuard(environ={}).guard_request("hello")

    assert result.max_output_tokens == 128


def test_max_output_tokens_above_hard_cap_rejected():
    result = OpenAIRequestCostGuard(environ={}).guard_request(
        "hello",
        max_output_tokens=513,
    )

    assert result.allowed is False
    assert "hard cap 512" in result.safe_message


def test_warning_mentions_possible_account_credits_or_limits_without_key():
    secret = "sk-test-secret-that-must-not-appear"
    guard = OpenAIRequestCostGuard(environ={"OPENAI_API_KEY": secret})

    result = guard.guard_request("hello")

    assert result.warning_text is not None
    assert "лимит аккаунта" in result.warning_text
    assert "может списать средства" in result.warning_text
    assert secret not in result.warning_text


def test_invalid_model_value_is_not_printed_in_status_or_model_text():
    secret_like_model = "sk-secret-that-must-not-appear"
    guard = OpenAIRequestCostGuard(environ={"OPENAI_MODEL": secret_like_model})

    assert secret_like_model not in guard.status_text_ru()
    assert secret_like_model not in guard.model_text_ru()
    assert "<invalid model value>" in guard.status_text_ru()
