from ai import AIProviderLanguagePolicy


def test_default_russian_policy_applies_to_plain_prompt():
    result = AIProviderLanguagePolicy().apply("hello")

    assert result.applied is True
    assert result.language == "ru"
    assert result.reason == "default_russian"
    assert "Отвечай на русском языке" in result.policy_prefix
    assert result.prompt.startswith(result.policy_prefix)


def test_prompt_text_is_preserved_exactly_after_prefix():
    prompt = "Line 1\n  Line 2 with spaces  "
    result = AIProviderLanguagePolicy().apply(prompt)

    assert result.prompt == result.policy_prefix + prompt


def test_explicit_english_request_is_respected():
    result = AIProviderLanguagePolicy().apply("Answer in English: hello")

    assert result.language == "en"
    assert result.reason == "explicit_language_request"
    assert "Отвечай на русском языке" not in result.policy_prefix
    assert "Соблюдай эту просьбу" in result.policy_prefix


def test_explicit_russian_request_remains_russian():
    result = AIProviderLanguagePolicy().apply("Ответь на русском: hello")

    assert result.language == "ru"
    assert "Отвечай на русском языке" in result.policy_prefix


def test_explicit_chechen_request_is_respected():
    result = AIProviderLanguagePolicy().apply("Ответь на чеченском: привет")

    assert result.language == "ce"
    assert "Отвечай на русском языке" not in result.policy_prefix


def test_explicit_arabic_request_is_respected():
    result = AIProviderLanguagePolicy().apply("Ответь на арабском: привет")

    assert result.language == "ar"
    assert "Отвечай на русском языке" not in result.policy_prefix


def test_translation_to_english_is_respected():
    result = AIProviderLanguagePolicy().apply("Переведи это на английский: привет")

    assert result.language == "en"
    assert "Отвечай на русском языке" not in result.policy_prefix


def test_translation_to_russian_is_allowed():
    result = AIProviderLanguagePolicy().apply("Translate to Russian: hello")

    assert result.language == "ru"
    assert "Отвечай на русском языке" in result.policy_prefix


def test_code_prompt_keeps_code_instruction_and_applies_russian_explanation_rule():
    prompt = "Write Python code: print('hello')"
    result = AIProviderLanguagePolicy().apply(prompt)

    assert "Код, команды, имена файлов и цитаты сохраняй без изменения синтаксиса." in result.policy_prefix
    assert result.prompt.endswith(prompt)


def test_quoted_english_text_is_preserved():
    prompt = 'Explain the quote "Hello world"'
    result = AIProviderLanguagePolicy().apply(prompt)

    assert result.prompt.endswith(prompt)
    assert '"Hello world"' in result.prompt


def test_already_prefixed_prompt_is_not_double_prefixed():
    policy = AIProviderLanguagePolicy()
    first = policy.apply("hello")
    second = policy.apply(first.prompt)

    assert second.applied is False
    assert second.reason == "already_prefixed"
    assert second.prompt == first.prompt
    assert second.prompt.count("Системная инструкция JARVIS:") == 1


def test_no_memory_profile_files_logs_or_secrets_in_policy_prefix():
    result = AIProviderLanguagePolicy().apply("hello")
    prefix = result.policy_prefix

    assert "memory/profile/files/logs" not in prefix
    assert "API_KEY" not in prefix
    assert "token" not in prefix.lower()
    assert "secret" not in prefix.lower()
    assert "памяти или профилю" in prefix
    assert "файлам" in prefix


def test_status_text_safe_and_no_network():
    text = AIProviderLanguagePolicy().status_text_ru()

    assert "enabled: yes" in text
    assert "default language: Russian / ru" in text
    assert "external one-shot providers" in text
    assert "dry_run: unchanged" in text
    assert "explicit language requests respected" in text
    assert "translation requests respected" in text
    assert "memory/profile/files/logs not sent" in text
    assert "responses not executed as commands" in text
    assert "network: not called" in text
