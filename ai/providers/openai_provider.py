"""Safe OpenAI Responses API provider adapter."""

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


class UrllibOpenAIHTTPClient:
    """Tiny JSON POST client for the Responses API."""

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


class OpenAIProvider:
    NAME = "openai"
    ENDPOINT = "https://api.openai.com/v1/responses"
    DEFAULT_MODEL = "openai-default"
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
            provider_type="openai",
            enabled=False,
            default_model=self.DEFAULT_MODEL,
            api_key_env_var="OPENAI_API_KEY",
        )
        self.http_client = http_client or UrllibOpenAIHTTPClient()
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
                "OpenAI Responses API adapter. Disabled by default; network calls "
                "require an explicit allow_network=True instance."
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
                f"OpenAI provider does not support capability: {capability.value}",
            )
        if not self.config.enabled:
            return self._error_response(capability, "OpenAI provider is disabled.")

        api_key = self._api_key()
        if not api_key:
            return self._error_response(
                capability,
                "OpenAI API key is missing. Set OPENAI_API_KEY in the environment.",
            )
        if not self.allow_network:
            return self._error_response(
                capability,
                "OpenAI provider is configured but real network calls are disabled.",
            )

        payload = {
            "model": self._model_name(),
            "input": self._input_for(request.prompt, capability),
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
            return self._error_response(
                capability,
                f"OpenAI HTTP error: status {error.code}.",
            )
        except TimeoutError:
            return self._error_response(capability, "OpenAI network timeout.")
        except (socket.timeout, urllib.error.URLError, OSError) as error:
            status = getattr(error, "status", None) or getattr(error, "code", None)
            if status is not None:
                return self._error_response(
                    capability,
                    f"OpenAI HTTP error: status {status}.",
                )
            return self._error_response(capability, "OpenAI network error.")

        try:
            data = json.loads(raw_response)
        except (TypeError, json.JSONDecodeError):
            return self._error_response(capability, "OpenAI response was not valid JSON.")

        text = self._extract_text(data)
        if text is None:
            return self._error_response(
                capability,
                "OpenAI response text could not be parsed safely.",
            )

        return AIResponse(
            text=text,
            provider_name=self.NAME,
            model_name=self._model_name(),
            capability=capability.value,
            safety_level=AIProviderSafetyLevel.EXTERNAL_API.value,
        )

    def _api_key(self) -> str | None:
        env_var = self.config.api_key_env_var or "OPENAI_API_KEY"
        value = self.environ.get(env_var)
        if value is None or not str(value).strip():
            return None
        return str(value)

    def _model_name(self) -> str:
        return self.config.default_model or self.DEFAULT_MODEL

    @classmethod
    def _capability_from_task_type(cls, task_type: str) -> AIProviderCapability:
        normalized = str(task_type or "chat").strip().lower()
        for capability in AIProviderCapability:
            if capability.value == normalized:
                return capability
        return AIProviderCapability.CHAT

    @staticmethod
    def _input_for(prompt: str, capability: AIProviderCapability) -> str:
        if capability == AIProviderCapability.SUMMARY:
            return "Кратко перескажи следующий текст:\n\n" + prompt
        if capability == AIProviderCapability.CLASSIFICATION:
            return "Классифицируй запрос одной короткой категорией:\n\n" + prompt
        return prompt

    @classmethod
    def _extract_text(cls, data) -> str | None:
        output_text = data.get("output_text") if isinstance(data, dict) else None
        if isinstance(output_text, str) and output_text.strip():
            return output_text

        output = data.get("output") if isinstance(data, dict) else None
        if not isinstance(output, list):
            return None
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for content_item in content:
                if not isinstance(content_item, dict):
                    continue
                text = content_item.get("text")
                if isinstance(text, str) and text.strip():
                    return text
        return None

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
