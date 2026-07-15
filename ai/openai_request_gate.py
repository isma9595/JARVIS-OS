"""One-shot gate for explicit real OpenAI requests."""

from __future__ import annotations

from dataclasses import dataclass, replace
import os

from ai.context_privacy_policy import AIContextPrivacyPolicy, AIContextTarget
from ai.openai_cost_guard import OpenAIRequestCostGuard
from ai.provider_language_policy import AIProviderLanguagePolicy
from ai.provider_config import AIProviderConfig, AIProviderKeyStatus
from ai.provider_config_manager import AIProviderConfigManager
from ai.provider_contracts import (
    AIProviderCapability,
    AIProviderSafetyLevel,
    AIRequest,
    AIResponse,
)
from ai.provider_router import AIProviderRouter
from ai.providers.openai_provider import OpenAIProvider


@dataclass(frozen=True)
class OpenAIRequestGateStatus:
    provider_configured: bool
    key_status: AIProviderKeyStatus
    default_provider_name: str | None
    can_request: bool
    reason: str


class OpenAIRequestGate:
    """Allow exactly one explicit OpenAI request without changing global state."""

    def __init__(
        self,
        config_manager: AIProviderConfigManager | None = None,
        router: AIProviderRouter | None = None,
        provider_factory=None,
        http_client=None,
        environ=None,
        request_guard: OpenAIRequestCostGuard | None = None,
        language_policy: AIProviderLanguagePolicy | None = None,
        context_privacy_policy: AIContextPrivacyPolicy | None = None,
    ):
        self.config_manager = config_manager or AIProviderConfigManager(environ=environ)
        self.router = router
        self.provider_factory = provider_factory or OpenAIProvider
        self.http_client = http_client
        self.environ = os.environ if environ is None else environ
        self.request_guard = request_guard or OpenAIRequestCostGuard(environ=self.environ)
        self.language_policy = language_policy or AIProviderLanguagePolicy()
        self.context_privacy_policy = context_privacy_policy or AIContextPrivacyPolicy()

    def can_make_real_request(self) -> OpenAIRequestGateStatus:
        status = self.config_manager.status_for("openai")
        default_name = self._default_provider_name()
        if status is None:
            return OpenAIRequestGateStatus(
                provider_configured=False,
                key_status=AIProviderKeyStatus.MISSING,
                default_provider_name=default_name,
                can_request=False,
                reason="OpenAI provider config is missing.",
            )
        if status.key_status != AIProviderKeyStatus.PRESENT:
            return OpenAIRequestGateStatus(
                provider_configured=True,
                key_status=status.key_status,
                default_provider_name=default_name,
                can_request=False,
                reason="OPENAI_API_KEY is missing.",
            )
        return OpenAIRequestGateStatus(
            provider_configured=True,
            key_status=status.key_status,
            default_provider_name=default_name,
            can_request=True,
            reason="Explicit one-shot command may make one request.",
        )

    def generate_one_shot(
        self,
        request: AIRequest,
        capability: AIProviderCapability = AIProviderCapability.CHAT,
        model_override: str | None = None,
    ) -> AIResponse:
        validation_error = request.validation_error()
        if validation_error:
            return self._error_response(capability, validation_error)

        privacy_decision = self.context_privacy_policy.decide(
            request.prompt,
            AIContextTarget.EXTERNAL_PROVIDER,
        )
        if not privacy_decision.allowed:
            return self._error_response(
                capability,
                self.context_privacy_policy.format_refusal(
                    request.prompt,
                    AIContextTarget.EXTERNAL_PROVIDER,
                ),
            )

        guard_result = self.request_guard.guard_request(
            request.prompt,
            request.metadata.get("max_output_tokens") if request.metadata else None,
            model_override=model_override,
        )
        if not guard_result.allowed:
            return self._error_response(capability, guard_result.safe_message)

        gate_status = self.can_make_real_request()
        if not gate_status.can_request:
            return self._error_response(capability, gate_status.reason)

        config = self._temporary_enabled_openai_config(guard_result.model)
        provider = self._build_provider(config)
        metadata = dict(request.metadata or {})
        metadata["max_output_tokens"] = str(guard_result.max_output_tokens)
        language_result = self.language_policy.apply(guard_result.prompt)
        one_shot_request = replace(
            request,
            prompt=language_result.prompt,
            task_type=capability.value,
            metadata=metadata,
        )
        response = provider.generate(one_shot_request)
        if response.is_error:
            return self._error_response(
                capability,
                response.error_message or response.text or "OpenAI request failed.",
            )
        return response

    def status_text_ru(self) -> str:
        status = self.can_make_real_request()
        default_name = status.default_provider_name or "none"
        return "\n".join(
            [
                "OpenAI one-shot real request status:",
                f"- provider config: {'present' if status.provider_configured else 'missing'}",
                f"- key status: {status.key_status.value}",
                "- key value is never printed",
                f"- model guard: {self.request_guard.safe_model_display()}",
                f"- max prompt chars: {self.request_guard.config.max_prompt_chars}",
                f"- max_output_tokens: {self.request_guard.config.max_output_tokens}",
                "- network: allowed only by explicit one-shot typed command",
                "- OpenAI is not enabled permanently",
                f"- default provider remains: {default_name}",
                f"- can request now: {status.can_request}",
                f"- reason: {status.reason}",
            ]
        )

    def guard_status_text_ru(self) -> str:
        return self.request_guard.status_text_ru()

    def model_text_ru(self) -> str:
        return self.request_guard.model_text_ru()

    def _temporary_enabled_openai_config(self, model: str) -> AIProviderConfig:
        config = self.config_manager.get_config("openai")
        if config is None:
            config = AIProviderConfig(
                name="openai",
                provider_type="openai",
                enabled=False,
                default_model=model,
                api_key_env_var="OPENAI_API_KEY",
            )
        return replace(config, enabled=True, default_model=model)

    def _build_provider(self, config: AIProviderConfig):
        kwargs = {
            "config": config,
            "allow_network": True,
            "environ": self.environ,
        }
        if self.http_client is not None:
            kwargs["http_client"] = self.http_client
        return self.provider_factory(**kwargs)

    def _default_provider_name(self) -> str | None:
        if self.router is None:
            return None
        provider = self.router.get_default_provider()
        if provider is None:
            return None
        return provider.get_info().name

    @staticmethod
    def _error_response(capability: AIProviderCapability, message: str) -> AIResponse:
        return AIResponse(
            text=message,
            provider_name="openai_request_gate",
            model_name="none",
            capability=capability.value,
            safety_level=AIProviderSafetyLevel.EXTERNAL_API.value,
            is_error=True,
            error_message=message,
        )
