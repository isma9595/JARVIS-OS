"""Deterministic AI context privacy boundary.

This module is intentionally self-contained: it does not call network, does not
read or write disk, and never persists prompts or responses.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re


class AIContextSensitivity(str, Enum):
    PUBLIC_OR_GENERAL = "public_or_general"
    USER_TYPED_GENERAL = "user_typed_general"
    PRIVATE_OR_PERSONAL = "private_or_personal"
    SECRET_LIKE = "secret_like"
    FILE_CONTENT = "file_content"
    FILE_PATH_REFERENCE = "file_path_reference"
    MEMORY_PROFILE = "memory_profile"
    LOG_OR_DEBUG = "log_or_debug"
    SCREEN_OR_OCR = "screen_or_ocr"
    AUDIO_TRANSCRIPT = "audio_transcript"
    UNKNOWN_SENSITIVE = "unknown_sensitive"


class AIContextTarget(str, Enum):
    DRY_RUN = "dry_run"
    LOCAL_OLLAMA = "local_ollama"
    EXTERNAL_PROVIDER = "external_provider"
    CONSENSUS_EXTERNAL = "consensus_external"


@dataclass(frozen=True)
class AIContextDecision:
    allowed: bool
    target: str
    sensitivity: str
    reason: str
    safe_alternative: str | None
    warnings: list[str]
    redacted_preview: str
    network_called: bool = False
    should_block_external: bool = False
    should_require_explicit_context_confirmation: bool = False


class AIContextPrivacyPolicy:
    """Classify user text and decide whether it is safe for an AI target."""

    _SECRET_PATTERNS = (
        re.compile(r"\bsk-[A-Za-z0-9_\-]{8,}\b"),
        re.compile(r"\bxoxb-[A-Za-z0-9_\-]{8,}\b"),
        re.compile(r"\bghp_[A-Za-z0-9_]{8,}\b"),
        re.compile(r"\bgsk_[A-Za-z0-9_\-]{8,}\b"),
        re.compile(r"\bya29\.[A-Za-z0-9_\-\.]{8,}\b"),
        re.compile(r"\b[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{12,}\b"),
        re.compile(r"\b(?!([A-Za-z0-9+/])\1{39,}\b)[A-Za-z0-9+/]{40,}={0,2}\b"),
        re.compile(
            r"(?i)\b(api[_ -]?key|apikey|token|bearer|authorization|password|пароль|ключ api|секрет)\b"
        ),
    )
    _PRIVATE_RE = re.compile(
        r"(?i)(private file|personal data|confidential|do not send to internet|"
        r"не отправляй в интернет|приватный файл|личные данные|конфиденциально|"
        r"паспорт|снилс|инн|банковская карта|договор|медкарта|диагноз|зарплата|персональные данные)"
    )
    _FILE_CONTENT_RE = re.compile(
        r"(?i)(содержимое файла|текст документа|загруженный файл|отправь файл)"
    )
    _FILE_PATH_RE = re.compile(
        r"(?i)([A-Z]:\\[^\s]+|/home/[^\s]+|/mnt/[^\s]+|\.(docx|pdf|xlsx|rtf|txt)\b)"
    )
    _MEMORY_RE = re.compile(
        r"(?i)(моя память|профиль пользователя|вспомни всё обо мне|вспомни все обо мне|"
        r"мои сохраненные данные|мои сохранённые данные|memory/profile)"
    )
    _LOG_RE = re.compile(r"(?i)(logs|traceback|\.env\b|debug log|журнал|лог)")
    _SCREEN_RE = re.compile(r"(?i)(скриншот|экран|ocr|то что на мониторе|screen capture)")
    _AUDIO_RE = re.compile(r"(?i)(запись микрофона|аудио|голосовая запись)")

    def classify_text(self, text: str) -> AIContextSensitivity:
        safe = self._normalize_text(text)
        if not safe:
            return AIContextSensitivity.USER_TYPED_GENERAL
        if self._has_secret(safe):
            return AIContextSensitivity.SECRET_LIKE
        if self._MEMORY_RE.search(safe):
            return AIContextSensitivity.MEMORY_PROFILE
        if self._SCREEN_RE.search(safe):
            return AIContextSensitivity.SCREEN_OR_OCR
        if self._AUDIO_RE.search(safe):
            return AIContextSensitivity.AUDIO_TRANSCRIPT
        if self._FILE_CONTENT_RE.search(safe):
            return AIContextSensitivity.FILE_CONTENT
        if self._FILE_PATH_RE.search(safe):
            return AIContextSensitivity.FILE_PATH_REFERENCE
        if self._PRIVATE_RE.search(safe):
            return AIContextSensitivity.PRIVATE_OR_PERSONAL
        if self._LOG_RE.search(safe):
            return AIContextSensitivity.LOG_OR_DEBUG
        return AIContextSensitivity.USER_TYPED_GENERAL

    def redacted_preview(self, text: str, limit: int = 180) -> str:
        safe = self._normalize_text(text)
        for pattern in self._SECRET_PATTERNS:
            safe = pattern.sub("[REDACTED]", safe)
        if len(safe) <= limit:
            return safe
        return safe[: max(0, limit - 15)].rstrip() + "... [truncated]"

    def decide(self, text: str, target: AIContextTarget | str) -> AIContextDecision:
        target_enum = self._target(target)
        sensitivity = self.classify_text(text)
        preview = self.redacted_preview(text)
        warnings = [
            "network: not called by privacy preflight",
            "secrets are redacted in policy output",
            "prompts/responses are not stored to disk",
        ]

        if target_enum == AIContextTarget.DRY_RUN:
            return AIContextDecision(
                allowed=True,
                target=target_enum.value,
                sensitivity=sensitivity.value,
                reason="dry_run is offline and deterministic; no provider network is used.",
                safe_alternative=None,
                warnings=warnings,
                redacted_preview=preview,
                should_block_external=False,
                should_require_explicit_context_confirmation=self._needs_context_package(sensitivity),
            )

        if target_enum == AIContextTarget.LOCAL_OLLAMA:
            if sensitivity in {
                AIContextSensitivity.PUBLIC_OR_GENERAL,
                AIContextSensitivity.USER_TYPED_GENERAL,
                AIContextSensitivity.PRIVATE_OR_PERSONAL,
                AIContextSensitivity.FILE_PATH_REFERENCE,
            }:
                return AIContextDecision(
                    allowed=True,
                    target=target_enum.value,
                    sensitivity=sensitivity.value,
                    reason="Ollama is local-only and may handle user-typed private text or path references.",
                    safe_alternative=None,
                    warnings=warnings
                    + [
                        "localhost-only request still requires explicit one-shot",
                        "raw files/memory/logs/screen/audio are not packaged automatically",
                    ],
                    redacted_preview=preview,
                    should_block_external=True,
                    should_require_explicit_context_confirmation=False,
                )
            return AIContextDecision(
                allowed=False,
                target=target_enum.value,
                sensitivity=sensitivity.value,
                reason=self._blocked_reason(sensitivity, local=True),
                safe_alternative=self._safe_alternative(sensitivity, local=True),
                warnings=warnings,
                redacted_preview=preview,
                should_block_external=True,
                should_require_explicit_context_confirmation=self._needs_context_package(sensitivity),
            )

        if target_enum in {AIContextTarget.EXTERNAL_PROVIDER, AIContextTarget.CONSENSUS_EXTERNAL}:
            if sensitivity in {
                AIContextSensitivity.PUBLIC_OR_GENERAL,
                AIContextSensitivity.USER_TYPED_GENERAL,
            }:
                extra = []
                if target_enum == AIContextTarget.CONSENSUS_EXTERNAL:
                    extra.append("external consensus may use multiple provider quotas")
                return AIContextDecision(
                    allowed=True,
                    target=target_enum.value,
                    sensitivity=sensitivity.value,
                    reason="No private, secret, file, memory, log, screen, or audio markers were detected.",
                    safe_alternative=None,
                    warnings=warnings + extra,
                    redacted_preview=preview,
                    should_block_external=False,
                    should_require_explicit_context_confirmation=False,
                )
            return AIContextDecision(
                allowed=False,
                target=target_enum.value,
                sensitivity=sensitivity.value,
                reason=self._blocked_reason(sensitivity, local=False),
                safe_alternative=self._safe_alternative(sensitivity, local=False),
                warnings=warnings
                + (
                    ["external consensus is stricter and may use multiple provider quotas"]
                    if target_enum == AIContextTarget.CONSENSUS_EXTERNAL
                    else []
                ),
                redacted_preview=preview,
                should_block_external=True,
                should_require_explicit_context_confirmation=self._needs_context_package(sensitivity),
            )

        raise ValueError(f"Unsupported AI context target: {target}")

    def status_text_ru(self) -> str:
        return "\n".join(
            [
                "AI context privacy boundary status:",
                "- enabled: yes",
                "- mode: deterministic preflight",
                "- network: not called",
                "- dry_run: safest default",
                "- Ollama: local-only option",
                "- external providers: blocked for sensitive/private/secret/file/memory/log/screen/audio context",
                "- consensus: explicit-only and stricter",
                "- secrets redacted",
                "- no memory/profile/files/logs/screen/audio sent automatically",
                "- no prompts/responses stored to disk",
                "- no response execution",
            ]
        )

    def matrix_text_ru(self) -> str:
        return "\n".join(
            [
                "AI context privacy matrix:",
                "- mode: deterministic preflight",
                "- network: not called",
                "",
                "Context type | dry_run | Ollama/local | external providers | external consensus",
                "PUBLIC_OR_GENERAL | allowed | allowed | allowed | allowed with quota warning",
                "USER_TYPED_GENERAL | allowed | allowed | allowed | allowed with quota warning",
                "PRIVATE_OR_PERSONAL | allowed | allowed local-only | blocked | blocked",
                "SECRET_LIKE | allowed redacted output only | blocked | blocked | blocked",
                "FILE_PATH_REFERENCE | allowed | allowed path text only | blocked | blocked",
                "FILE_CONTENT | allowed | blocked until explicit context package | blocked | blocked",
                "MEMORY_PROFILE | allowed | blocked until explicit context package | blocked | blocked",
                "LOG_OR_DEBUG | allowed | blocked until explicit context package | blocked | blocked",
                "SCREEN_OR_OCR | allowed | blocked until explicit context package | blocked | blocked",
                "AUDIO_TRANSCRIPT | allowed | blocked until explicit context package | blocked | blocked",
                "UNKNOWN_SENSITIVE | allowed | blocked | blocked | blocked",
                "",
                "- no automatic memory/profile/files/logs/screen/audio sending",
                "- secrets are redacted in previews and refusals",
                "- manual provider selection does not override this boundary",
            ]
        )

    def check_text_ru(self, text: str, target: AIContextTarget | str | None = None) -> str:
        targets = [self._target(target)] if target is not None else list(AIContextTarget)
        lines = [
            "AI context privacy check:",
            f"- redacted preview: {self.redacted_preview(text)}",
            f"- sensitivity: {self.classify_text(text).value}",
            "- network: not called",
            "- text was checked in memory only and was not stored",
            "",
            "Decisions:",
        ]
        for item in targets:
            decision = self.decide(text, item)
            lines.extend(
                [
                    f"- target: {decision.target}",
                    f"  allowed: {decision.allowed}",
                    f"  reason: {decision.reason}",
                    f"  safe alternative: {decision.safe_alternative or 'none'}",
                    f"  require explicit context confirmation: {decision.should_require_explicit_context_confirmation}",
                ]
            )
        return "\n".join(lines)

    def format_refusal(self, text: str, target: AIContextTarget | str) -> str:
        decision = self.decide(text, target)
        lines = [
            "AI context privacy boundary blocked this request.",
            f"- target: {decision.target}",
            f"- sensitivity: {decision.sensitivity}",
            f"- reason: {decision.reason}",
            f"- redacted preview: {decision.redacted_preview}",
            f"- safe alternative: {decision.safe_alternative or 'none'}",
            "- provider was not called",
            "- network_called: False",
            "- secrets were redacted",
            "- no prompt/response was stored to disk",
        ]
        return "\n".join(lines)

    def _has_secret(self, text: str) -> bool:
        return any(pattern.search(text) for pattern in self._SECRET_PATTERNS)

    @staticmethod
    def _needs_context_package(sensitivity: AIContextSensitivity) -> bool:
        return sensitivity in {
            AIContextSensitivity.FILE_CONTENT,
            AIContextSensitivity.MEMORY_PROFILE,
            AIContextSensitivity.LOG_OR_DEBUG,
            AIContextSensitivity.SCREEN_OR_OCR,
            AIContextSensitivity.AUDIO_TRANSCRIPT,
            AIContextSensitivity.UNKNOWN_SENSITIVE,
        }

    @staticmethod
    def _blocked_reason(sensitivity: AIContextSensitivity, local: bool) -> str:
        if sensitivity == AIContextSensitivity.SECRET_LIKE:
            return "Secret-like context must be redacted or handled manually; no provider receives it in this task."
        if local:
            return "Raw context packages are not implemented for local sending in this task."
        return "External providers may receive only general user-typed prompts without sensitive markers."

    @staticmethod
    def _safe_alternative(sensitivity: AIContextSensitivity, local: bool) -> str:
        if sensitivity == AIContextSensitivity.SECRET_LIKE:
            return "Redact the secret manually, then use dry_run or a non-secret summary."
        if local:
            return "Use dry_run, or provide a short user-typed summary after removing raw context."
        return "Use Ollama/local for private typed text, or dry_run; redact secrets first."

    @staticmethod
    def _normalize_text(text: str) -> str:
        return " ".join(str(text or "").replace("\r", " ").replace("\n", " ").split())

    @staticmethod
    def _target(target: AIContextTarget | str | None) -> AIContextTarget:
        if isinstance(target, AIContextTarget):
            return target
        value = str(target or "").strip().lower()
        aliases = {
            "dry_run": AIContextTarget.DRY_RUN,
            "dryrun": AIContextTarget.DRY_RUN,
            "ollama": AIContextTarget.LOCAL_OLLAMA,
            "local_ollama": AIContextTarget.LOCAL_OLLAMA,
            "local": AIContextTarget.LOCAL_OLLAMA,
            "external": AIContextTarget.EXTERNAL_PROVIDER,
            "external_provider": AIContextTarget.EXTERNAL_PROVIDER,
            "consensus": AIContextTarget.CONSENSUS_EXTERNAL,
            "consensus_external": AIContextTarget.CONSENSUS_EXTERNAL,
        }
        if value in aliases:
            return aliases[value]
        raise ValueError(f"Unknown AI context target: {target}")
