"""Deterministic AI provider selection policy.

This module is recommendation-only. It never calls provider APIs, never writes
prompts or responses to disk, and only reports key presence as PRESENT/MISSING.
"""

from __future__ import annotations

from dataclasses import dataclass
import os

from ai.provider_config import AIProviderKeyStatus
from ai.provider_config_manager import AIProviderConfigManager


@dataclass(frozen=True)
class AIProviderRole:
    provider: str
    default_model: str | None
    role: str
    strengths: tuple[str, ...]
    weaknesses: tuple[str, ...]
    safety_level: str
    requires_key: bool
    env_var: str | None
    implemented: bool
    network_capable: bool


@dataclass(frozen=True)
class AIProviderSelectionRequest:
    prompt: str
    task_type: str | None = None
    prefer_private: bool = False
    prefer_fast: bool = False
    prefer_russian: bool = False
    prefer_strong_reasoning: bool = False
    prefer_code: bool = False
    prefer_consensus: bool = False
    continuation: bool = False


@dataclass(frozen=True)
class AIProviderSelectionRecommendation:
    ok: bool
    recommended_provider: str
    recommended_model: str | None
    reason: str
    fallback_chain: list[str]
    skipped: list[str]
    warnings: list[str]
    network_called: bool = False
    dry_run_default_unchanged: bool = True


class AIProviderSelectionPolicy:
    """Recommend providers from safe metadata only."""

    PROVIDER_ORDER = ("dry_run", "groq", "gigachat", "openai", "gemini", "ollama")
    EXTERNAL_ORDER = ("groq", "gigachat", "openai", "gemini")

    def __init__(
        self,
        config_manager: AIProviderConfigManager | None = None,
        environ=None,
    ):
        self.environ = os.environ if environ is None else environ
        self.config_manager = config_manager or AIProviderConfigManager(
            environ=self.environ
        )

    def roles(self) -> tuple[AIProviderRole, ...]:
        configured = {
            status.name: status for status in self.config_manager.statuses()
        }

        def model(provider: str, fallback: str | None):
            status = configured.get(provider)
            return status.default_model if status is not None else fallback

        return (
            AIProviderRole(
                provider="dry_run",
                default_model=model("dry_run", "jarvis-dry-run-v0"),
                role="offline deterministic default",
                strengths=("safety", "no key", "no network", "predictable tests"),
                weaknesses=("not real intelligence", "limited answer quality"),
                safety_level="offline_deterministic",
                requires_key=False,
                env_var=None,
                implemented=True,
                network_capable=False,
            ),
            AIProviderRole(
                provider="groq",
                default_model=model("groq", "llama-3.1-8b-instant"),
                role="fast external model",
                strengths=(
                    "speed",
                    "concise answers",
                    "good general use",
                    "useful first external fallback",
                ),
                weaknesses=("external network", "quota/rate limits", "not private/offline"),
                safety_level="explicit_one_shot_external",
                requires_key=True,
                env_var="GROQ_API_KEY",
                implemented=True,
                network_capable=True,
            ),
            AIProviderRole(
                provider="gigachat",
                default_model=model("gigachat", "GigaChat"),
                role="Russian/Russia-friendly external fallback",
                strengths=(
                    "Russian language",
                    "Russia-friendly ecosystem",
                    "useful alternative to Groq",
                ),
                weaknesses=("external network", "token flow", "quota/rate limits"),
                safety_level="explicit_one_shot_external",
                requires_key=True,
                env_var="GIGACHAT_AUTH_KEY",
                implemented=True,
                network_capable=True,
            ),
            AIProviderRole(
                provider="openai",
                default_model=model("openai", "openai-default"),
                role="strong reasoning/code external provider if account quota exists",
                strengths=("reasoning", "code", "general quality depending on model"),
                weaknesses=("external network", "billing/quota", "may not be available"),
                safety_level="explicit_one_shot_external",
                requires_key=True,
                env_var="OPENAI_API_KEY",
                implemented=True,
                network_capable=True,
            ),
            AIProviderRole(
                provider="gemini",
                default_model=model("gemini", "gemini-2.5-flash-lite"),
                role="alternative external provider",
                strengths=("general reasoning", "summarization", "alternative viewpoint"),
                weaknesses=("external network", "regional/account limits may apply"),
                safety_level="explicit_one_shot_external",
                requires_key=True,
                env_var="GEMINI_API_KEY",
                implemented=True,
                network_capable=True,
            ),
            AIProviderRole(
                provider="ollama",
                default_model=model("ollama", "qwen2.5:1.5b"),
                role="local/offline provider",
                strengths=("privacy/offline", "local control", "no API key", "no external network"),
                weaknesses=(
                    "requires local Ollama server",
                    "requires manually installed model",
                    "depends on laptop performance/model size",
                ),
                safety_level="local_only_explicit_one_shot",
                requires_key=False,
                env_var=None,
                implemented=True,
                network_capable=False,
            ),
        )

    def status_text_ru(self) -> str:
        return "\n".join(
            [
                "AI provider selection policy status:",
                "- enabled: yes",
                "- mode: recommendation only",
                "- network: not called",
                "- dry_run remains default",
                "- manual session selection wins",
                "- consensus remains explicit-only",
                "- external providers require explicit one-shot",
                "- Ollama implemented as local-only explicit one-shot provider",
                "- keys are checked only as PRESENT/MISSING",
                "- secrets are never printed",
                "- memory/profile/files/logs are not sent",
                "- prompts/responses are not stored to disk",
            ]
        )

    def matrix_text_ru(self) -> str:
        lines = [
            "AI provider fallback matrix:",
            "- mode: recommendation only",
            "- network: not called",
            "- dry_run remains default",
            "- provider order: dry_run, ollama, groq, gigachat, openai, gemini",
            "- fallback patterns:",
            "  general/fast: groq -> gigachat -> openai -> gemini -> dry_run",
            "  russian/russia: gigachat -> groq -> openai -> gemini -> dry_run",
            "  code/reasoning: openai -> groq -> gemini -> gigachat -> dry_run",
            "  private/offline: ollama -> dry_run",
            "  consensus: explicit command only",
            "",
            "Provider roles:",
        ]
        for role in self.roles():
            env_var = role.env_var or "not required"
            key = self._key_presence(role)
            implemented = "yes" if role.implemented else "planned"
            network = "local-only" if role.provider == "ollama" else ("yes" if role.network_capable else "no")
            strengths = ", ".join(role.strengths)
            weaknesses = ", ".join(role.weaknesses)
            lines.extend(
                [
                    f"- {role.provider}: role={role.role}; model={role.default_model or 'none'}",
                    f"  implemented={implemented}; network_capable={network}; env={env_var}; key={key}",
                    f"  strengths={strengths}",
                    f"  weaknesses={weaknesses}",
                ]
            )
        lines.extend(
            [
                "- key env var names are shown, values are never printed",
                "- actual fallback execution is not implemented in this task",
            ]
        )
        return "\n".join(lines)

    def recommend(
        self,
        prompt: str,
        session_snapshot=None,
        consensus_requested: bool = False,
    ) -> AIProviderSelectionRecommendation:
        text = self._safe_prompt(prompt)
        task_type = self.classify_task(text)
        key_presence = self.key_presence()
        role_by_provider = {role.provider: role for role in self.roles()}

        if self._manual_session_selected(session_snapshot):
            provider = session_snapshot.selected_provider
            model = session_snapshot.selected_model
            return AIProviderSelectionRecommendation(
                ok=True,
                recommended_provider=provider,
                recommended_model=model,
                reason=(
                    "manual runtime selection wins; continue with selected "
                    f"provider/model {provider}/{model}"
                ),
                fallback_chain=[provider],
                skipped=[],
                warnings=self._base_warnings(),
            )

        if consensus_requested or task_type == "consensus":
            return AIProviderSelectionRecommendation(
                ok=True,
                recommended_provider="consensus",
                recommended_model=None,
                reason="prompt asks to compare multiple AI responses; consensus remains explicit-only",
                fallback_chain=["groq", "gigachat", "openai", "gemini"],
                skipped=self._skipped_for_chain(("groq", "gigachat", "openai", "gemini"), key_presence),
                warnings=self._base_warnings()
                + ["run explicit command only: консенсус ai: <text> or спроси все ai: <text>"],
            )

        if task_type == "private":
            return AIProviderSelectionRecommendation(
                ok=True,
                recommended_provider="ollama",
                recommended_model=role_by_provider["ollama"].default_model,
                reason=(
                    "privacy/offline requirement detected; prefer Ollama for real "
                    "local intelligence with no external network, then dry_run if unavailable"
                ),
                fallback_chain=["ollama", "dry_run"],
                skipped=["external providers skipped for privacy/offline safety"],
                warnings=self._base_warnings()
                + [
                    "Ollama recommendation does not call runtime",
                    "check local runtime with: список ollama моделей",
                    "run explicit local request with: ollama реальный запрос: <text>",
                ],
            )

        chain = self.build_fallback_chain(task_type, key_presence)
        recommended_provider = chain[0] if chain else "dry_run"
        role = role_by_provider.get(recommended_provider, role_by_provider["dry_run"])
        reason = self._reason_for(task_type, recommended_provider, key_presence)
        return AIProviderSelectionRecommendation(
            ok=True,
            recommended_provider=recommended_provider,
            recommended_model=role.default_model,
            reason=reason,
            fallback_chain=chain,
            skipped=self._skipped_for_chain(self._ordered_chain_for_task(task_type), key_presence),
            warnings=self._base_warnings(),
        )

    def recommendation_text_ru(
        self,
        prompt: str,
        session_snapshot=None,
        consensus_requested: bool = False,
    ) -> str:
        recommendation = self.recommend(
            prompt,
            session_snapshot=session_snapshot,
            consensus_requested=consensus_requested,
        )
        key_lines = [
            f"- {provider}: {status}"
            for provider, status in self.key_presence().items()
        ]
        next_commands = self._next_commands(recommendation, prompt)
        return "\n".join(
            [
                "AI provider selection recommendation:",
                f"- ok: {recommendation.ok}",
                f"- recommended provider: {recommendation.recommended_provider}",
                f"- recommended model: {recommendation.recommended_model or 'none'}",
                f"- reason: {recommendation.reason}",
                f"- fallback chain: {' -> '.join(recommendation.fallback_chain)}",
                f"- network_called: {recommendation.network_called}",
                f"- dry_run_default_unchanged: {recommendation.dry_run_default_unchanged}",
                "- key presence:",
                *key_lines,
                "- skipped:",
                *(f"  - {item}" for item in (recommendation.skipped or ["none"])),
                "- warnings:",
                *(f"  - {item}" for item in recommendation.warnings),
                "- safe next command examples:",
                *next_commands,
                "- prompt was analyzed in memory only and was not stored",
                "- provider response execution: not applicable; no provider was called",
            ]
        )

    def classify_task(self, prompt: str) -> str:
        text = self._safe_prompt(prompt).lower()
        if any(
            marker in text
            for marker in (
                "consensus",
                "compare answers",
                "compare multiple",
                "сравни ответы",
                "сравнить ответы",
                "спроси все ai",
                "нескольких ии",
                "несколько ии",
                "нескольких ai",
            )
        ):
            return "consensus"
        if any(
            marker in text
            for marker in (
                "private",
                "personal data",
                "local-only",
                "offline",
                "no internet",
                "secret",
                "secrets",
                "приват",
                "персональн",
                "локально",
                "офлайн",
                "без интернета",
                "не отправляй",
                "секрет",
                "ключ",
                "файл",
            )
        ):
            return "private"
        if any(
            marker in text
            for marker in (
                "code",
                "python",
                "debug",
                "reason",
                "architecture",
                "refactor",
                "код",
                "программ",
                "ошибк",
                "архитект",
                "рефактор",
                "рассуж",
            )
        ):
            return "code"
        if any(
            marker in text
            for marker in (
                "russian",
                "russia",
                "росси",
                "русск",
                "сбер",
                "гигачат",
                "gigachat",
            )
        ):
            return "russian"
        if any(marker in text for marker in ("fast", "quick", "быстро", "скорее", "простой")):
            return "fast"
        return "general"

    def build_fallback_chain(
        self, task_type: str | None, key_presence: dict[str, str] | None = None
    ) -> list[str]:
        key_presence = key_presence or self.key_presence()
        ordered = self._ordered_chain_for_task(task_type)
        available = [
            provider
            for provider in ordered
            if provider == "dry_run" or key_presence.get(provider) == "PRESENT"
        ]
        if "dry_run" not in available:
            available.append("dry_run")
        return available

    def key_presence(self) -> dict[str, str]:
        return {role.provider: self._key_presence(role) for role in self.roles()}

    def _ordered_chain_for_task(self, task_type: str | None) -> tuple[str, ...]:
        if task_type == "russian":
            return ("gigachat", "groq", "openai", "gemini", "dry_run")
        if task_type == "code":
            return ("openai", "groq", "gemini", "gigachat", "dry_run")
        if task_type in {"fast", "general"}:
            return ("groq", "gigachat", "openai", "gemini", "dry_run")
        return ("groq", "gigachat", "openai", "gemini", "dry_run")

    def _key_presence(self, role: AIProviderRole) -> str:
        if not role.requires_key:
            return "NOT_REQUIRED"
        status = self.config_manager.status_for(role.provider)
        if status is not None:
            if status.key_status == AIProviderKeyStatus.PRESENT:
                return "PRESENT"
            if status.key_status == AIProviderKeyStatus.INVALID_REFERENCE:
                return "INVALID_REFERENCE"
            return "MISSING"
        value = self.environ.get(role.env_var or "")
        return "PRESENT" if value is not None and str(value).strip() else "MISSING"

    @staticmethod
    def _manual_session_selected(session_snapshot) -> bool:
        return bool(
            session_snapshot is not None
            and getattr(session_snapshot, "selection_mode", None) == "manual"
            and getattr(session_snapshot, "selected_provider", None)
            and getattr(session_snapshot, "selected_model", None)
        )

    @staticmethod
    def _safe_prompt(prompt: str) -> str:
        return str(prompt or "").replace("\r", " ").replace("\n", " ").strip()

    @staticmethod
    def _base_warnings() -> list[str]:
        return [
            "recommendation only; no provider was called",
            "external providers still require explicit one-shot command",
            "dry_run remains default",
            "secrets are never printed",
            "AI responses must never execute as commands",
        ]

    def _skipped_for_chain(
        self, ordered: tuple[str, ...], key_presence: dict[str, str]
    ) -> list[str]:
        skipped = []
        for provider in ordered:
            if provider == "dry_run":
                continue
            status = key_presence.get(provider, "MISSING")
            if status != "PRESENT":
                skipped.append(f"{provider}: key {status}")
        return skipped

    @staticmethod
    def _reason_for(
        task_type: str | None, provider: str, key_presence: dict[str, str]
    ) -> str:
        if provider == "dry_run":
            return f"no suitable external key is PRESENT for {task_type or 'general'} task; safe dry_run fallback"
        if task_type == "russian":
            return f"{provider} selected for Russian/Russia-oriented task; key is {key_presence.get(provider)}"
        if task_type == "code":
            return f"{provider} selected for code/strong reasoning task; key is {key_presence.get(provider)}"
        if task_type == "fast":
            return f"{provider} selected for fast/simple external answer; key is {key_presence.get(provider)}"
        return f"{provider} selected for general external answer; key is {key_presence.get(provider)}"

    @staticmethod
    def _next_commands(
        recommendation: AIProviderSelectionRecommendation, prompt: str
    ) -> list[str]:
        provider = recommendation.recommended_provider
        safe_prompt = str(prompt or "").strip()
        if provider == "consensus":
            return [
                "  - консенсус ai: <text>",
                "  - спроси все ai: <text>",
            ]
        if provider == "dry_run":
            return ["  - спроси ai: <text>"]
        if provider == "ollama":
            return [
                "  - список ollama моделей",
                "  - ollama реальный запрос: <text>",
                f"  - example only, not executed: ollama реальный запрос: {safe_prompt[:80]}",
            ]
        return [
            f"  - выбрать ai provider {provider}",
            f"  - выбрать ai модель {provider} {recommendation.recommended_model or '<model>'}",
            f"  - {provider} реальный запрос: <text>",
            f"  - example only, not executed: {provider} реальный запрос: {safe_prompt[:80]}",
        ]
