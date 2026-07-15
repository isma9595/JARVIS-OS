from ai import SecureProviderRuntime
from security import ApiKeyManager, MemorySecureKeyBackend, SecureKeyStore


SECRET = "dummy-test-runtime-secret"


class CountingStore(SecureKeyStore):
    def __init__(self):
        super().__init__(MemorySecureKeyBackend())
        self.get_secret_calls = 0

    def get_secret(self, provider, secret_name="api_key"):
        self.get_secret_calls += 1
        return super().get_secret(provider, secret_name)


def build_runtime(environ=None, store=None):
    manager = ApiKeyManager(
        store or SecureKeyStore(MemorySecureKeyBackend()),
        environ={} if environ is None else environ,
    )
    return SecureProviderRuntime(api_key_manager=manager, environ=manager.environ), manager


def test_status_works_with_no_stored_keys_and_no_env():
    runtime, _ = build_runtime()

    status = runtime.credential_status("groq")
    text = runtime.status_text_ru()

    assert status.source == "missing"
    assert status.can_attempt_real_request is False
    assert "secure provider runtime: yes" in text
    assert "no network" in text
    assert "no provider call" in text


def test_status_does_not_include_secrets_or_decrypt_for_status():
    store = CountingStore()
    runtime, manager = build_runtime({"GROQ_API_KEY": SECRET}, store)
    manager.secure_key_store.set_secret("groq", SECRET)

    text = runtime.status_text_ru()

    assert SECRET not in text
    assert "source: secure_store" in text
    assert store.get_secret_calls == 0


def test_secure_store_preferred_over_env_when_both_exist():
    runtime, manager = build_runtime({"GROQ_API_KEY": "env-secret"})
    manager.secure_key_store.set_secret("groq", "stored-secret")

    credential = runtime.resolve_credential("groq")

    assert credential.source == "secure_store"
    assert credential.value == "stored-secret"


def test_env_fallback_works_when_secure_store_missing():
    runtime, _ = build_runtime({"GROQ_API_KEY": SECRET})

    credential = runtime.resolve_credential("groq")

    assert credential.source == "env"
    assert credential.value == SECRET
    assert credential.safe_to_use is True


def test_unsupported_provider_safe():
    runtime, _ = build_runtime()

    status = runtime.credential_status("unknown")
    credential = runtime.resolve_credential("unknown")

    assert status.supported is False
    assert status.source == "unsupported"
    assert credential.safe_to_use is False


def test_dry_run_and_ollama_no_key_behavior():
    runtime, _ = build_runtime()

    for provider in ("dry_run", "ollama"):
        status = runtime.credential_status(provider)
        credential = runtime.resolve_credential(provider)
        assert status.source == "local/no_key"
        assert status.can_attempt_real_request is True
        assert credential.safe_to_use is True


def test_resolve_credential_does_not_leak_in_repr_or_to_dict():
    runtime, _ = build_runtime({"GROQ_API_KEY": SECRET})

    credential = runtime.resolve_credential("groq")

    assert SECRET not in repr(credential)
    assert credential.to_dict()["value"] is None
    assert SECRET not in str(credential.to_dict())


def test_missing_credential_safe_to_use_false():
    runtime, _ = build_runtime()

    credential = runtime.resolve_credential("openai")

    assert credential.safe_to_use is False
    assert credential.value is None
    assert credential.source == "missing"


def test_no_network_provider_call_during_status(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("status must not use network")

    monkeypatch.setattr("urllib.request.urlopen", fail)
    runtime, _ = build_runtime({"OPENAI_API_KEY": SECRET})

    text = runtime.status_text_ru()

    assert "no network" in text
    assert "no provider call" in text
