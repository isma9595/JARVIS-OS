from security import ApiKeyManager, MemorySecureKeyBackend, SecureKeyStore


SECRET = "dummy-test-key-for-storage-only"


def build_manager(environ=None):
    return ApiKeyManager(
        SecureKeyStore(MemorySecureKeyBackend()),
        environ={} if environ is None else environ,
    )


def test_status_text_is_safe():
    manager = build_manager()

    text = manager.status_text_ru()

    assert "secure key storage foundation: yes" in text
    assert "backend: memory-test" in text
    assert (
        "provider real requests can use SecureProviderRuntime credential resolution when explicitly invoked"
        in text
    )
    assert "no keys printed" in text
    assert "no network" in text


def test_list_text_shows_supported_providers_without_values():
    manager = build_manager({"GROQ_API_KEY": SECRET})

    text = manager.list_text_ru()

    assert "openai" in text
    assert "gemini" in text
    assert "groq" in text
    assert "gigachat" in text
    assert "PRESENT" in text
    assert "MISSING" in text
    assert SECRET not in text


def test_import_from_missing_env_refuses_safely():
    manager = build_manager()

    text = manager.import_from_env("groq")

    assert "stored: no" in text
    assert "env: MISSING" in text
    assert "no key value printed" in text


def test_import_from_env_stores_without_printing_value():
    manager = build_manager({"GROQ_API_KEY": SECRET})

    text = manager.import_from_env("groq")
    listing = manager.list_text_ru()

    assert "stored: yes" in text
    assert "env: PRESENT" in text
    assert manager.secure_key_store.has_secret("groq") is True
    assert SECRET not in text
    assert SECRET not in listing
    assert "***only" in listing


def test_delete_provider_key_works_without_printing_value():
    manager = build_manager({"GROQ_API_KEY": SECRET})
    manager.import_from_env("groq")

    text = manager.delete_provider_key("groq")

    assert "deleted: yes" in text
    assert SECRET not in text
    assert manager.secure_key_store.has_secret("groq") is False


def test_unsupported_provider_safe_refusal():
    manager = build_manager()

    text = manager.import_from_env("unknown")

    assert "supported: no" in text
    assert "openai, gemini, groq, gigachat" in text
    assert "no key value printed" in text


def test_help_text_warns_not_to_paste_keys_and_no_network():
    manager = build_manager()

    text = manager.safe_help_text_ru()

    assert "do not paste real API keys" in text
    assert "commands do not accept raw key text" in text
    assert "no provider validation or network request" in text
