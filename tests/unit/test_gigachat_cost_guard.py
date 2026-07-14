from ai import GigaChatRequestCostGuard


def test_default_model_resolves():
    guard = GigaChatRequestCostGuard(environ={})

    assert guard.resolve_model() == "GigaChat"


def test_gigachat_model_override_resolves():
    guard = GigaChatRequestCostGuard(environ={"GIGACHAT_MODEL": "GigaChat-Pro"})

    assert guard.resolve_model() == "GigaChat-Pro"


def test_valid_model_examples_accepted():
    guard = GigaChatRequestCostGuard(environ={})

    for model in ("GigaChat", "GigaChat-2", "GigaChat-Pro", "GigaChat-2-Pro"):
        assert guard.validate_model(model) is None


def test_invalid_models_rejected():
    guard = GigaChatRequestCostGuard(environ={})

    for model in (
        "",
        "bad model",
        "../GigaChat",
        r"bad\model",
        "sk-key-looking-value",
        "a" * 121,
        "abcdefghijklmnopqrstuvwxyzABCDEFGH123456",
    ):
        assert guard.validate_model(model) is not None


def test_prompt_validation():
    guard = GigaChatRequestCostGuard(environ={})

    assert guard.guard_request("").allowed is False
    assert guard.guard_request("x" * 1201).allowed is False
    assert guard.guard_request("x" * 1200).allowed is True


def test_max_output_tokens_bounded():
    guard = GigaChatRequestCostGuard(environ={})

    assert guard.guard_request("hello", 16).allowed is True
    assert guard.guard_request("hello", 15).allowed is False
    assert guard.guard_request("hello", 513).allowed is False
    assert guard.guard_request("hello", "bad").allowed is False


def test_warning_mentions_quota_one_shot_and_no_secret_leakage():
    secret = "gigachat-secret-that-must-not-leak"
    guard = GigaChatRequestCostGuard(environ={"GIGACHAT_AUTH_KEY": secret})
    result = guard.guard_request("hello")

    assert result.allowed is True
    assert "free/paid quota" in result.warning_text
    assert "one-shot" in result.warning_text
    assert "token" in result.warning_text
    assert secret not in result.warning_text
