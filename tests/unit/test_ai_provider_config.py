import json
from pathlib import Path

import pytest

from ai import (
    AIProviderConfig,
    AIProviderConfigManager,
    AIProviderKeyStatus,
    AIProviderRuntimeState,
)


def test_default_configs_include_dry_run_external_and_ollama():
    configs = {config.name: config for config in AIProviderConfigManager.default_configs()}

    assert set(configs) == {"dry_run", "groq", "gigachat", "gemini", "openai", "ollama"}
    assert configs["dry_run"].enabled is True
    assert configs["groq"].enabled is False
    assert configs["gigachat"].enabled is False
    assert configs["gemini"].enabled is False
    assert configs["openai"].enabled is False
    assert configs["ollama"].enabled is False
    assert configs["groq"].default_model == "llama-3.1-8b-instant"
    assert configs["groq"].api_key_env_var == "GROQ_API_KEY"
    assert configs["gigachat"].default_model == "GigaChat"
    assert configs["gigachat"].api_key_env_var == "GIGACHAT_AUTH_KEY"
    assert configs["gemini"].default_model == "gemini-2.5-flash-lite"
    assert configs["gemini"].api_key_env_var == "GEMINI_API_KEY"
    assert configs["openai"].api_key_env_var == "OPENAI_API_KEY"
    assert configs["ollama"].default_model == "qwen2.5:1.5b"
    assert configs["ollama"].api_key_env_var is None
    assert configs["ollama"].safety_level == "local_only"


def test_dry_run_key_status_is_not_required():
    status = AIProviderConfigManager(environ={}).status_for("dry_run")

    assert status.key_status == AIProviderKeyStatus.NOT_REQUIRED
    assert status.runtime_state == AIProviderRuntimeState.DRY_RUN_ONLY


def test_ollama_key_status_is_not_required_and_disabled_by_default():
    status = AIProviderConfigManager(environ={}).status_for("ollama")

    assert status.key_status == AIProviderKeyStatus.NOT_REQUIRED
    assert status.runtime_state == AIProviderRuntimeState.DISABLED
    assert status.default_model == "qwen2.5:1.5b"


def test_missing_env_vars_produce_missing():
    manager = AIProviderConfigManager(environ={})

    assert manager.status_for("groq").key_status == AIProviderKeyStatus.MISSING
    assert manager.status_for("gigachat").key_status == AIProviderKeyStatus.MISSING
    assert manager.status_for("gemini").key_status == AIProviderKeyStatus.MISSING
    assert manager.status_for("openai").key_status == AIProviderKeyStatus.MISSING


def test_present_env_var_produces_present_but_value_is_not_shown():
    secret = "sk-test-secret-value-that-must-not-leak"
    manager = AIProviderConfigManager(environ={"GROQ_API_KEY": secret})
    status = manager.status_for("groq")
    text = manager.format_status_ru()

    assert status.key_status == AIProviderKeyStatus.PRESENT
    assert "PRESENT" in text
    assert secret not in text
    assert "значение не отображается" in text


def test_api_key_env_var_rejects_obvious_secret_values():
    with pytest.raises(ValueError):
        AIProviderConfig(
            name="bad",
            provider_type="external",
            api_key_env_var="sk-obvious-secret",
        )


def test_api_key_env_var_rejects_long_token_like_values():
    with pytest.raises(ValueError):
        AIProviderConfig(
            name="bad",
            provider_type="external",
            api_key_env_var="abcdefghijklmnopqrstuvwxyzABCDEFGH123456",
        )


def test_status_text_does_not_contain_env_var_value():
    secret = "super-secret-key-value"
    manager = AIProviderConfigManager(environ={"GEMINI_API_KEY": secret})
    text = "\n".join(
        [
            manager.format_status_ru(),
            manager.format_provider_list_ru(),
            manager.check_provider_key_text_ru("gemini"),
        ]
    )

    assert secret not in text
    assert "GEMINI_API_KEY" in text
    assert "PRESENT" in text


def test_openai_env_var_value_never_appears_in_status_text():
    secret = "openai-secret-that-must-not-print"
    manager = AIProviderConfigManager(environ={"OPENAI_API_KEY": secret})
    status = manager.status_for("openai")
    text = "\n".join(
        [
            manager.format_status_ru(),
            manager.format_provider_list_ru(),
            manager.check_provider_key_text_ru("openai"),
        ]
    )

    assert status.key_status == AIProviderKeyStatus.PRESENT
    assert "OPENAI_API_KEY" in text
    assert "PRESENT" in text
    assert secret not in text


def test_groq_env_var_value_never_appears_in_status_text():
    secret = "groq-secret-that-must-not-print"
    manager = AIProviderConfigManager(environ={"GROQ_API_KEY": secret})
    status = manager.status_for("groq")
    text = "\n".join(
        [
            manager.format_status_ru(),
            manager.format_provider_list_ru(),
            manager.check_provider_key_text_ru("groq"),
        ]
    )

    assert status.key_status == AIProviderKeyStatus.PRESENT
    assert status.default_model == "llama-3.1-8b-instant"
    assert "GROQ_API_KEY" in text
    assert "PRESENT" in text
    assert secret not in text


def test_gigachat_env_var_value_never_appears_in_status_text():
    secret = "gigachat-secret-that-must-not-print"
    manager = AIProviderConfigManager(environ={"GIGACHAT_AUTH_KEY": secret})
    status = manager.status_for("gigachat")
    text = "\n".join(
        [
            manager.format_status_ru(),
            manager.format_provider_list_ru(),
            manager.check_provider_key_text_ru("gigachat"),
        ]
    )

    assert status.key_status == AIProviderKeyStatus.PRESENT
    assert status.default_model == "GigaChat"
    assert "GIGACHAT_AUTH_KEY" in text
    assert "PRESENT" in text
    assert secret not in text


def test_example_config_does_not_contain_secrets():
    path = Path("config/ai_providers.example.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    text = path.read_text(encoding="utf-8")

    assert "sk-" not in text
    assert "secret" not in text.lower().replace("secrets", "").replace("secret.", "")
    env_vars = [provider["api_key_env_var"] for provider in data["providers"]]
    assert env_vars == [
        "GROQ_API_KEY",
        "GIGACHAT_AUTH_KEY",
        "GEMINI_API_KEY",
        "OPENAI_API_KEY",
        None,
    ]


def test_config_layer_has_no_network_dependency():
    manager = AIProviderConfigManager(environ={})

    statuses = manager.statuses()

    assert [status.name for status in statuses] == [
        "dry_run",
        "groq",
        "gigachat",
        "gemini",
        "openai",
        "ollama",
    ]
