"""Deterministic AI provider router for offline dry-run behavior."""

from __future__ import annotations

from dataclasses import replace

from ai.provider_config_manager import AIProviderConfigManager
from ai.provider_contracts import (
    AIProvider,
    AIProviderCapability,
    AIProviderSafetyLevel,
    AIRequest,
    AIResponse,
)
from ai.providers.dry_run_provider import DryRunAIProvider
from ai.providers.gemini_provider import GeminiProvider
from ai.providers.gigachat_provider import GigaChatProvider
from ai.providers.groq_provider import GroqProvider
from ai.providers.openai_provider import OpenAIProvider


class AIProviderRouter:
    def __init__(
        self,
        providers: list[AIProvider] | None = None,
        config_manager: AIProviderConfigManager | None = None,
    ):
        self._providers: dict[str, AIProvider] = {}
        self._default_provider_name: str | None = None
        self.config_manager = config_manager or AIProviderConfigManager()

        initial_providers = providers if providers is not None else self._default_providers()
        for provider in initial_providers:
            self.register_provider(provider)

        if "dry_run" in self._providers:
            self._default_provider_name = "dry_run"
        elif self._default_provider_name is None and self._providers:
            self._default_provider_name = next(iter(self._providers))

    def register_provider(self, provider: AIProvider):
        info = provider.get_info()
        self._providers[info.name] = provider
        if self._default_provider_name is None:
            self._default_provider_name = info.name

    def list_providers(self):
        return [provider.get_info() for provider in self._providers.values()]

    def get_default_provider(self):
        if self._default_provider_name is None:
            return None
        return self._providers.get(self._default_provider_name)

    def set_default_provider(self, name: str):
        if name not in self._providers:
            raise ValueError(f"Unknown AI provider: {name}")
        self._default_provider_name = name

    def route(self, capability: AIProviderCapability):
        default_provider = self.get_default_provider()
        if default_provider is not None and default_provider.supports(capability):
            return default_provider

        for provider in self._providers.values():
            if provider.supports(capability):
                return provider
        return None

    def generate(
        self,
        request: AIRequest,
        capability: AIProviderCapability = AIProviderCapability.CHAT,
    ) -> AIResponse:
        validation_error = request.validation_error()
        if validation_error:
            return self._error_response(capability, validation_error)

        provider = self.route(capability)
        if provider is None:
            return self._error_response(
                capability,
                f"No AI provider supports capability: {capability.value}",
            )
        routed_request = replace(request, task_type=capability.value)
        return provider.generate(routed_request)

    def generate_with_provider(
        self,
        provider_name: str,
        request: AIRequest,
        capability: AIProviderCapability = AIProviderCapability.CHAT,
    ) -> AIResponse:
        validation_error = request.validation_error()
        if validation_error:
            return self._error_response(capability, validation_error)

        provider = self._providers.get(str(provider_name or "").strip().lower())
        if provider is None:
            return self._error_response(
                capability,
                f"Unknown AI provider: {provider_name}",
            )
        if not provider.supports(capability):
            return self._error_response(
                capability,
                f"AI provider {provider_name} does not support capability: {capability.value}",
            )
        routed_request = replace(request, task_type=capability.value)
        return provider.generate(routed_request)

    def status_text_ru(self):
        default_provider = self.get_default_provider()
        default_name = default_provider.get_info().name if default_provider else "нет"
        provider_count = len(self._providers)
        provider_names = ", ".join(self._providers.keys()) or "нет"
        return (
            "Статус AI provider router:\n"
            f"- Провайдер по умолчанию: {default_name}\n"
            f"- Доступно провайдеров: {provider_count}\n"
            f"- Провайдеры: {provider_names}\n"
            "- Активный режим: dry-run / offline deterministic\n"
            "- Внешние провайдеры из конфигурации остаются выключенными по умолчанию.\n"
            "- OpenAI зарегистрирован как disabled external provider; сеть для него выключена, пока явно не разрешена.\n"
            "- Gemini зарегистрирован как disabled external provider; сеть выключена кроме явного one-shot.\n"
            "- Groq зарегистрирован как disabled external provider; сеть выключена кроме явного one-shot.\n"
            "- GigaChat зарегистрирован как disabled external provider; сеть выключена кроме явного one-shot; auth key/token не печатаются.\n"
            "- Слой конфигурации проверяет только наличие переменных окружения и не показывает ключи.\n"
            "- Реальные внешние AI-провайдеры не активны по умолчанию.\n"
            "- Сеть не используется.\n"
            "- API-ключи не требуются."
        )

    def providers_text_ru(self):
        lines = [
            "AI провайдеры:",
            "Активен только offline deterministic provider.",
        ]
        for info in self.list_providers():
            capabilities = ", ".join(info.capabilities)
            lines.append(
                f"- {info.name} ({info.model_name}) [{info.safety_level}] "
                f"enabled={info.enabled}; capabilities: {capabilities}"
            )
        lines.extend(
            [
                "OpenAI виден как внешний провайдер, но выключен по умолчанию; сеть не используется без явного разрешения.",
                "Gemini виден как внешний провайдер, но выключен по умолчанию; сеть не используется кроме явного one-shot.",
                "Groq виден как внешний провайдер, но выключен по умолчанию; сеть не используется кроме явного one-shot.",
                "GigaChat виден как внешний провайдер, но выключен по умолчанию; сеть не используется кроме явного one-shot; auth key/token не печатаются.",
                "API-ключи не печатаются.",
            ]
        )
        return "\n".join(lines)

    def _default_providers(self):
        providers: list[AIProvider] = [DryRunAIProvider()]
        openai_config = self.config_manager.get_config("openai")
        if openai_config is not None:
            providers.append(OpenAIProvider(config=openai_config))
        gemini_config = self.config_manager.get_config("gemini")
        if gemini_config is not None:
            providers.append(GeminiProvider(config=gemini_config))
        groq_config = self.config_manager.get_config("groq")
        if groq_config is not None:
            providers.append(GroqProvider(config=groq_config))
        gigachat_config = self.config_manager.get_config("gigachat")
        if gigachat_config is not None:
            providers.append(GigaChatProvider(config=gigachat_config))
        return providers

    @staticmethod
    def _error_response(capability: AIProviderCapability, message: str) -> AIResponse:
        return AIResponse(
            text=f"AI dry-run error: {message}",
            provider_name="router",
            model_name="none",
            capability=capability.value,
            safety_level=AIProviderSafetyLevel.OFFLINE_DETERMINISTIC.value,
            is_error=True,
            error_message=message,
        )
