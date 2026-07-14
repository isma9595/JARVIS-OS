"""Safe Groq OpenAI-compatible chat completions provider adapter."""

from __future__ import annotations

import json
import os
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
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
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
        }

        try:
            raw_response = self.http_client.post_json(
                self.ENDPOINT,
                headers=headers,
                payload=payload,
                timeout=self.timeout_seconds,
            )
        except urllib.error.HTTPError as error:
            return self._http_error_response(capability, error.code)
        except TimeoutError:
            return self._error_response(capability, "Groq network timeout.")
        except (socket.timeout, urllib.error.URLError, OSError) as error:
            status = getattr(error, "status", None) or getattr(error, "code", None)
            if status is not None:
                return self._http_error_response(capability, status)
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
        if value is None or not str(value).strip():
            return None
        return str(value)

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
        return [
            {
                "role": "system",
                "content": (
                    "You are JARVIS-OS external text provider. Answer safely "
                    "and concisely. Do not claim you can execute commands."
                ),
            },
            {"role": "user", "content": user_content},
        ]

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

    def _http_error_response(self, capability: AIProviderCapability, status: int) -> AIResponse:
        try:
            status_int = int(status)
        except (TypeError, ValueError):
            status_int = 0
        if status_int in (401, 403):
            return self._error_response(
                capability,
                f"Groq authentication failed: status {status_int}. Check GROQ_API_KEY.",
            )
        if status_int == 429:
            return self._error_response(
                capability,
                "Groq rate or quota limit reached: status 429.",
            )
        return self._error_response(capability, f"Groq HTTP error: status {status_int}.")

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
