"""Safe manual verification helpers for the AI provider layer.

This module is deterministic by default. It never calls external providers,
never stores prompts or responses, and never prints key values. The only
network-capable method is the explicit Ollama localhost readiness check.
"""

from __future__ import annotations

from dataclasses import dataclass

from ai.context_privacy_policy import AIContextPrivacyPolicy, AIContextTarget
from ai.ollama_runtime import OllamaRuntime
from ai.provider_config import AIProviderKeyStatus
from ai.provider_config_manager import AIProviderConfigManager


@dataclass(frozen=True)
class AIProviderVerificationCheck:
    name: str
    status: str
    detail: str
    network_called: bool = False
    safe: bool = True


@dataclass(frozen=True)
class AIProviderVerificationReport:
    ok: bool
    checks: tuple[AIProviderVerificationCheck, ...]
    summary: str


class AIProviderLiveVerification:
    """Render safe diagnostics for manual AI provider verification."""

    LIVE_PROVIDERS = ("openai", "gemini", "groq", "gigachat")

    def __init__(
        self,
        config_manager: AIProviderConfigManager | None = None,
        context_privacy_policy: AIContextPrivacyPolicy | None = None,
        ollama_runtime: OllamaRuntime | None = None,
    ):
        self.config_manager = config_manager or AIProviderConfigManager()
        self.context_privacy_policy = context_privacy_policy or AIContextPrivacyPolicy()
        self.ollama_runtime = ollama_runtime or OllamaRuntime()

    def status_text_ru(self) -> str:
        return "\n".join(
            [
                "AI live verification status:",
                "- enabled: yes",
                "- mode: manual verification helper",
                "- network: not called",
                "- dry_run default: yes",
                "- external providers: explicit-only",
                "- Ollama: local-only",
                "- privacy boundary: active",
                "- fallback: explicit-only",
                "- consensus: explicit-only",
                "- no secrets printed",
                "- no prompt/response storage",
                "- provider responses are not executed as commands",
            ]
        )

    def checklist_text_ru(self) -> str:
        return "\n".join(
            [
                "AI live verification checklist:",
                "- no-key safe mode: run 'проверка ai без ключей'",
                "- Ollama local checklist: run 'проверка ollama local'",
                "- Groq live checklist: set GROQ_API_KEY locally, then run 'проверка live ai readiness'",
                "- GigaChat live checklist: set GIGACHAT_AUTH_KEY locally, then run 'проверка live ai readiness'",
                "- privacy boundary checklist: run 'проверка ai privacy'",
                "- fallback checklist: use 'план ai fallback: <text>' before 'fallback ai запрос: <text>'",
                "- consensus checklist: use 'статус ai consensus' before explicit consensus commands",
                "- voice safety checklist: status/checklist commands may auto-execute; local/live/provider requests require confirmation",
                "- network: not called",
                "- secrets: never paste keys into chat",
                "- no prompt/response storage",
                "- no automatic model pull/download/install",
                "- provider responses are not executed as commands",
            ]
        )

    def no_key_check_text_ru(self) -> str:
        lines = [
            "AI no-key safe mode check:",
            "- network: not called",
            "- key presence only:",
        ]
        for provider in self.LIVE_PROVIDERS:
            status = self.config_manager.status_for(provider)
            key_status = "PRESENT" if self._present(status) else "MISSING"
            env_var = status.api_key_env_var if status else provider.upper()
            lines.append(f"  - {provider}: {key_status} ({env_var})")
        lines.extend(
            [
                "- dry_run default: yes",
                "- ordinary provider commands: no automatic fallback/retry",
                "- fallback explicit command required: fallback ai запрос: <text>",
                "- privacy boundary: active",
                "- no secrets printed",
                "- no prompt/response storage",
                "- provider responses are not executed as commands",
            ]
        )
        return "\n".join(lines)

    def privacy_check_text_ru(self) -> str:
        safe_text = "Скажи коротко: проверка безопасного текста."
        secret_text = "api key sk-test-secret-value-1234567890abcdef"
        private_text = "это приватный вопрос, не отправляй в интернет"
        safe_external = self.context_privacy_policy.decide(
            safe_text,
            AIContextTarget.EXTERNAL_PROVIDER,
        )
        secret_external = self.context_privacy_policy.decide(
            secret_text,
            AIContextTarget.EXTERNAL_PROVIDER,
        )
        private_external = self.context_privacy_policy.decide(
            private_text,
            AIContextTarget.EXTERNAL_PROVIDER,
        )
        consensus_private = self.context_privacy_policy.decide(
            private_text,
            AIContextTarget.CONSENSUS_EXTERNAL,
        )
        return "\n".join(
            [
                "AI privacy verification:",
                "- network: not called",
                "- uses canned safe examples only",
                f"- safe public example external allowed: {safe_external.allowed}",
                f"- secret-like example external allowed: {secret_external.allowed}",
                f"- secret-like redacted preview: {secret_external.redacted_preview}",
                f"- private example external allowed: {private_external.allowed}",
                f"- consensus private example allowed: {consensus_private.allowed}",
                "- external providers are blocked for private/secret context",
                "- no real provider called",
                "- no raw secret value printed",
                "- no prompt/response storage",
                "- provider responses are not executed as commands",
            ]
        )

    def live_readiness_text_ru(self) -> str:
        lines = [
            "AI live readiness:",
            "- network: not called",
            "- key presence only:",
        ]
        for provider in self.LIVE_PROVIDERS:
            status = self.config_manager.status_for(provider)
            key_status = "PRESENT" if self._present(status) else "MISSING"
            env_var = status.api_key_env_var if status else provider.upper()
            lines.append(f"  - {provider}: {key_status} ({env_var})")
        lines.extend(
            [
                "- provider statuses: safe; no key values printed",
                "- do not paste keys into chat",
                "- exact manual commands if keys/local model are present:",
                "  - groq реальный запрос: Скажи одним коротким предложением: Groq работает?",
                "  - gigachat реальный запрос: Скажи одним коротким предложением: GigaChat работает?",
                "  - ollama реальный запрос: Скажи одним коротким предложением: локальный AI работает?",
                "  - fallback ai запрос: обычный короткий вопрос",
                "- external providers remain explicit-only",
                "- dry_run remains default",
                "- no prompt/response storage",
                "- provider responses are not executed as commands",
            ]
        )
        return "\n".join(lines)

    def local_check_text_ru(self) -> str:
        status = self.ollama_runtime.status(check_models=True)
        installed = ", ".join(status.installed_models) if status.installed_models else "none"
        return "\n".join(
            [
                "Ollama local readiness check:",
                "- explicit local-only check: yes",
                "- network scope: localhost-only /api/tags",
                "- external network called: False",
                "- no pull/download/install",
                "- no cloud",
                "- no keys",
                f"- base_url: {status.base_url}",
                f"- configured model: {status.model}",
                f"- server reachable: {status.server_reachable}",
                f"- configured model installed: {status.model_installed}",
                f"- installed models: {installed}",
                f"- status: {status.safe_message}",
                "- no prompt/response storage",
                "- provider responses are not executed as commands",
            ]
        )

    @staticmethod
    def _present(status) -> bool:
        return bool(status and status.key_status == AIProviderKeyStatus.PRESENT)
