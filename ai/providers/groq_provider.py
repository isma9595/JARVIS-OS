"""Safe Groq OpenAI-compatible chat completions provider adapter."""

from __future__ import annotations

import json
import os
import re
import socket
import urllib.error
import urllib.request

from ai.provider_config import AIProviderConfig
from ai.provider_contracts import (
    AIProviderCapability,
    AIProviderInfo,
    AIProviderSafetyLevel,
    AIRequest,
    AIResponse,
)


class UrllibGroqHTTPClient:
    """Tiny JSON POST client for Groq chat completions."""

    def post_json(self, url: str, headers: dict[str, str], payload: dict, timeout: int):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8")


class GroqProvider:
    NAME = "groq"
    ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
    DEFAULT_MODEL = "llama-3.1-8b-instant"
    CAPABILITIES = {
        AIProviderCapability.CHAT,
        AIProviderCapability.SUMMARY,
        AIProviderCapability.CLASSIFICATION,
    }

    def __init__(
        self,
        config: AIProviderConfig | None = None,
        http_client=None,
        timeout_seconds: int = 30,
        allow_network: bool = False,
        environ=None,
    ):
        self.config = config or AIProviderConfig(
            name=self.NAME,
            provider_type="groq",
            enabled=False,
            default_model=self.DEFAULT_MODEL,
            api_key_env_var="GROQ_API_KEY",
        )
        self.http_client = http_client or UrllibGroqHTTPClient()
        self.timeout_seconds = timeout_seconds
        self.allow_network = allow_network
        self.environ = os.environ if environ is None else environ

    def get_info(self) -> AIProviderInfo:
        return AIProviderInfo(
            name=self.NAME,
            model_name=self._model_name(),
            capabilities=sorted(capability.value for capability in self.CAPABILITIES),
            safety_level=AIProviderSafetyLevel.EXTERNAL_API.value,
            enabled=bool(self.config.enabled),
            description=(
                "Groq OpenAI-compatible chat adapter. Disabled by default; "
                "network calls require an explicit allow_network=True one-shot instance."
            ),
        )

    def supports(self, capability: AIProviderCapability) -> bool:
        return capability in self.CAPABILITIES

    def generate(self, request: AIRequest) -> AIResponse:
        validation_error = request.validation_error()
        capability = self._capability_from_task_type(request.task_type)
        if validation_error:
            return self._error_response(capability, validation_error)
        if not self.supports(capability):
            return self._error_response(
                capability,
                f"Groq provider does not support capability: {capability.value}",
            )
        if not self.config.enabled:
            return self._error_response(capability, "Groq provider is disabled.")

        api_key = self._api_key()
        if not api_key:
            return self._error_response(
                capability,
                "Groq API key is missing. Set GROQ_API_KEY in the environment.",
            )
        if not self.allow_network:
            return self._error_response(
                capability,
                "Groq provider is configured but real network calls are disabled.",
            )

        payload = {
            "model": self._model_name(),
            "messages": self._messages_for(request.prompt, capability),
            "max_tokens": self._max_output_tokens_for(request),
            "temperature": 0.2,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "JARVIS-OS/0.2",
        }

        try:
            raw_response = self.http_client.post_json(
                self.ENDPOINT,
                headers=headers,
                payload=payload,
                timeout=self.timeout_seconds,
            )
        except urllib.error.HTTPError as error:
            return self._http_error_response(capability, error.code, error, api_key)
        except TimeoutError:
            return self._error_response(capability, "Groq network timeout.")
        except (socket.timeout, urllib.error.URLError, OSError) as error:
            status = getattr(error, "status", None) or getattr(error, "code", None)
            if status is not None:
                return self._http_error_response(capability, status, error, api_key)
            return self._error_response(capability, "Groq network error.")

        try:
            data = json.loads(raw_response)
        except (TypeError, json.JSONDecodeError):
            return self._error_response(capability, "Groq response was not valid JSON.")

        text = self._extract_text(data)
        if text is None:
            return self._error_response(
                capability,
                "Groq response text could not be parsed safely.",
            )

        return AIResponse(
            text=text,
            provider_name=self.NAME,
            model_name=self._model_name(),
            capability=capability.value,
            safety_level=AIProviderSafetyLevel.EXTERNAL_API.value,
        )

    def _api_key(self) -> str | None:
        env_var = self.config.api_key_env_var or "GROQ_API_KEY"
        value = self.environ.get(env_var)
        if value is None:
            return None
        stripped = str(value).strip()
        if not stripped:
            return None
        return stripped

    def _model_name(self) -> str:
        return self.config.default_model or self.DEFAULT_MODEL

    @staticmethod
    def _max_output_tokens_for(request: AIRequest) -> int:
        metadata = request.metadata or {}
        try:
            value = int(metadata.get("max_output_tokens", 128))
        except (TypeError, ValueError):
            return 128
        if value <= 0:
            return 128
        return value

    @classmethod
    def _capability_from_task_type(cls, task_type: str) -> AIProviderCapability:
        normalized = str(task_type or "chat").strip().lower()
        for capability in AIProviderCapability:
            if capability.value == normalized:
                return capability
        return AIProviderCapability.CHAT

    @staticmethod
    def _messages_for(prompt: str, capability: AIProviderCapability) -> list[dict[str, str]]:
        if capability == AIProviderCapability.SUMMARY:
            user_content = "Кратко перескажи следующий текст:\n\n" + prompt
        elif capability == AIProviderCapability.CLASSIFICATION:
            user_content = "Классифицируй запрос одной короткой категорией:\n\n" + prompt
        else:
            user_content = prompt
        return [{"role": "user", "content": user_content}]

    @classmethod
    def _extract_text(cls, data) -> str | None:
        if not isinstance(data, dict):
            return None
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            return None
        first = choices[0]
        if not isinstance(first, dict):
            return None
        message = first.get("message")
        if not isinstance(message, dict):
            return None
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content
        return None

    def _http_error_response(
        self,
        capability: AIProviderCapability,
        status: int,
        error=None,
        api_key: str | None = None,
    ) -> AIResponse:
        try:
            status_int = int(status)
        except (TypeError, ValueError):
            status_int = 0
        detail = self._safe_http_error_detail(error, api_key)
        if status_int in (401, 403):
            lines = [
                f"Groq authentication/permission failed: status {status_int}.",
            ]
            if detail:
                lines.extend(detail)
            else:
                lines.append("Groq error body was unavailable/unparseable safely.")
            lines.append("The key value was not printed.")
            return self._error_response(
                capability,
                "\n".join(lines),
            )
        if status_int == 429:
            message = "Groq rate or quota limit reached: status 429."
            if detail:
                message = "\n".join([message, *detail])
            return self._error_response(
                capability,
                message,
            )
        message = f"Groq HTTP error: status {status_int}."
        if detail:
            message = "\n".join([message, *detail])
        return self._error_response(capability, message)

    @classmethod
    def _safe_http_error_detail(cls, error, api_key: str | None = None) -> list[str] | None:
        body = cls._read_error_body(error)
        if not body:
            return None
        try:
            data = json.loads(body)
        except (TypeError, json.JSONDecodeError):
            return None
        if not isinstance(data, dict):
            return None
        error_data = data.get("error")
        if not isinstance(error_data, dict):
            return None

        parts = []
        for label, key in (
            ("Groq error message", "message"),
            ("Groq error type", "type"),
            ("Groq error code", "code"),
        ):
            value = error_data.get(key)
            if isinstance(value, str) and value.strip():
                safe_value = cls._sanitize_error_fragment(value, api_key)
                if safe_value:
                    parts.append(f"{label}: {safe_value}")
        if not parts:
            return None
        return parts

    @staticmethod
    def _read_error_body(error) -> str | None:
        if error is None or not hasattr(error, "read"):
            return None
        try:
            raw_body = error.read()
        except Exception:
            return None
        if isinstance(raw_body, bytes):
            try:
                return raw_body.decode("utf-8", errors="replace")
            except Exception:
                return None
        if isinstance(raw_body, str):
            return raw_body
        return None

    @classmethod
    def _sanitize_error_fragment(cls, value: str, api_key: str | None = None) -> str:
        text = str(value).replace("\r", " ").replace("\n", " ").strip()
        if api_key:
            text = text.replace(api_key, "<redacted>")
        text = re.sub(r"Bearer\s+[A-Za-z0-9._~+/=-]+", "Bearer <redacted>", text)
        text = re.sub(r"\b(?:gsk_|sk-)[A-Za-z0-9._-]{12,}", "<redacted>", text)
        return cls._cap_text(text, 160)

    @staticmethod
    def _cap_text(value: str, limit: int) -> str:
        text = str(value or "")
        if len(text) <= limit:
            return text
        return text[: limit - 3].rstrip() + "..."

    def _error_response(
        self,
        capability: AIProviderCapability,
        message: str,
    ) -> AIResponse:
        return AIResponse(
            text=message,
            provider_name=self.NAME,
            model_name=self._model_name(),
            capability=capability.value,
            safety_level=AIProviderSafetyLevel.EXTERNAL_API.value,
            is_error=True,
            error_message=message,
        )
