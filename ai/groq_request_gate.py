"""One-shot gate for explicit real Groq requests."""

from __future__ import annotations

from dataclasses import dataclass, replace
import os

from ai.groq_cost_guard import GroqRequestCostGuard
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
from ai.providers.groq_provider import GroqProvider


@dataclass(frozen=True)
class GroqRequestGateStatus:
    provider_configured: bool
    key_status: AIProviderKeyStatus
    default_provider_name: str | None
    can_request: bool
    reason: str


class GroqRequestGate:
    """Allow exactly one explicit Groq request without changing global state."""

    def __init__(
        self,
        config_manager: AIProviderConfigManager | None = None,
        router: AIProviderRouter | None = None,
        provider_factory=None,
        http_client=None,
        environ=None,
        request_guard: GroqRequestCostGuard | None = None,
        language_policy: AIProviderLanguagePolicy | None = None,
    ):
        self.config_manager = config_manager or AIProviderConfigManager(environ=environ)
        self.router = router
        self.provider_factory = provider_factory or GroqProvider
        self.http_client = http_client
        self.environ = os.environ if environ is None else environ
        self.request_guard = request_guard or GroqRequestCostGuard(environ=self.environ)
        self.language_policy = language_policy or AIProviderLanguagePolicy()

    def can_make_real_request(self) -> GroqRequestGateStatus:
        status = self.config_manager.status_for("groq")
        default_name = self._default_provider_name()
        if status is None:
            return GroqRequestGateStatus(
                provider_configured=False,
                key_status=AIProviderKeyStatus.MISSING,
                default_provider_name=default_name,
                can_request=False,
                reason="Groq provider config is missing.",
            )
        real_key = self.environ.get("GROQ_API_KEY")
        if real_key is None or not str(real_key).strip():
            return GroqRequestGateStatus(
                provider_configured=True,
                key_status=AIProviderKeyStatus.MISSING,
                default_provider_name=default_name,
                can_request=False,
                reason="GROQ_API_KEY is missing.",
            )
        return GroqRequestGateStatus(
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
    ) -> AIResponse:
        validation_error = request.validation_error()
        if validation_error:
            return self._error_response(capability, validation_error)

        guard_result = self.request_guard.guard_request(
            request.prompt,
            request.metadata.get("max_output_tokens") if request.metadata else None,
        )
        if not guard_result.allowed:
            return self._error_response(capability, guard_result.safe_message)

        gate_status = self.can_make_real_request()
        if not gate_status.can_request:
            return self._error_response(capability, gate_status.reason)

        config = self._temporary_enabled_groq_config(guard_result.model)
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
                response.error_message or response.text or "Groq request failed.",
            )
        return response

    def status_text_ru(self) -> str:
        status = self.can_make_real_request()
        default_name = status.default_provider_name or "none"
        return "\n".join(
            [
                "Groq one-shot real request status:",
                f"- provider config: {'present' if status.provider_configured else 'missing'}",
                f"- key status: {status.key_status.value}",
                "- key value is never printed",
                f"- model guard: {self.request_guard.safe_model_display()}",
                f"- max prompt chars: {self.request_guard.config.max_prompt_chars}",
                f"- max_tokens: {self.request_guard.config.max_output_tokens}",
                "- network: allowed only by explicit one-shot typed command",
                "- Groq is not enabled permanently",
                f"- default provider remains: {default_name}",
                f"- can request now: {status.can_request}",
                f"- reason: {status.reason}",
            ]
        )

    def guard_status_text_ru(self) -> str:
        return self.request_guard.status_text_ru()

    def model_text_ru(self) -> str:
        return self.request_guard.model_text_ru()

    def request_shape_text_ru(self) -> str:
        config = self._temporary_enabled_groq_config(self.request_guard.resolve_model())
        key_value = self.environ.get(config.api_key_env_var or "GROQ_API_KEY")
        auth_status = "PRESENT" if key_value is not None and str(key_value).strip() else "MISSING"
        return "\n".join(
            [
                "Groq request shape:",
                f"- endpoint: {GroqProvider.ENDPOINT}",
                "- method: POST",
                f"- model: {config.default_model}",
                f"- max_tokens: {self.request_guard.config.max_output_tokens}",
                "- temperature: 0.2",
                "- headers:",
                f"  - Authorization: {auth_status}",
                "  - Content-Type: application/json",
                "  - Accept: application/json",
                "  - User-Agent: JARVIS-OS/0.2",
                "- payload fields:",
                "  - model",
                "  - messages",
                "  - max_tokens",
                "  - temperature",
                "- network: not called",
                "- key value is never printed",
            ]
        )

    def _temporary_enabled_groq_config(self, model: str) -> AIProviderConfig:
        config = self.config_manager.get_config("groq")
        if config is None:
            config = AIProviderConfig(
                name="groq",
                provider_type="groq",
                enabled=False,
                default_model=model,
                api_key_env_var="GROQ_API_KEY",
            )
        return replace(
            config,
            name="groq",
            provider_type="groq",
            enabled=True,
            default_model=model,
            api_key_env_var="GROQ_API_KEY",
        )

    def _build_provider(self, config: AIProviderConfig):
        kwargs = {
            "config": config,
            "allow_network": True,
            "environ": self.environ,
            "timeout_seconds": self.request_guard.config.timeout_seconds,
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
            provider_name="groq_request_gate",
            model_name="none",
            capability=capability.value,
            safety_level=AIProviderSafetyLevel.EXTERNAL_API.value,
            is_error=True,
            error_message=message,
        )
