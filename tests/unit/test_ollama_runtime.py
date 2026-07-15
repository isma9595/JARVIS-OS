import os

from ai.ollama_runtime import OllamaRuntime, OllamaRuntimeConfig


class FakeOllamaClient:
    def __init__(self, tags=None, error=None):
        self.tags = tags or {"models": [{"name": "qwen2.5:1.5b"}]}
        self.error = error
        self.calls = []

    def get_json(self, url, timeout):
        self.calls.append(("GET", url, timeout))
        if self.error:
            raise self.error
        return self.tags


def test_default_config_uses_localhost_and_default_model():
    config = OllamaRuntime.load_config({})

    assert config.base_url == "http://127.0.0.1:11434"
    assert config.model == "qwen2.5:1.5b"
    assert config.tags_timeout_seconds == 5
    assert config.request_timeout_seconds == 30


def test_base_url_accepts_localhost_127_and_ipv6_loopback():
    for url in (
        "http://localhost:11434",
        "http://127.0.0.1:11434",
        "http://[::1]:11434",
        "http://127.0.0.1:11434/api",
    ):
        ok, safe, error = OllamaRuntime.validate_base_url(url)

        assert ok is True
        assert safe.startswith("http://")
        assert error is None


def test_base_url_rejects_non_localhost_credentials_https_and_bad_paths():
    for url in (
        "https://localhost:11434",
        "http://example.com:11434",
        "http://192.168.1.20:11434",
        "http://user:pass@localhost:11434",
        "http://localhost:11434/../api",
    ):
        ok, _, error = OllamaRuntime.validate_base_url(url)

        assert ok is False
        assert error


def test_build_url_creates_safe_api_paths():
    runtime = OllamaRuntime(
        config=OllamaRuntimeConfig(
            base_url="http://127.0.0.1:11434",
            model="qwen2.5:1.5b",
            tags_timeout_seconds=5,
            request_timeout_seconds=30,
            source="test",
        )
    )

    assert runtime.build_url("/api/tags") == "http://127.0.0.1:11434/api/tags"
    assert runtime.build_url("/api/chat") == "http://127.0.0.1:11434/api/chat"


def test_list_models_handles_success():
    client = FakeOllamaClient(tags={"models": [{"name": "b"}, {"name": "a"}]})
    runtime = OllamaRuntime(http_client=client, environ={})

    ok, models, error = runtime.list_models()

    assert ok is True
    assert models == ("a", "b")
    assert error is None
    assert client.calls[0][1].endswith("/api/tags")


def test_list_models_handles_server_unavailable_safely():
    client = FakeOllamaClient(error=OSError("secret-token-value-that-must-not-print"))
    runtime = OllamaRuntime(http_client=client, environ={})

    ok, models, error = runtime.list_models()

    assert ok is False
    assert models == ()
    assert "unavailable" in error
    assert "secret-token" not in error


def test_status_does_not_print_secret_like_values(monkeypatch):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://evil.example.com:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5:1.5b")
    runtime = OllamaRuntime(environ=os.environ)

    status = runtime.status()

    assert status.ok is False
    assert "key" not in status.safe_message.lower()
    assert "token" not in status.safe_message.lower()
