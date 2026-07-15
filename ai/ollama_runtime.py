"""Local-only Ollama runtime helpers.

This module only talks to localhost after URL validation. It never installs
Ollama, pulls models, stores prompts/responses, or uses API keys.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
import posixpath
import re
import socket
from urllib.parse import urlparse, urlunparse
import urllib.error
import urllib.request


_TOKEN_RE = re.compile(r"(api[_-]?key|token|auth[_-]?key)\s*[:=]\s*\S+", re.I)
_LONG_SECRET_RE = re.compile(r"\b[A-Za-z0-9._~+/=-]{32,}\b")


@dataclass(frozen=True)
class OllamaRuntimeConfig:
    base_url: str
    model: str
    tags_timeout_seconds: int
    request_timeout_seconds: int
    source: str


@dataclass(frozen=True)
class OllamaRuntimeStatus:
    ok: bool
    base_url: str
    model: str
    server_reachable: bool
    model_installed: bool | None
    installed_models: tuple[str, ...]
    safe_message: str


class UrllibOllamaHTTPClient:
    def get_json(self, url: str, timeout: int):
        request = urllib.request.Request(
            url,
            headers={"Accept": "application/json", "User-Agent": "JARVIS-OS/0.2"},
            method="GET",
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def post_json(self, url: str, payload: dict, timeout: int):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "JARVIS-OS/0.2",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))


class OllamaRuntime:
    DEFAULT_BASE_URL = "http://127.0.0.1:11434"
    DEFAULT_MODEL = "qwen2.5:1.5b"
    LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}

    def __init__(
        self,
        config: OllamaRuntimeConfig | None = None,
        http_client=None,
        environ=None,
    ):
        self.environ = os.environ if environ is None else environ
        self.config = config or self.load_config(self.environ)
        self.http_client = http_client or UrllibOllamaHTTPClient()

    @classmethod
    def load_config(cls, environ=None) -> OllamaRuntimeConfig:
        env = os.environ if environ is None else environ
        raw_base_url = str(env.get("OLLAMA_BASE_URL") or cls.DEFAULT_BASE_URL).strip()
        raw_model = str(env.get("OLLAMA_MODEL") or cls.DEFAULT_MODEL).strip()
        source = "env" if env.get("OLLAMA_BASE_URL") or env.get("OLLAMA_MODEL") else "defaults"
        return OllamaRuntimeConfig(
            base_url=raw_base_url,
            model=raw_model or cls.DEFAULT_MODEL,
            tags_timeout_seconds=5,
            request_timeout_seconds=30,
            source=source,
        )

    @classmethod
    def validate_base_url(cls, base_url: str) -> tuple[bool, str, str | None]:
        text = str(base_url or "").strip()
        if not text:
            return False, "", "Ollama base URL is empty."
        parsed = urlparse(text)
        if parsed.scheme != "http":
            return False, "", "Ollama base URL must use http."
        if parsed.username or parsed.password:
            return False, "", "Ollama base URL must not contain credentials."
        host = parsed.hostname
        if host not in cls.LOCAL_HOSTS:
            return False, "", "Ollama base URL must point to localhost only."
        if parsed.params or parsed.query or parsed.fragment:
            return False, "", "Ollama base URL must not contain params, query, or fragment."
        path = parsed.path or ""
        if "\\" in path or ".." in path.split("/"):
            return False, "", "Ollama base URL path is not safe."
        normalized_path = "/" + posixpath.normpath(path).strip("/") if path.strip("/") else ""
        if normalized_path == "/.":
            normalized_path = ""
        if normalized_path and normalized_path != "/api":
            return False, "", "Ollama base URL may only use root or /api path."
        netloc = parsed.netloc
        if host == "::1" and not netloc.startswith("["):
            netloc = f"[::1]{(':' + str(parsed.port)) if parsed.port else ''}"
        safe = urlunparse(("http", netloc, normalized_path, "", "", "")).rstrip("/")
        return True, safe, None

    def build_url(self, path: str) -> str:
        ok, safe_base, error = self.validate_base_url(self.config.base_url)
        if not ok:
            raise ValueError(error or "Invalid Ollama base URL.")
        safe_path = self._safe_api_path(path)
        base = safe_base[:-4] if safe_base.endswith("/api") else safe_base
        return base.rstrip("/") + safe_path

    def list_models(self) -> tuple[bool, tuple[str, ...], str | None]:
        try:
            data = self.http_client.get_json(
                self.build_url("/api/tags"),
                timeout=self.config.tags_timeout_seconds,
            )
        except ValueError as error:
            return False, (), self._safe_error(error)
        except (TimeoutError, socket.timeout):
            return False, (), "Ollama localhost status check timed out."
        except (urllib.error.URLError, OSError):
            return False, (), "Ollama localhost server is unavailable."
        except Exception:
            return False, (), "Ollama localhost model list failed safely."

        models = self._parse_models(data)
        return True, models, None

    def status(self, check_models: bool = True) -> OllamaRuntimeStatus:
        ok, safe_base, error = self.validate_base_url(self.config.base_url)
        if not ok:
            return OllamaRuntimeStatus(
                ok=False,
                base_url=self._safe_display(self.config.base_url),
                model=self.config.model,
                server_reachable=False,
                model_installed=None,
                installed_models=(),
                safe_message=error or "Ollama base URL is invalid.",
            )
        if not check_models:
            return OllamaRuntimeStatus(
                ok=True,
                base_url=safe_base,
                model=self.config.model,
                server_reachable=False,
                model_installed=None,
                installed_models=(),
                safe_message="Ollama config is safe; runtime was not called.",
            )

        reachable, models, list_error = self.list_models()
        if not reachable:
            return OllamaRuntimeStatus(
                ok=False,
                base_url=safe_base,
                model=self.config.model,
                server_reachable=False,
                model_installed=None,
                installed_models=(),
                safe_message=list_error or "Ollama localhost server is unavailable.",
            )
        installed = self.config.model in models
        message = "Ollama localhost server is reachable."
        if not installed:
            message = "Ollama localhost server is reachable, but configured model is not installed."
        return OllamaRuntimeStatus(
            ok=installed,
            base_url=safe_base,
            model=self.config.model,
            server_reachable=True,
            model_installed=installed,
            installed_models=models,
            safe_message=message,
        )

    def chat(self, prompt: str, model: str | None = None) -> tuple[bool, str, str | None]:
        payload = {
            "model": model or self.config.model,
            "messages": [{"role": "user", "content": str(prompt or "")}],
            "stream": False,
        }
        try:
            data = self.http_client.post_json(
                self.build_url("/api/chat"),
                payload=payload,
                timeout=self.config.request_timeout_seconds,
            )
        except ValueError as error:
            return False, "", self._safe_error(error)
        except (TimeoutError, socket.timeout):
            return False, "", "Ollama localhost chat request timed out."
        except (urllib.error.URLError, OSError):
            return False, "", "Ollama localhost server is unavailable."
        except Exception:
            return False, "", "Ollama localhost chat request failed safely."

        answer = self._parse_answer(data)
        if not answer:
            return False, "", "Ollama response text could not be parsed safely."
        return True, answer, None

    @staticmethod
    def _safe_api_path(path: str) -> str:
        value = str(path or "").strip()
        if not value.startswith("/"):
            value = "/" + value
        if "\\" in value or ".." in value.split("/"):
            raise ValueError("Ollama API path is not safe.")
        normalized = "/" + posixpath.normpath(value).strip("/")
        if normalized not in {"/api/tags", "/api/chat"}:
            raise ValueError("Ollama API path is not allowed.")
        return normalized

    @staticmethod
    def _parse_models(data) -> tuple[str, ...]:
        if not isinstance(data, dict):
            return ()
        raw_models = data.get("models")
        if not isinstance(raw_models, list):
            return ()
        names = []
        for item in raw_models:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if isinstance(name, str) and name.strip():
                names.append(name.strip())
        return tuple(sorted(dict.fromkeys(names)))

    @staticmethod
    def _parse_answer(data) -> str | None:
        if not isinstance(data, dict):
            return None
        message = data.get("message")
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str) and content.strip():
                return content
        response = data.get("response")
        if isinstance(response, str) and response.strip():
            return response
        return None

    @classmethod
    def _safe_error(cls, value) -> str:
        text = cls._safe_display(value)
        text = _TOKEN_RE.sub(r"\1=[REDACTED]", text)
        text = _LONG_SECRET_RE.sub("[REDACTED]", text)
        return text[:180] if len(text) > 180 else text

    @staticmethod
    def _safe_display(value) -> str:
        return " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split())
