from ai import AIContextPrivacyPolicy, AIContextSensitivity, AIContextTarget


def test_status_and_matrix_are_safe_no_network():
    policy = AIContextPrivacyPolicy()

    status = policy.status_text_ru()
    matrix = policy.matrix_text_ru()

    assert "enabled: yes" in status
    assert "deterministic preflight" in status
    assert "network: not called" in status
    assert "no prompts/responses stored to disk" in status
    assert "dry_run" in matrix
    assert "Ollama/local" in matrix
    assert "external providers" in matrix
    assert "external consensus" in matrix
    assert "network: not called" in matrix


def test_classification_rules_cover_supported_context_types():
    policy = AIContextPrivacyPolicy()

    assert policy.classify_text("ordinary weather question") == AIContextSensitivity.USER_TYPED_GENERAL
    assert policy.classify_text("это приватный файл, не отправляй в интернет") == AIContextSensitivity.PRIVATE_OR_PERSONAL
    assert policy.classify_text("my api key sk-test-1234567890secret") == AIContextSensitivity.SECRET_LIKE
    assert policy.classify_text(r"C:\Users\User\Desktop\secret.pdf") == AIContextSensitivity.FILE_PATH_REFERENCE
    assert policy.classify_text("содержимое файла ниже") == AIContextSensitivity.FILE_CONTENT
    assert policy.classify_text("моя память и профиль пользователя") == AIContextSensitivity.MEMORY_PROFILE
    assert policy.classify_text("debug log traceback") == AIContextSensitivity.LOG_OR_DEBUG
    assert policy.classify_text("скриншот экрана OCR") == AIContextSensitivity.SCREEN_OR_OCR
    assert policy.classify_text("запись микрофона аудио") == AIContextSensitivity.AUDIO_TRANSCRIPT


def test_redacted_preview_truncates_and_does_not_echo_secret():
    policy = AIContextPrivacyPolicy()
    secret = "sk-test-1234567890secret"

    preview = policy.redacted_preview("token " + secret + " " + ("a" * 300), limit=80)

    assert secret not in preview
    assert "[REDACTED]" in preview
    assert "[truncated]" in preview
    assert len(preview) <= 80


def test_dry_run_allows_all_without_network():
    policy = AIContextPrivacyPolicy()

    decision = policy.decide("password sk-test-1234567890secret", AIContextTarget.DRY_RUN)

    assert decision.allowed is True
    assert decision.network_called is False
    assert decision.target == "dry_run"


def test_ollama_allows_private_typed_but_blocks_secrets_and_raw_context():
    policy = AIContextPrivacyPolicy()

    private_decision = policy.decide("личные данные, не отправляй в интернет", AIContextTarget.LOCAL_OLLAMA)
    secret_decision = policy.decide("api key sk-test-1234567890secret", AIContextTarget.LOCAL_OLLAMA)
    screen_decision = policy.decide("скриншот экрана", AIContextTarget.LOCAL_OLLAMA)

    assert private_decision.allowed is True
    assert secret_decision.allowed is False
    assert screen_decision.allowed is False
    assert secret_decision.network_called is False


def test_external_and_consensus_block_sensitive_context():
    policy = AIContextPrivacyPolicy()

    for target in (AIContextTarget.EXTERNAL_PROVIDER, AIContextTarget.CONSENSUS_EXTERNAL):
        for text in (
            "конфиденциально паспорт",
            "api key sk-test-1234567890secret",
            r"C:\Users\User\Desktop\secret.pdf",
            "моя память",
            "debug log traceback",
            "скриншот экрана",
            "голосовая запись",
        ):
            decision = policy.decide(text, target)

            assert decision.allowed is False
            assert decision.should_block_external is True
            assert decision.network_called is False


def test_general_prompt_allowed_for_external_and_consensus():
    policy = AIContextPrivacyPolicy()

    assert policy.decide("обычный вопрос про погоду", AIContextTarget.EXTERNAL_PROVIDER).allowed is True
    assert policy.decide("ordinary general question", AIContextTarget.CONSENSUS_EXTERNAL).allowed is True


def test_check_text_redacts_secret_and_reports_all_targets():
    policy = AIContextPrivacyPolicy()
    secret = "sk-test-1234567890secret"

    text = policy.check_text_ru(f"мой api key {secret}")

    assert secret not in text
    assert "secret_like" in text
    assert "dry_run" in text
    assert "external_provider" in text
    assert "consensus_external" in text
    assert "network: not called" in text
