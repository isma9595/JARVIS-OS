import pytest

from security import (
    MemorySecureKeyBackend,
    SecureKeyStore,
    UnavailableSecureKeyBackend,
)


SECRET = "dummy-test-key-for-storage-only"


def test_memory_store_status_is_safe_for_tests():
    store = SecureKeyStore(MemorySecureKeyBackend())

    status = store.status()

    assert status.available is True
    assert status.backend_name == "memory-test"
    assert status.persistent is False
    assert status.encrypted_at_rest is True
    assert status.safe_to_store is True


def test_set_get_list_and_delete_secret_without_exposing_raw_value():
    backend = MemorySecureKeyBackend()
    store = SecureKeyStore(backend)

    store.set_secret("groq", SECRET)

    assert store.has_secret("groq") is True
    assert store.get_secret("groq") == SECRET
    records = store.list_records()
    assert len(records) == 1
    assert records[0].provider == "groq"
    assert records[0].present is True
    assert records[0].masked_hint.endswith(SECRET[-4:])
    assert records[0].masked_hint != SECRET
    assert SECRET not in str(records)
    assert SECRET not in str(backend.read_entries())

    assert store.delete_secret("groq") is True
    assert store.delete_secret("groq") is False
    assert store.has_secret("groq") is False


def test_masked_hint_never_equals_full_short_secret():
    store = SecureKeyStore(MemorySecureKeyBackend())

    store.set_secret("openai", "abcd")
    record = store.list_records()[0]

    assert record.masked_hint == "***abcd"
    assert record.masked_hint != "abcd"


def test_unavailable_backend_refuses_storage():
    store = SecureKeyStore(UnavailableSecureKeyBackend("DPAPI unavailable"))

    status = store.status()

    assert status.safe_to_store is False
    with pytest.raises(RuntimeError):
        store.set_secret("groq", SECRET)
    assert store.has_secret("groq") is False


def test_no_plain_text_output_in_records_or_backend_entries():
    backend = MemorySecureKeyBackend()
    store = SecureKeyStore(backend)

    store.set_secret("gemini", SECRET)

    combined = str(store.list_records()) + str(backend.read_entries())
    assert SECRET not in combined
    assert "dummy-test-key" not in combined
