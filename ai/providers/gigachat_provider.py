"""Safe GigaChat chat completions provider adapter."""

from __future__ import annotations

import json
import os
import re
import socket
import urllib.error
import urllib.request

from ai.gigachat_token_manager import GigaChatTokenManager
from ai.provider_config import AIProviderConfig
from ai.provider_contracts import (
    AIProviderCapability,
    AIProviderInfo,
    AIProviderSafetyLevel,
    AIRequest,
    AIResponse,
)


class UrllibGigaChatHTTPClient:
    """Tiny JSON POST client for GigaChat chat completions."""

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


class GigaChatProvider:
    NAME = "gigachat"
    ENDPOINT = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
    DEFAULT_MODEL = "GigaChat"
    CAPABILITIES = {
        AIProviderCapability.CHAT,
        AIProviderCapability.SUMMARY,
        AIProviderCapability.CLASSIFICATION,
    }

    def __init__(
        self,
        config: AIProviderConfig | None = None,
        token_manager: GigaChatTokenManager | None = None,
        http_client=None,
        timeout_seconds: int = 30,
        allow_network: bool = False,
        environ=None,
    ):
        self.config = config or AIProviderConfig(
            name=self.NAME,
            provider_type="gigachat",
            enabled=False,
            default_model=self.DEFAULT_MODEL,
            api_key_env_var="GIGACHAT_AUTH_KEY",
        )
        self.environ = os.environ if environ is None else environ
        self.http_client = http_client or UrllibGigaChatHTTPClient()
        self.timeout_seconds = timeout_seconds
        self.allow_network = allow_network
        self.token_manager = token_manager or GigaChatTokenManager(
            environ=self.environ,
            timeout_seconds=timeout_seconds,
        )

    def get_info(self) -> AIProviderInfo:
        return AIProviderInfo(
            name=self.NAME,
            model_name=self._model_name(),
            capabilities=sorted(capability.value for capability in self.CAPABILITIES),
            safety_level=AIProviderSafetyLevel.EXTERNAL_API.value,
            enabled=bool(self.config.enabled),
            description=(
                "GigaChat chat completions adapter. Disabled by default; network "
                "calls require an explicit allow_network=True one-shot instance."
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
                f"GigaChat provider does not support capability: {capability.value}",
            )
        if not self.config.enabled:
            return self._error_response(capability, "GigaChat provider is disabled.")
        if not self._auth_key_present():
            return self._error_response(
                capability,
                "GigaChat auth key is missing. Set GIGACHAT_AUTH_KEY in the environment.",
            )
        if not self.allow_network:
            return self._error_response(
                capability,
                "GigaChat provider is configured but real network calls are disabled.",
            )

        token_result = self.token_manager.get_access_token()
        if not token_result.ok or not token_result.access_token:
            return self._error_response(
                capability,
                token_result.error_message or "GigaChat access token could not be obtained.",
            )

        payload = {
            "model": self._model_name(),
            "messages": self._messages_for(request.prompt, capability),
            "max_tokens": self._max_output_tokens_for(request),
            "temperature": 0.2,
        }
        headers = {
            "Authorization": f"Bearer {token_result.access_token}",
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
            return self._http_error_response(
                capability,
                error.code,
                error,
                token_result.access_token,
            )
        except TimeoutError:
            return self._error_response(capability, "GigaChat network timeout.")
        except (socket.timeout, urllib.error.URLError, OSError) as error:
            status = getattr(error, "status", None) or getattr(error, "code", None)
            if status is not None:
                return self._http_error_response(
                    capability,
                    status,
                    error,
                    token_result.access_token,
                )
            return self._error_response(capability, "GigaChat network error.")

        try:
            data = json.loads(raw_response)
        except (TypeError, json.JSONDecodeError):
            return self._error_response(capability, "GigaChat response was not valid JSON.")

        text = self._extract_text(data)
        if text is None:
            return self._error_response(
                capability,
                "GigaChat response text could not be parsed safely.",
            )

        return AIResponse(
            text=text,
            provider_name=self.NAME,
            model_name=self._model_name(),
            capability=capability.value,
            safety_level=AIProviderSafetyLevel.EXTERNAL_API.value,
        )

    def _auth_key_present(self) -> bool:
        env_var = self.config.api_key_env_var or "GIGACHAT_AUTH_KEY"
        value = self.environ.get(env_var)
        return value is not None and bool(str(value).strip())

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
        access_token: str | None = None,
    ) -> AIResponse:
        try:
            status_int = int(status)
        except (TypeError, ValueError):
            status_int = 0
        detail = self._safe_http_error_detail(error, access_token)
        if status_int in (401, 403):
            message = f"GigaChat authentication/permission failed: status {status_int}."
        elif status_int == 404:
            message = "GigaChat model or endpoint was not found: status 404."
        elif status_int == 422:
            message = "GigaChat validation/context error: status 422."
        elif status_int == 429:
            message = "GigaChat rate or quota limit reached: status 429."
        else:
            message = f"GigaChat HTTP error: status {status_int}."
        if detail:
            message = "\n".join([message, *detail])
        if status_int in (401, 403):
            message = "\n".join([message, "Auth key and token values were not printed."])
        return self._error_response(capability, message)

    @classmethod
    def _safe_http_error_detail(
        cls,
        error,
        access_token: str | None = None,
    ) -> list[str] | None:
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
            error_data = data

        parts = []
        for label, key in (
            ("GigaChat error message", "message"),
            ("GigaChat error type", "type"),
            ("GigaChat error code", "code"),
        ):
            value = error_data.get(key)
            if isinstance(value, str) and value.strip():
                safe_value = cls._sanitize_error_fragment(value, access_token)
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
    def _sanitize_error_fragment(cls, value: str, access_token: str | None = None) -> str:
        text = str(value).replace("\r", " ").replace("\n", " ").strip()
        if access_token:
            text = text.replace(access_token, "<redacted>")
        text = re.sub(r"Bearer\s+[A-Za-z0-9._~+/=-]+", "Bearer <redacted>", text)
        text = re.sub(r"Basic\s+[A-Za-z0-9._~+/=-]+", "Basic <redacted>", text)
        text = re.sub(r"\b[A-Za-z0-9_-]{32,}\b", "<redacted>", text)
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
