"""Explicit multi-provider AI consensus mode.

Consensus is intentionally opt-in. It calls only existing one-shot provider
gates, keeps all data in memory, and synthesizes a deterministic text summary.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
import re
from typing import Callable

from ai.provider_config import AIProviderKeyStatus
from ai.provider_config_manager import AIProviderConfigManager
from ai.provider_contracts import AIProviderCapability, AIRequest, AIResponse


@dataclass(frozen=True)
class AIProviderConsensusConfig:
    enabled: bool = True
    provider_order: tuple[str, ...] = ("groq", "gigachat", "openai", "gemini")
    max_prompt_chars: int = 1200
    max_answer_chars_per_provider: int = 1200
    max_final_chars: int = 2500
    require_explicit_command: bool = True
    warn_multiple_quotas: bool = True


@dataclass(frozen=True)
class AIProviderConsensusProviderResult:
    provider: str
    model: str | None
    attempted: bool
    succeeded: bool
    skipped: bool
    safe_status: str
    answer: str | None
    error: str | None


@dataclass(frozen=True)
class AIProviderConsensusResult:
    ok: bool
    prompt_preview: str
    attempted_count: int
    success_count: int
    skipped_count: int
    provider_results: list[AIProviderConsensusProviderResult]
    final_answer: str
    safety_footer: str


class AIProviderConsensusManager:
    """Run explicit consensus requests through existing external one-shot gates."""

    PROVIDER_ENV_VARS = {
        "groq": "GROQ_API_KEY",
        "gigachat": "GIGACHAT_AUTH_KEY",
        "openai": "OPENAI_API_KEY",
        "gemini": "GEMINI_API_KEY",
    }

    def __init__(
        self,
        config: AIProviderConsensusConfig | None = None,
        config_manager: AIProviderConfigManager | None = None,
        request_gates: dict[str, object] | None = None,
        provider_callers: dict[str, Callable[[AIRequest], AIResponse]] | None = None,
        environ=None,
    ):
        self.config = config or AIProviderConsensusConfig()
        self.environ = os.environ if environ is None else environ
        self.config_manager = config_manager or AIProviderConfigManager(
            environ=self.environ
        )
        self.request_gates = request_gates or {}
        self.provider_callers = provider_callers or {}

    def status_text_ru(self) -> str:
        providers = ", ".join(self.config.provider_order)
        return "\n".join(
            [
                "AI consensus status:",
                f"- enabled: {'yes' if self.config.enabled else 'no'}",
                "- mode: explicit only",
                f"- providers considered: {providers}",
                "- dry_run: not included as real consensus provider",
                "- multiple provider quotas may be used only after explicit command",
                "- memory/profile/files/logs not sent",
                "- responses not executed as commands",
                "- network: not called",
                "- prompts/responses are not stored to disk",
                "- key/token values are never printed",
            ]
        )

    def run_consensus(self, prompt: str) -> AIProviderConsensusResult:
        validation_error = self._validate_prompt(prompt)
        if validation_error:
            return self._blocked_result(prompt, validation_error)

        results: list[AIProviderConsensusProviderResult] = []
        for provider in self.config.provider_order:
            if not self._has_required_key(provider):
                results.append(
                    AIProviderConsensusProviderResult(
                        provider=provider,
                        model=self._safe_default_model(provider),
                        attempted=False,
                        succeeded=False,
                        skipped=True,
                        safe_status="skipped_missing_key",
                        answer=None,
                        error=f"{self.PROVIDER_ENV_VARS[provider]} is missing.",
                    )
                )
                continue
            results.append(self._attempt_provider(provider, prompt))

        attempted_count = sum(1 for result in results if result.attempted)
        success_count = sum(1 for result in results if result.succeeded)
        skipped_count = sum(1 for result in results if result.skipped)
        final_answer = self._synthesize(prompt, results)
        ok = success_count > 0
        if attempted_count == 0:
            final_answer = (
                "Consensus request was not sent. No external provider keys are present."
            )
            ok = False
        elif success_count == 0:
            final_answer = (
                "Consensus request completed without a synthesized answer: all attempted "
                "providers failed safely."
            )
            ok = False

        return AIProviderConsensusResult(
            ok=ok,
            prompt_preview=self._cap_text(prompt.strip(), 180),
            attempted_count=attempted_count,
            success_count=success_count,
            skipped_count=skipped_count,
            provider_results=results,
            final_answer=self._cap_text(final_answer, self.config.max_final_chars),
            safety_footer=self._safety_footer(attempted_count, success_count),
        )

    def format_result_text(self, result: AIProviderConsensusResult) -> str:
        lines = [
            "Consensus status summary:",
            f"- ok: {result.ok}",
            f"- prompt preview: {result.prompt_preview}",
            f"- providers attempted: {result.attempted_count}",
            f"- successful providers: {result.success_count}",
            f"- skipped providers: {result.skipped_count}",
            "- warning: multiple provider quotas/rate limits may be used",
            "",
            "Provider results:",
        ]
        for provider_result in result.provider_results:
            model = provider_result.model or "unknown"
            lines.append(
                f"- {provider_result.provider}: status={provider_result.safe_status}; "
                f"model={model}; attempted={provider_result.attempted}; "
                f"succeeded={provider_result.succeeded}"
            )
            if provider_result.answer:
                lines.append(f"  answer: {provider_result.answer}")
            if provider_result.error:
                lines.append(f"  error: {provider_result.error}")

        lines.extend(
            [
                "",
                "JARVIS final synthesized answer:",
                result.final_answer or "No final synthesized answer was produced.",
                "",
                "Safety footer:",
                result.safety_footer,
            ]
        )
        return "\n".join(lines)

    def _attempt_provider(
        self, provider: str, prompt: str
    ) -> AIProviderConsensusProviderResult:
        request = AIRequest(
            prompt=prompt,
            task_type=AIProviderCapability.CHAT.value,
            language="ru",
        )
        try:
            response = self._call_provider(provider, request)
        except Exception as exc:
            return AIProviderConsensusProviderResult(
                provider=provider,
                model=self._safe_default_model(provider),
                attempted=True,
                succeeded=False,
                skipped=False,
                safe_status="failed",
                answer=None,
                error=self._safe_error(exc),
            )

        model = self._safe_text(response.model_name) or self._safe_default_model(provider)
        if response.is_error:
            return AIProviderConsensusProviderResult(
                provider=provider,
                model=model,
                attempted=True,
                succeeded=False,
                skipped=False,
                safe_status="failed",
                answer=None,
                error=self._safe_error(response.error_message or response.text),
            )

        return AIProviderConsensusProviderResult(
            provider=provider,
            model=model,
            attempted=True,
            succeeded=True,
            skipped=False,
            safe_status="success",
            answer=self._cap_text(
                self._safe_text(response.text), self.config.max_answer_chars_per_provider
            ),
            error=None,
        )

    def _call_provider(self, provider: str, request: AIRequest) -> AIResponse:
        caller = self.provider_callers.get(provider)
        if caller is not None:
            return caller(request)

        gate = self.request_gates.get(provider)
        if gate is None:
            raise RuntimeError(f"{provider} consensus gate is not configured.")
        return gate.generate_one_shot(
            request,
            capability=AIProviderCapability.CHAT,
        )

    def _synthesize(
        self, prompt: str, results: list[AIProviderConsensusProviderResult]
    ) -> str:
        successful = [result for result in results if result.succeeded and result.answer]
        if not successful:
            return ""
        if len(successful) == 1:
            only = successful[0]
            failed = [
                result.provider
                for result in results
                if result.skipped or (result.attempted and not result.succeeded)
            ]
            failed_text = ", ".join(failed) if failed else "none"
            return (
                "Синтезированный ответ JARVIS на основе доступных ответов провайдеров.\n"
                "only one provider succeeded.\n"
                "Успешно ответил только один провайдер, поэтому это лучший доступный "
                f"ответ без межпровайдерского сравнения.\n\n"
                f"Лучший доступный ответ ({only.provider}):\n{only.answer}\n\n"
                f"Пропущены или завершились ошибкой: {failed_text}."
            )

        common_terms = self._common_terms([result.answer or "" for result in successful])
        common_text = (
            ", ".join(common_terms[:10])
            if common_terms
            else "явных общих формулировок мало; ответы дополняют друг друга"
        )
        differences = "; ".join(
            f"{result.provider}: {self._cap_text(result.answer or '', 260)}"
            for result in successful
        )
        base = successful[0]
        other_names = ", ".join(result.provider for result in successful[1:])
        return (
            "Синтезированный ответ JARVIS на основе доступных ответов провайдеров.\n\n"
            f"Общие точки: {common_text}.\n\n"
            f"Различия и акценты: {differences}.\n\n"
            "Конфликты или неопределённости: если формулировки расходятся, "
            "используйте их как неподтверждённые различия, потому что JARVIS не "
            "добавляет факты вне полученных ответов.\n\n"
            f"Итоговая рекомендация: взять за основу ответ {base.provider}: "
            f"{self._cap_text(base.answer or '', 700)}"
            f" Дополнительные акценты сверить по ответам: {other_names}."
        )

    def _blocked_result(self, prompt: str, reason: str) -> AIProviderConsensusResult:
        return AIProviderConsensusResult(
            ok=False,
            prompt_preview=self._cap_text(str(prompt or "").strip(), 180),
            attempted_count=0,
            success_count=0,
            skipped_count=0,
            provider_results=[],
            final_answer=f"Consensus request was not sent. Reason: {reason}",
            safety_footer=self._safety_footer(0, 0, completed=False),
        )

    def _validate_prompt(self, prompt: str) -> str | None:
        if not self.config.enabled:
            return "consensus mode is disabled."
        if not isinstance(prompt, str) or not prompt.strip():
            return "AI consensus prompt is empty."
        if len(prompt.strip()) > self.config.max_prompt_chars:
            return (
                f"AI consensus prompt is too long; max {self.config.max_prompt_chars} chars."
            )
        return None

    def _has_required_key(self, provider: str) -> bool:
        status = self.config_manager.status_for(provider)
        if status is not None:
            return status.key_status == AIProviderKeyStatus.PRESENT
        env_var = self.PROVIDER_ENV_VARS.get(provider)
        if env_var is None:
            return False
        value = self.environ.get(env_var)
        return value is not None and bool(str(value).strip())

    def _safe_default_model(self, provider: str) -> str | None:
        status = self.config_manager.status_for(provider)
        if status is None:
            return None
        return self._safe_text(status.default_model)

    def _safe_error(self, value) -> str:
        text = self._safe_text(value)
        for env_var in self.PROVIDER_ENV_VARS.values():
            secret = self.environ.get(env_var)
            if secret is not None and len(str(secret)) >= 4:
                text = text.replace(str(secret), "[REDACTED]")
        text = re.sub(r"(api[_-]?key|token|auth[_-]?key)\s*[:=]\s*\S+", r"\1=[REDACTED]", text, flags=re.IGNORECASE)
        return self._cap_text(text or "provider failed safely.", 240)

    @staticmethod
    def _safe_text(value) -> str:
        text = str(value or "").replace("\r", " ").replace("\n", " ").strip()
        return " ".join(text.split())

    @staticmethod
    def _cap_text(text: str, limit: int) -> str:
        safe = str(text or "").strip()
        if len(safe) <= limit:
            return safe
        return safe[: max(0, limit - 15)].rstrip() + "... [truncated]"

    @staticmethod
    def _common_terms(answers: list[str]) -> list[str]:
        stop_words = {
            "это",
            "для",
            "что",
            "как",
            "или",
            "при",
            "the",
            "and",
            "that",
            "with",
            "from",
            "this",
        }
        counts: dict[str, int] = {}
        for answer in answers:
            words = {
                word
                for word in re.findall(r"[\wА-Яа-яЁё]{4,}", answer.lower())
                if word not in stop_words
            }
            for word in words:
                counts[word] = counts.get(word, 0) + 1
        return sorted(word for word, count in counts.items() if count >= 2)

    @staticmethod
    def _safety_footer(attempted_count: int, success_count: int, completed=True) -> str:
        first = (
            "- explicit consensus request completed"
            if completed
            else "- explicit consensus request was not sent"
        )
        return "\n".join(
            [
                first,
                f"- providers attempted: {attempted_count}",
                f"- successful providers: {success_count}",
                "- dry_run remains default",
                "- external providers were not enabled permanently",
                "- responses were not executed as commands",
                "- key/token values were not printed",
                "- no memory/profile/files/logs were sent automatically",
                "- multiple provider quotas/rate limits may be used",
            ]
        )
