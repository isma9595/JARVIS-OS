"""Explicit-only controlled AI provider fallback executor.

This module does not persist prompts or responses, does not execute provider
responses as commands, and does not implement raw provider HTTP calls.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ai.context_privacy_policy import (
    AIContextPrivacyPolicy,
    AIContextSensitivity,
    AIContextTarget,
)
from ai.provider_config import AIProviderKeyStatus
from ai.provider_config_manager import AIProviderConfigManager
from ai.provider_contracts import AIProviderCapability, AIRequest, AIResponse
from ai.provider_selection_policy import AIProviderSelectionPolicy
from ai.providers.dry_run_provider import DryRunAIProvider


class AIProviderAttemptStatus(str, Enum):
    SKIPPED = "SKIPPED"
    BLOCKED_BY_PRIVACY = "BLOCKED_BY_PRIVACY"
    MISSING_KEY = "MISSING_KEY"
    UNAVAILABLE = "UNAVAILABLE"
    FAILED = "FAILED"
    SUCCEEDED = "SUCCEEDED"


@dataclass(frozen=True)
class AIProviderFallbackAttempt:
    provider: str
    model: str | None
    status: str
    reason: str
    network_scope: str
    safe_error: str | None = None


@dataclass(frozen=True)
class AIProviderFallbackPlan:
    prompt_preview: str
    task_type: str
    chain: tuple[str, ...]
    reason: str
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class AIProviderFallbackResult:
    ok: bool
    final_provider: str | None
    final_model: str | None
    answer: str
    attempts: tuple[AIProviderFallbackAttempt, ...]
    safe_summary: str
    network_called: bool
    dry_run_default_unchanged: bool
    response_executed: bool = False


class AIProviderFallbackExecutor:
    """Run a bounded fallback chain only after an explicit fallback command."""

    EXTERNAL_PROVIDERS = {"groq", "gigachat", "openai", "gemini"}
    MAX_ATTEMPTS = 6

    def __init__(
        self,
        config_manager: AIProviderConfigManager | None = None,
        selection_policy: AIProviderSelectionPolicy | None = None,
        context_privacy_policy: AIContextPrivacyPolicy | None = None,
        request_gates: dict[str, object] | None = None,
        dry_run_provider: DryRunAIProvider | None = None,
    ):
        self.config_manager = config_manager or AIProviderConfigManager()
        self.context_privacy_policy = context_privacy_policy or AIContextPrivacyPolicy()
        self.selection_policy = selection_policy or AIProviderSelectionPolicy(
            config_manager=self.config_manager,
            context_privacy_policy=self.context_privacy_policy,
        )
        self.request_gates = dict(request_gates or {})
        self.dry_run_provider = dry_run_provider or DryRunAIProvider()

    def status_text_ru(self) -> str:
        return "\n".join(
            [
                "AI fallback execution status:",
                "- enabled: yes",
                "- mode: explicit only",
                "- ordinary provider commands: no automatic retry",
                "- privacy boundary: enforced",
                "- language policy: enforced by provider gates",
                "- session pinning: respected but not allowed to bypass privacy",
                "- consensus: separate explicit mode",
                "- dry_run remains default",
                "- network: not called",
                "- prompts/responses not stored",
                "- responses not executed",
            ]
        )

    def build_plan(self, prompt: str, session_snapshot=None) -> AIProviderFallbackPlan:
        preview = self.context_privacy_policy.redacted_preview(prompt)
        sensitivity = self.context_privacy_policy.classify_text(prompt)
        task_type = self.selection_policy.classify_task(prompt)
        chain = self._build_chain(task_type, sensitivity, session_snapshot)
        if sensitivity == AIContextSensitivity.SECRET_LIKE:
            reason = "secret-like context detected; real and local providers will be blocked"
        elif sensitivity in {
            AIContextSensitivity.PRIVATE_OR_PERSONAL,
            AIContextSensitivity.FILE_PATH_REFERENCE,
        }:
            reason = "private/offline context detected; external providers are blocked"
        else:
            reason = f"deterministic fallback chain for {task_type} task"
        return AIProviderFallbackPlan(
            prompt_preview=preview,
            task_type=task_type,
            chain=chain,
            reason=reason,
            warnings=(
                "explicit fallback command required for execution",
                "plan does not call provider network",
                "privacy preflight runs before every provider",
                "dry_run remains the terminal fallback",
                "provider responses are not executed as commands",
            ),
        )

    def plan_text_ru(self, prompt: str, session_snapshot=None) -> str:
        plan = self.build_plan(prompt, session_snapshot=session_snapshot)
        lines = [
            "AI fallback execution plan:",
            "- network: not called",
            f"- redacted preview: {plan.prompt_preview}",
            f"- task type: {plan.task_type}",
            f"- planned chain: {' -> '.join(plan.chain)}",
            f"- reason: {plan.reason}",
            "- obvious provider readiness:",
        ]
        for provider in plan.chain:
            lines.append(f"  - {provider}: {self._plan_provider_note(provider, prompt)}")
        lines.extend(
            [
                "- warnings:",
                *(f"  - {warning}" for warning in plan.warnings),
                "- safe next command: fallback ai запрос: <text>",
                "- prompt was analyzed in memory only and was not stored",
            ]
        )
        return "\n".join(lines)

    def execute(self, prompt: str, session_snapshot=None) -> AIProviderFallbackResult:
        plan = self.build_plan(prompt, session_snapshot=session_snapshot)
        attempts: list[AIProviderFallbackAttempt] = []
        network_called = False
        answer = ""
        final_provider = None
        final_model = None

        for provider in plan.chain:
            if provider == "dry_run":
                response = self._run_dry_run(prompt)
                status = (
                    AIProviderAttemptStatus.FAILED
                    if response.is_error
                    else AIProviderAttemptStatus.SUCCEEDED
                )
                attempts.append(
                    AIProviderFallbackAttempt(
                        provider="dry_run",
                        model=response.model_name,
                        status=status.value,
                        reason="terminal offline fallback",
                        network_scope="none",
                        safe_error=(
                            self._safe_error(response.error_message or response.text)
                            if response.is_error
                            else None
                        ),
                    )
                )
                if not response.is_error:
                    answer = response.text
                    final_provider = "dry_run"
                    final_model = response.model_name
                    break
                continue

            privacy = self._privacy_decision(prompt, provider)
            if not privacy.allowed:
                attempts.append(
                    AIProviderFallbackAttempt(
                        provider=provider,
                        model=self._default_model(provider),
                        status=AIProviderAttemptStatus.BLOCKED_BY_PRIVACY.value,
                        reason=privacy.reason,
                        network_scope=self._network_scope(provider),
                        safe_error=self._safe_error(privacy.safe_alternative or privacy.reason),
                    )
                )
                continue

            if provider in self.EXTERNAL_PROVIDERS and not self._key_present(provider):
                attempts.append(
                    AIProviderFallbackAttempt(
                        provider=provider,
                        model=self._default_model(provider),
                        status=AIProviderAttemptStatus.MISSING_KEY.value,
                        reason=f"{self._key_env_var(provider)} is missing",
                        network_scope="external",
                        safe_error=None,
                    )
                )
                continue

            gate = self.request_gates.get(provider)
            if gate is None or not hasattr(gate, "generate_one_shot"):
                attempts.append(
                    AIProviderFallbackAttempt(
                        provider=provider,
                        model=self._default_model(provider),
                        status=AIProviderAttemptStatus.UNAVAILABLE.value,
                        reason="provider gate is unavailable",
                        network_scope=self._network_scope(provider),
                        safe_error=None,
                    )
                )
                continue

            network_called = True
            response = gate.generate_one_shot(
                AIRequest(
                    prompt=prompt,
                    task_type=AIProviderCapability.CHAT.value,
                    language="ru",
                ),
                capability=AIProviderCapability.CHAT,
                model_override=self._manual_model_for(provider, session_snapshot),
            )
            if response.is_error:
                attempts.append(
                    AIProviderFallbackAttempt(
                        provider=provider,
                        model=response.model_name or self._default_model(provider),
                        status=self._failed_status(provider, response).value,
                        reason="provider did not return a usable answer",
                        network_scope=self._network_scope(provider),
                        safe_error=self._safe_error(response.error_message or response.text),
                    )
                )
                continue

            attempts.append(
                AIProviderFallbackAttempt(
                    provider=provider,
                    model=response.model_name,
                    status=AIProviderAttemptStatus.SUCCEEDED.value,
                    reason="first successful provider answer",
                    network_scope=self._network_scope(provider),
                    safe_error=None,
                )
            )
            answer = response.text
            final_provider = provider
            final_model = response.model_name
            break

        ok = final_provider is not None
        safe_summary = self._summary(ok, final_provider, attempts)
        return AIProviderFallbackResult(
            ok=ok,
            final_provider=final_provider,
            final_model=final_model,
            answer=answer,
            attempts=tuple(attempts),
            safe_summary=safe_summary,
            network_called=network_called,
            dry_run_default_unchanged=True,
            response_executed=False,
        )

    def result_text_ru(self, result: AIProviderFallbackResult) -> str:
        lines = [
            "AI fallback execution result:",
            f"- ok: {result.ok}",
            f"- final provider: {result.final_provider or 'none'}",
            f"- final model: {result.final_model or 'none'}",
            f"- network_called: {result.network_called}",
            f"- dry_run_default_unchanged: {result.dry_run_default_unchanged}",
            f"- response_executed: {result.response_executed}",
            "- attempts:",
        ]
        for attempt in result.attempts:
            line = (
                f"  - {attempt.provider}: status={attempt.status}; "
                f"model={attempt.model or 'none'}; network_scope={attempt.network_scope}; "
                f"reason={attempt.reason}"
            )
            if attempt.safe_error:
                line += f"; safe_error={attempt.safe_error}"
            lines.append(line)
        lines.extend(
            [
                "- answer:",
                result.answer or "No provider returned an answer.",
                "",
                "Safety footer:",
                "- explicit fallback command was required",
                "- ordinary provider commands do not auto-retry",
                "- privacy boundary was enforced before provider calls",
                "- language policy stayed inside provider gates",
                "- consensus was not invoked",
                "- prompts/responses were not stored to disk",
                "- secrets/keys/tokens were not printed",
                "- response was not executed as a command",
                result.safe_summary,
            ]
        )
        return "\n".join(lines)

    def _build_chain(self, task_type: str, sensitivity, session_snapshot) -> tuple[str, ...]:
        if sensitivity in {
            AIContextSensitivity.PRIVATE_OR_PERSONAL,
            AIContextSensitivity.FILE_PATH_REFERENCE,
        }:
            base = ("ollama", "dry_run")
        elif task_type == "russian":
            base = ("gigachat", "groq", "openai", "gemini", "ollama", "dry_run")
        elif task_type == "code":
            base = ("openai", "groq", "gemini", "gigachat", "ollama", "dry_run")
        else:
            base = ("groq", "gigachat", "openai", "gemini", "ollama", "dry_run")

        manual = self._manual_provider(session_snapshot)
        ordered = (manual, *base) if manual else base
        unique = []
        for provider in ordered:
            normalized = str(provider or "").strip().lower()
            if normalized and normalized not in unique:
                unique.append(normalized)
            if len(unique) >= self.MAX_ATTEMPTS:
                break
        if "dry_run" not in unique:
            unique[-1:] = ["dry_run"]
        return tuple(unique)

    def _privacy_decision(self, prompt: str, provider: str):
        if provider == "ollama":
            return self.context_privacy_policy.decide(prompt, AIContextTarget.LOCAL_OLLAMA)
        return self.context_privacy_policy.decide(prompt, AIContextTarget.EXTERNAL_PROVIDER)

    def _run_dry_run(self, prompt: str) -> AIResponse:
        safe_prompt = self.context_privacy_policy.redacted_preview(prompt)
        return self.dry_run_provider.generate(
            AIRequest(
                prompt=safe_prompt,
                task_type=AIProviderCapability.CHAT.value,
                language="ru",
            )
        )

    def _plan_provider_note(self, provider: str, prompt: str) -> str:
        if provider == "dry_run":
            return "offline terminal fallback"
        privacy = self._privacy_decision(prompt, provider)
        if not privacy.allowed:
            return f"blocked by privacy boundary ({privacy.sensitivity})"
        if provider in self.EXTERNAL_PROVIDERS and not self._key_present(provider):
            return f"key MISSING ({self._key_env_var(provider)})"
        if provider == "ollama":
            return "local runtime/model checked only during explicit execution"
        return "eligible if provider gate succeeds"

    def _key_present(self, provider: str) -> bool:
        status = self.config_manager.status_for(provider)
        return bool(status and status.key_status == AIProviderKeyStatus.PRESENT)

    def _key_env_var(self, provider: str) -> str:
        status = self.config_manager.status_for(provider)
        return (status.api_key_env_var if status else None) or "key"

    def _default_model(self, provider: str) -> str | None:
        status = self.config_manager.status_for(provider)
        if status is not None:
            return status.default_model
        role_by_provider = {role.provider: role for role in self.selection_policy.roles()}
        role = role_by_provider.get(provider)
        return role.default_model if role else None

    @staticmethod
    def _network_scope(provider: str) -> str:
        if provider == "ollama":
            return "localhost-only"
        if provider == "dry_run":
            return "none"
        return "external"

    @staticmethod
    def _manual_provider(session_snapshot) -> str | None:
        if (
            session_snapshot is not None
            and getattr(session_snapshot, "selection_mode", None) == "manual"
            and getattr(session_snapshot, "selected_provider", None)
        ):
            return str(session_snapshot.selected_provider).strip().lower()
        return None

    @staticmethod
    def _manual_model_for(provider: str, session_snapshot) -> str | None:
        if (
            session_snapshot is not None
            and getattr(session_snapshot, "selection_mode", None) == "manual"
            and str(getattr(session_snapshot, "selected_provider", "")).strip().lower()
            == provider
        ):
            return getattr(session_snapshot, "selected_model", None)
        return None

    @staticmethod
    def _failed_status(provider: str, response: AIResponse) -> AIProviderAttemptStatus:
        error = str(response.error_message or response.text or "").lower()
        if provider == "ollama" and (
            "unavailable" in error
            or "not installed" in error
            or "not running" in error
            or "server" in error
        ):
            return AIProviderAttemptStatus.UNAVAILABLE
        return AIProviderAttemptStatus.FAILED

    def _safe_error(self, text: str | None) -> str | None:
        if not text:
            return None
        return self.context_privacy_policy.redacted_preview(str(text), limit=220)

    @staticmethod
    def _summary(ok: bool, final_provider: str | None, attempts) -> str:
        if ok:
            return f"Fallback stopped at first successful provider: {final_provider}."
        return f"Fallback ended without a provider answer after {len(attempts)} bounded attempts."
