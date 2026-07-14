"""Offline deterministic dry-run AI provider."""

from __future__ import annotations

from ai.provider_contracts import (
    AIProviderCapability,
    AIProviderInfo,
    AIProviderSafetyLevel,
    AIRequest,
    AIResponse,
)


class DryRunAIProvider:
    NAME = "dry_run"
    MODEL_NAME = "jarvis-dry-run-v0"
    SAFETY_LEVEL = AIProviderSafetyLevel.OFFLINE_DETERMINISTIC
    CAPABILITIES = {
        AIProviderCapability.CHAT,
        AIProviderCapability.SUMMARY,
        AIProviderCapability.CLASSIFICATION,
    }

    def get_info(self) -> AIProviderInfo:
        return AIProviderInfo(
            name=self.NAME,
            model_name=self.MODEL_NAME,
            capabilities=sorted(capability.value for capability in self.CAPABILITIES),
            safety_level=self.SAFETY_LEVEL.value,
            enabled=True,
            description=(
                "Deterministic offline dry-run provider. No network, no API keys, "
                "no tool execution."
            ),
        )

    def supports(self, capability: AIProviderCapability) -> bool:
        return capability in self.CAPABILITIES

    def generate(self, request: AIRequest) -> AIResponse:
        validation_error = request.validation_error()
        if validation_error:
            return self._error_response(AIProviderCapability.CHAT, validation_error)

        capability = self._capability_from_task_type(request.task_type)
        if not self.supports(capability):
            return self._error_response(
                capability,
                f"Unsupported dry-run capability: {capability.value}",
            )

        if capability == AIProviderCapability.SUMMARY:
            text = self._summary_text(request.prompt, request.max_chars)
        elif capability == AIProviderCapability.CLASSIFICATION:
            text = self._classification_text(request.prompt)
        else:
            text = (
                "AI dry-run: я получил запрос, но внешний AI-провайдер ещё не подключён. "
                f"Превью запроса: {self._preview(request.prompt)}"
            )

        return AIResponse(
            text=text,
            provider_name=self.NAME,
            model_name=self.MODEL_NAME,
            capability=capability.value,
            safety_level=self.SAFETY_LEVEL.value,
        )

    def generate_for_capability(
        self,
        request: AIRequest,
        capability: AIProviderCapability,
    ) -> AIResponse:
        if not self.supports(capability):
            return self._error_response(
                capability,
                f"Unsupported dry-run capability: {capability.value}",
            )
        request.task_type = capability.value
        return self.generate(request)

    @classmethod
    def _capability_from_task_type(cls, task_type: str) -> AIProviderCapability:
        normalized = str(task_type or "chat").strip().lower()
        for capability in AIProviderCapability:
            if capability.value == normalized:
                return capability
        return AIProviderCapability.CHAT

    @classmethod
    def _summary_text(cls, prompt: str, max_chars: int | None):
        normalized = " ".join(str(prompt).split())
        first_sentence = cls._first_sentence(normalized)
        limit = max_chars or 160
        summary = cls._trim(first_sentence, limit)
        return f"AI dry-run summary: {summary}"

    @staticmethod
    def _classification_text(prompt: str):
        normalized = " ".join(str(prompt or "").lower().split())
        if not normalized:
            category = "unknown"
        elif "код" in normalized or "python" in normalized:
            category = "code"
        elif "письмо" in normalized or "документ" in normalized:
            category = "writing"
        elif "статус" in normalized or "провер" in normalized:
            category = "diagnostic"
        else:
            category = "general"
        return f"AI dry-run classification: {category}"

    @classmethod
    def _preview(cls, prompt: str):
        return cls._trim(" ".join(str(prompt).split()), 120)

    @staticmethod
    def _first_sentence(text: str):
        for separator in (".", "!", "?"):
            index = text.find(separator)
            if index >= 0:
                return text[: index + 1].strip()
        return text

    @staticmethod
    def _trim(text: str, max_chars: int):
        if len(text) <= max_chars:
            return text
        if max_chars <= 3:
            return text[:max_chars]
        return text[: max_chars - 3].rstrip() + "..."

    def _error_response(
        self,
        capability: AIProviderCapability,
        message: str,
    ) -> AIResponse:
        return AIResponse(
            text=f"AI dry-run error: {message}",
            provider_name=self.NAME,
            model_name=self.MODEL_NAME,
            capability=capability.value,
            safety_level=self.SAFETY_LEVEL.value,
            is_error=True,
            error_message=message,
        )
