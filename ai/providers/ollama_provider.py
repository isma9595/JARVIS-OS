"""Local-only Ollama provider adapter."""

from __future__ import annotations

from ai.ollama_runtime import OllamaRuntime
from ai.provider_contracts import (
    AIProviderCapability,
    AIProviderInfo,
    AIProviderSafetyLevel,
    AIRequest,
    AIResponse,
)


class OllamaProvider:
    NAME = "ollama"
    CAPABILITIES = {
        AIProviderCapability.CHAT,
        AIProviderCapability.SUMMARY,
        AIProviderCapability.CLASSIFICATION,
        AIProviderCapability.CODE,
    }

    def __init__(
        self,
        runtime: OllamaRuntime | None = None,
        enabled: bool = False,
        model: str | None = None,
    ):
        self.runtime = runtime or OllamaRuntime()
        self.enabled = enabled
        self.model = model or self.runtime.config.model

    def get_info(self) -> AIProviderInfo:
        return AIProviderInfo(
            name=self.NAME,
            model_name=self.model,
            capabilities=sorted(capability.value for capability in self.CAPABILITIES),
            safety_level=AIProviderSafetyLevel.LOCAL_ONLY.value,
            enabled=bool(self.enabled),
            description=(
                "Ollama localhost-only adapter. No API key, no cloud, no model "
                "pull automation; explicit one-shot only."
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
                f"Ollama provider does not support capability: {capability.value}",
            )
        if not self.enabled:
            return self._error_response(
                capability,
                "Ollama provider is disabled; use explicit local one-shot.",
            )

        ok, answer, safe_error = self.runtime.chat(
            self._prompt_for(request.prompt, capability),
            model=self.model,
        )
        if not ok:
            return self._error_response(
                capability,
                safe_error or "Ollama localhost request failed safely.",
            )
        return AIResponse(
            text=answer,
            provider_name=self.NAME,
            model_name=self.model,
            capability=capability.value,
            safety_level=AIProviderSafetyLevel.LOCAL_ONLY.value,
        )

    @classmethod
    def _capability_from_task_type(cls, task_type: str) -> AIProviderCapability:
        normalized = str(task_type or "chat").strip().lower()
        for capability in AIProviderCapability:
            if capability.value == normalized:
                return capability
        return AIProviderCapability.CHAT

    @staticmethod
    def _prompt_for(prompt: str, capability: AIProviderCapability) -> str:
        if capability == AIProviderCapability.SUMMARY:
            return "Summarize briefly:\n\n" + prompt
        if capability == AIProviderCapability.CLASSIFICATION:
            return "Classify this request with one short category:\n\n" + prompt
        return prompt

    def _error_response(
        self,
        capability: AIProviderCapability,
        message: str,
    ) -> AIResponse:
        return AIResponse(
            text=message,
            provider_name=self.NAME,
            model_name=self.model,
            capability=capability.value,
            safety_level=AIProviderSafetyLevel.LOCAL_ONLY.value,
            is_error=True,
            error_message=message,
        )
