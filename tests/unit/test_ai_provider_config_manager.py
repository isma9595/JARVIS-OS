from ai import AIProviderConfigManager, AIProviderKeyStatus


def test_manager_formats_russian_config_status():
    text = AIProviderConfigManager(environ={}).format_status_ru()

    assert "Статус AI конфигурации и ключей" in text
    assert "dry_run" in text
    assert "groq" in text
    assert "gemini" in text
    assert "openai" in text
    assert "Сеть не используется" in text


def test_manager_formats_provider_list():
    text = AIProviderConfigManager(environ={}).format_provider_list_ru()

    assert "Конфигурация AI провайдеров" in text
    assert "GROQ_API_KEY" in text
    assert "GEMINI_API_KEY" in text
    assert "OPENAI_API_KEY" in text
    assert "выключен" in text


def test_key_safety_text_mentions_env_vars_no_commits_and_no_printing_keys():
    text = AIProviderConfigManager(environ={}).format_key_safety_help_ru()

    assert "переменные окружения" in text
    assert "Не коммитьте секреты" in text
    assert "не значение" in text
    assert "сеть не используется" in text.lower()


def test_check_specific_provider_key_status_missing():
    text = AIProviderConfigManager(environ={}).check_provider_key_text_ru("openai")

    assert "OPENAI_API_KEY" in text
    assert "MISSING" in text
    assert "значение ключа не отображается" in text.lower()
    assert "провайдер не вызывается" in text


def test_check_specific_provider_key_status_present_without_value():
    secret = "very-secret-groq-value"
    manager = AIProviderConfigManager(environ={"GROQ_API_KEY": secret})
    status = manager.status_for("groq")
    text = manager.check_provider_key_text_ru("groq")

    assert status.key_status == AIProviderKeyStatus.PRESENT
    assert "PRESENT" in text
    assert secret not in text
    assert "значение не отображается" in text


def test_unknown_provider_returns_safe_error():
    text = AIProviderConfigManager(environ={}).check_provider_key_text_ru("unknown")

    assert "не найден" in text
    assert "Ключи не читаются" in text
    assert "сеть не используется" in text


def test_no_actual_key_value_in_output_when_env_set():
    secret = "gemini-secret-that-must-stay-hidden"
    manager = AIProviderConfigManager(environ={"GEMINI_API_KEY": secret})

    combined = "\n".join(
        [
            manager.format_status_ru(),
            manager.format_provider_list_ru(),
            manager.check_provider_key_text_ru("gemini"),
        ]
    )

    assert secret not in combined
    assert "GEMINI_API_KEY" in combined
    assert "PRESENT" in combined


def test_gemini_status_safe_with_default_model_and_key_states():
    missing = AIProviderConfigManager(environ={})
    present_secret = "gemini-secret-that-must-stay-hidden"
    present = AIProviderConfigManager(environ={"GEMINI_API_KEY": present_secret})

    assert missing.status_for("gemini").key_status == AIProviderKeyStatus.MISSING
    assert present.status_for("gemini").key_status == AIProviderKeyStatus.PRESENT
    text = "\n".join(
        [
            present.format_status_ru(),
            present.format_provider_list_ru(),
            present.check_provider_key_text_ru("gemini"),
        ]
    )
    assert "gemini-2.5-flash-lite" in text
    assert "GEMINI_API_KEY" in text
    assert present_secret not in text


def test_check_openai_key_status_present_without_value():
    secret = "openai-secret-that-must-stay-hidden"
    manager = AIProviderConfigManager(environ={"OPENAI_API_KEY": secret})
    status = manager.status_for("openai")
    text = manager.check_provider_key_text_ru("openai")

    assert status.key_status == AIProviderKeyStatus.PRESENT
    assert "PRESENT" in text
    assert "OPENAI_API_KEY" in text
    assert secret not in text


def test_groq_status_safe_with_default_model_and_key_states():
    missing = AIProviderConfigManager(environ={})
    present_secret = "groq-secret-that-must-stay-hidden"
    present = AIProviderConfigManager(environ={"GROQ_API_KEY": present_secret})

    assert missing.status_for("groq").key_status == AIProviderKeyStatus.MISSING
    assert present.status_for("groq").key_status == AIProviderKeyStatus.PRESENT
    text = "\n".join(
        [
            present.format_status_ru(),
            present.format_provider_list_ru(),
            present.check_provider_key_text_ru("groq"),
        ]
    )
    assert "llama-3.1-8b-instant" in text
    assert "GROQ_API_KEY" in text
    assert present_secret not in text
