import json
from pathlib import Path

import pytest

from ai import (
    AIProviderConfig,
    AIProviderConfigManager,
    AIProviderKeyStatus,
    AIProviderRuntimeState,
)


def test_default_configs_include_dry_run_groq_gemini():
    configs = {config.name: config for config in AIProviderConfigManager.default_configs()}

    assert set(configs) == {"dry_run", "groq", "gemini"}
    assert configs["dry_run"].enabled is True
    assert configs["groq"].enabled is False
    assert configs["gemini"].enabled is False


def test_dry_run_key_status_is_not_required():
    status = AIProviderConfigManager(environ={}).status_for("dry_run")

    assert status.key_status == AIProviderKeyStatus.NOT_REQUIRED
    assert status.runtime_state == AIProviderRuntimeState.DRY_RUN_ONLY


def test_missing_env_vars_produce_missing():
    manager = AIProviderConfigManager(environ={})

    assert manager.status_for("groq").key_status == AIProviderKeyStatus.MISSING
    assert manager.status_for("gemini").key_status == AIProviderKeyStatus.MISSING


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
    text = AIProviderConfigManager(environ={"GEMINI_API_KEY": secret}).format_status_ru()

    assert secret not in text
    assert "GEMINI_API_KEY" in text


def test_example_config_does_not_contain_secrets():
    path = Path("config/ai_providers.example.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    text = path.read_text(encoding="utf-8")

    assert "sk-" not in text
    assert "secret" not in text.lower().replace("secrets", "")
    assert data["providers"][0]["api_key_env_var"] == "GROQ_API_KEY"
    assert data["providers"][1]["api_key_env_var"] == "GEMINI_API_KEY"


def test_config_layer_has_no_network_dependency():
    manager = AIProviderConfigManager(environ={})

    statuses = manager.statuses()

    assert [status.name for status in statuses] == ["dry_run", "groq", "gemini"]
