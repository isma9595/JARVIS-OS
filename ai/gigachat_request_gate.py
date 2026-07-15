"""One-shot gate for explicit real GigaChat requests."""

from __future__ import annotations

from dataclasses import dataclass, replace
import os

from ai.context_privacy_policy import AIContextPrivacyPolicy, AIContextTarget
from ai.gigachat_cost_guard import GigaChatRequestCostGuard
from ai.gigachat_token_manager import GigaChatTokenManager
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
from ai.providers.gigachat_provider import GigaChatProvider


@dataclass(frozen=True)
class GigaChatRequestGateStatus:
    provider_configured: bool
    key_status: AIProviderKeyStatus
    default_provider_name: str | None
    can_request: bool
    reason: str


class GigaChatRequestGate:
    """Allow exactly one explicit GigaChat request without changing global state."""

    def __init__(
        self,
        config_manager: AIProviderConfigManager | None = None,
        router: AIProviderRouter | None = None,
        provider_factory=None,
        http_client=None,
        token_manager: GigaChatTokenManager | None = None,
        token_http_client=None,
        environ=None,
        request_guard: GigaChatRequestCostGuard | None = None,
        language_policy: AIProviderLanguagePolicy | None = None,
        context_privacy_policy: AIContextPrivacyPolicy | None = None,
    ):
        self.config_manager = config_manager or AIProviderConfigManager(environ=environ)
        self.router = router
        self.provider_factory = provider_factory or GigaChatProvider
        self.http_client = http_client
        self.environ = os.environ if environ is None else environ
        self.request_guard = request_guard or GigaChatRequestCostGuard(environ=self.environ)
        self.language_policy = language_policy or AIProviderLanguagePolicy()
        self.context_privacy_policy = context_privacy_policy or AIContextPrivacyPolicy()
        self.token_manager = token_manager or GigaChatTokenManager(
            environ=self.environ,
            http_client=token_http_client,
            timeout_seconds=self.request_guard.config.timeout_seconds,
        )

    def can_make_real_request(self) -> GigaChatRequestGateStatus:
        status = self.config_manager.status_for("gigachat")
        default_name = self._default_provider_name()
        if status is None:
            return GigaChatRequestGateStatus(
                provider_configured=False,
                key_status=AIProviderKeyStatus.MISSING,
                default_provider_name=default_name,
                can_request=False,
                reason="GigaChat provider config is missing.",
            )
        auth_key = self.environ.get("GIGACHAT_AUTH_KEY")
        if auth_key is None or not str(auth_key).strip():
            return GigaChatRequestGateStatus(
                provider_configured=True,
                key_status=AIProviderKeyStatus.MISSING,
                default_provider_name=default_name,
                can_request=False,
                reason="GIGACHAT_AUTH_KEY is missing.",
            )
        return GigaChatRequestGateStatus(
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

        config = self._temporary_enabled_gigachat_config(guard_result.model)
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
                response.error_message or response.text or "GigaChat request failed.",
            )
        return response

    def status_text_ru(self) -> str:
        status = self.can_make_real_request()
        token_status = self.token_manager.safe_status()
        default_name = status.default_provider_name or "none"
        return "\n".join(
            [
                "GigaChat one-shot real request status:",
                f"- provider config: {'present' if status.provider_configured else 'missing'}",
                f"- enabled: {'enabled' if False else 'disabled'}",
                "- auth env var: GIGACHAT_AUTH_KEY",
                f"- auth key status: {status.key_status.value}",
                f"- scope: {token_status['scope']}",
                f"- model/default model: {self.request_guard.safe_model_display()}",
                "- runtime: DISABLED",
                "- network: disabled except explicit one-shot",
                "- auth key and token values are never printed",
                "- no status network call is made",
                "- GigaChat is not enabled permanently",
                f"- default provider remains: {default_name}",
                f"- can request now: {status.can_request}",
                f"- reason: {status.reason}",
                "- dry_run remains default",
            ]
        )

    def guard_status_text_ru(self) -> str:
        return self.request_guard.status_text_ru()

    def token_status_text_ru(self) -> str:
        return self.token_manager.status_text_ru()

    def model_text_ru(self) -> str:
        return self.request_guard.model_text_ru()

    def request_shape_text_ru(self) -> str:
        config = self._temporary_enabled_gigachat_config(self.request_guard.resolve_model())
        key_value = self.environ.get("GIGACHAT_AUTH_KEY")
        auth_status = "PRESENT" if key_value is not None and str(key_value).strip() else "MISSING"
        return "\n".join(
            [
                "GigaChat request shape:",
                f"- oauth endpoint: {GigaChatTokenManager.OAUTH_ENDPOINT}",
                f"- chat endpoint: {GigaChatProvider.ENDPOINT}",
                "- method: POST",
                f"- model: {config.default_model}",
                f"- scope: {self.token_manager.scope()}",
                f"- max_tokens: {self.request_guard.config.max_output_tokens}",
                "- temperature: 0.2",
                "- oauth headers:",
                "  - Content-Type: application/x-www-form-urlencoded",
                "  - Accept: application/json",
                "  - RqUID: uuid4",
                f"  - Authorization Basic: {auth_status}",
                "- chat headers:",
                "  - Authorization Bearer: token from memory",
                "  - Content-Type: application/json",
                "  - Accept: application/json",
                "  - User-Agent: JARVIS-OS/0.2",
                "- payload fields:",
                "  - model",
                "  - messages",
                "  - max_tokens",
                "  - temperature",
                "- network: not called",
                "- auth key and token values are never printed",
            ]
        )

    def _temporary_enabled_gigachat_config(self, model: str) -> AIProviderConfig:
        config = self.config_manager.get_config("gigachat")
        if config is None:
            config = AIProviderConfig(
                name="gigachat",
                provider_type="gigachat",
                enabled=False,
                default_model=model,
                api_key_env_var="GIGACHAT_AUTH_KEY",
            )
        return replace(
            config,
            name="gigachat",
            provider_type="gigachat",
            enabled=True,
            default_model=model,
            api_key_env_var="GIGACHAT_AUTH_KEY",
        )

    def _build_provider(self, config: AIProviderConfig):
        kwargs = {
            "config": config,
            "token_manager": self.token_manager,
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
            provider_name="gigachat_request_gate",
            model_name="none",
            capability=capability.value,
            safety_level=AIProviderSafetyLevel.EXTERNAL_API.value,
            is_error=True,
            error_message=message,
        )
