"""Deterministic intent resolution for AppService input.

The resolver is a pure metadata boundary. It does not execute commands, call
providers, call ActionRouter, read credentials, touch audio, or persist state.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re

from app.app_contracts import AppClarificationOption, AppIntentResolutionContract
from core.command_registry import CommandMetadata, CommandRegistry


class IntentKind(Enum):
    LOCAL_COMMAND = "local_command"
    ORDINARY_CONVERSATION = "ordinary_conversation"
    PROVIDER_REQUEST = "provider_request"
    CONFIRMATION_RESPONSE = "confirmation_response"
    CANCELLATION_RESPONSE = "cancellation_response"
    AMBIGUOUS = "ambiguous"
    UNSUPPORTED = "unsupported"


class ResolutionStatus(Enum):
    RESOLVED = "resolved"
    REQUIRES_CLARIFICATION = "requires_clarification"
    UNSUPPORTED = "unsupported"


class IntentConfidence(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class IntentResolution:
    original_text: str
    processing_text: str
    intent_kind: IntentKind
    resolution_status: ResolutionStatus
    matched_command: str | None
    confidence: IntentConfidence
    reason_codes: tuple[str, ...]
    clarification_question: str | None
    clarification_options: tuple[AppClarificationOption, ...]
    requires_clarification: bool
    source: str
    command_text: str | None = None

    def to_contract(self) -> AppIntentResolutionContract:
        return AppIntentResolutionContract(
            original_text=self.original_text,
            processing_text=self.processing_text,
            intent_kind=self.intent_kind.value,
            resolution_status=self.resolution_status.value,
            matched_command=self.matched_command,
            confidence=self.confidence.value,
            reason_codes=self.reason_codes,
            clarification_question=self.clarification_question,
            clarification_options=self.clarification_options,
            requires_clarification=self.requires_clarification,
            source=self.source,
        )

    def to_dict(self) -> dict[str, object]:
        return self.to_contract().to_dict()


@dataclass(frozen=True)
class ClarificationState:
    question_ru: str
    options: tuple[AppClarificationOption, ...]
    original_text: str
    source: str

    def to_dict(self) -> dict[str, object]:
        return {
            "question_ru": self.question_ru,
            "options": tuple(option.to_dict() for option in self.options),
            "original_text": self.original_text,
            "source": self.source,
        }


class HybridIntentResolver:
    """Resolve user text using only deterministic registry and pattern checks."""

    CONFIRMATION_RESPONSES = {
        "да",
        "подтверждаю",
        "подтвердить",
        "выполнить",
        "выполни",
        "ок",
        "ага",
        "yes",
        "confirm",
        "proceed",
    }
    CANCELLATION_RESPONSES = {
        "нет",
        "отмена",
        "отмени",
        "не надо",
        "stop",
        "cancel",
        "never mind",
        "no",
    }
    AMBIGUOUS_STATUS_PHRASES = {
        "покажи статус",
        "какой статус",
        "проверить статус",
        "статус какой",
    }
    RISKY_QUESTION_PREFIXES = (
        "можно ли ",
        "как ",
        "что будет если ",
        "зачем ",
        "почему ",
    )
    VAGUE_RISKY_PHRASES = {
        "удали это",
        "удалить это",
        "сотри это",
        "убери это",
    }
    RISKY_MISSPELLINGS = {
        "удали фал",
        "удалить фал",
    }
    EXACT_RISKY_PREFIXES = (
        "удали файл ",
    )
    EXACT_FORBIDDEN_EXISTING_PATH = {
        "удали system32",
        "удали все файлы",
    }
    SMALL_TALK = {
        "привет",
        "здравствуй",
        "здравствуйте",
        "салам",
        "добрый день",
    }
    STANDALONE_CLARIFICATION_LABELS = {
        "системы",
        "система",
        "микрофона",
        "appservice",
    }

    def __init__(self, command_registry: CommandRegistry):
        self.command_registry = command_registry

    def resolve(
        self,
        original_text: str,
        source: str,
        processing_text: str | None = None,
    ) -> IntentResolution:
        original = str(original_text or "").strip()
        processing = str(processing_text if processing_text is not None else original_text or "").strip()
        normalized = self.command_registry.normalize_alias(processing)
        reason_codes: list[str] = []
        if processing != original:
            reason_codes.append("safe_source_normalization")
        control_normalized = self._normalize_control_response(normalized)

        exact = self._match_registry_command(processing)
        if exact is not None:
            return self._resolved_command(
                original,
                processing,
                source,
                exact,
                processing,
                (*reason_codes, "registry_exact_or_alias"),
            )

        semantic = self._semantic_read_only_match(normalized)
        if semantic is not None:
            metadata, command_text, reason = semantic
            return self._resolved_command(
                original,
                processing,
                source,
                metadata,
                command_text,
                (*reason_codes, reason),
            )

        provider = self._explicit_provider_request(processing)
        if provider is not None:
            return IntentResolution(
                original_text=original,
                processing_text=processing,
                intent_kind=IntentKind.PROVIDER_REQUEST,
                resolution_status=ResolutionStatus.RESOLVED,
                matched_command=provider.command_id,
                confidence=IntentConfidence.HIGH,
                reason_codes=(*reason_codes, "explicit_provider_request"),
                clarification_question=None,
                clarification_options=(),
                requires_clarification=False,
                source=source,
                command_text=processing,
            )

        if control_normalized in self.CANCELLATION_RESPONSES:
            return self._resolved_non_command(
                original,
                processing,
                source,
                IntentKind.CANCELLATION_RESPONSE,
                (*reason_codes, "cancellation_response"),
            )
        if control_normalized in self.CONFIRMATION_RESPONSES:
            return self._resolved_non_command(
                original,
                processing,
                source,
                IntentKind.CONFIRMATION_RESPONSE,
                (*reason_codes, "confirmation_response"),
            )

        if normalized in self.AMBIGUOUS_STATUS_PHRASES:
            return self._status_clarification(original, processing, source, tuple(reason_codes))

        if normalized in self.VAGUE_RISKY_PHRASES:
            return self._unsupported(
                original,
                processing,
                source,
                (*reason_codes, "vague_risky_action_not_executed"),
            )
        if normalized in self.RISKY_MISSPELLINGS:
            return self._unsupported(
                original,
                processing,
                source,
                (*reason_codes, "risky_misspelling_not_repaired"),
            )
        if self._is_risky_question(normalized):
            return self._ordinary(
                original,
                processing,
                source,
                (*reason_codes, "risky_action_question"),
            )
        if normalized in self.EXACT_FORBIDDEN_EXISTING_PATH or self._is_exact_risky_existing_path(normalized):
            return IntentResolution(
                original_text=original,
                processing_text=processing,
                intent_kind=IntentKind.LOCAL_COMMAND,
                resolution_status=ResolutionStatus.RESOLVED,
                matched_command=None,
                confidence=IntentConfidence.HIGH,
                reason_codes=(*reason_codes, "exact_risky_existing_path"),
                clarification_question=None,
                clarification_options=(),
                requires_clarification=False,
                source=source,
                command_text=processing,
            )

        if normalized in self.SMALL_TALK:
            return self._ordinary(original, processing, source, (*reason_codes, "small_talk"))
        if normalized in self.STANDALONE_CLARIFICATION_LABELS:
            return self._unsupported(
                original,
                processing,
                source,
                (*reason_codes, "standalone_clarification_label"),
            )
        if self._looks_like_question(normalized):
            return self._ordinary(original, processing, source, (*reason_codes, "ordinary_question"))

        return IntentResolution(
            original_text=original,
            processing_text=processing,
            intent_kind=IntentKind.LOCAL_COMMAND,
            resolution_status=ResolutionStatus.RESOLVED,
            matched_command=None,
            confidence=IntentConfidence.LOW,
            reason_codes=(*reason_codes, "legacy_commandprocessor_fallback"),
            clarification_question=None,
            clarification_options=(),
            requires_clarification=False,
            source=source,
            command_text=processing,
        )

    def _resolved_command(
        self,
        original: str,
        processing: str,
        source: str,
        metadata: CommandMetadata,
        command_text: str,
        reason_codes: tuple[str, ...],
    ) -> IntentResolution:
        kind = (
            IntentKind.PROVIDER_REQUEST
            if metadata.requires_network or metadata.requires_ai_key
            else IntentKind.LOCAL_COMMAND
        )
        return IntentResolution(
            original_text=original,
            processing_text=processing,
            intent_kind=kind,
            resolution_status=ResolutionStatus.RESOLVED,
            matched_command=metadata.command_id,
            confidence=IntentConfidence.HIGH,
            reason_codes=reason_codes,
            clarification_question=None,
            clarification_options=(),
            requires_clarification=False,
            source=source,
            command_text=command_text,
        )

    def _resolved_non_command(
        self,
        original: str,
        processing: str,
        source: str,
        kind: IntentKind,
        reason_codes: tuple[str, ...],
    ) -> IntentResolution:
        return IntentResolution(
            original_text=original,
            processing_text=processing,
            intent_kind=kind,
            resolution_status=ResolutionStatus.RESOLVED,
            matched_command=None,
            confidence=IntentConfidence.HIGH,
            reason_codes=reason_codes,
            clarification_question=None,
            clarification_options=(),
            requires_clarification=False,
            source=source,
            command_text=processing,
        )

    def _status_clarification(
        self,
        original: str,
        processing: str,
        source: str,
        reason_codes: tuple[str, ...],
    ) -> IntentResolution:
        candidates = (
            ("system", "системы", "статус системы"),
            ("ai", "AI", "статус ai"),
            ("microphone", "микрофона", "статус микрофона"),
            ("app_service", "AppService", "статус app service"),
        )
        options = []
        for option_id, label, command_text in candidates:
            metadata = self._match_registry_command(command_text)
            options.append(
                AppClarificationOption(
                    option_id=option_id,
                    label_ru=label,
                    command_text=command_text,
                    command_id=metadata.command_id if metadata is not None else None,
                )
            )
        return IntentResolution(
            original_text=original,
            processing_text=processing,
            intent_kind=IntentKind.AMBIGUOUS,
            resolution_status=ResolutionStatus.REQUIRES_CLARIFICATION,
            matched_command=None,
            confidence=IntentConfidence.MEDIUM,
            reason_codes=(*reason_codes, "ambiguous_status_request"),
            clarification_question="Какой статус проверить: системы, AI, микрофона или AppService?",
            clarification_options=tuple(options),
            requires_clarification=True,
            source=source,
            command_text=None,
        )

    def _unsupported(
        self,
        original: str,
        processing: str,
        source: str,
        reason_codes: tuple[str, ...],
    ) -> IntentResolution:
        return IntentResolution(
            original_text=original,
            processing_text=processing,
            intent_kind=IntentKind.UNSUPPORTED,
            resolution_status=ResolutionStatus.UNSUPPORTED,
            matched_command=None,
            confidence=IntentConfidence.LOW,
            reason_codes=reason_codes,
            clarification_question=None,
            clarification_options=(),
            requires_clarification=False,
            source=source,
            command_text=None,
        )

    def _ordinary(
        self,
        original: str,
        processing: str,
        source: str,
        reason_codes: tuple[str, ...],
    ) -> IntentResolution:
        return IntentResolution(
            original_text=original,
            processing_text=processing,
            intent_kind=IntentKind.ORDINARY_CONVERSATION,
            resolution_status=ResolutionStatus.RESOLVED,
            matched_command=None,
            confidence=IntentConfidence.LOW,
            reason_codes=reason_codes,
            clarification_question=None,
            clarification_options=(),
            requires_clarification=False,
            source=source,
            command_text=processing,
        )

    def _match_registry_command(self, text: str) -> CommandMetadata | None:
        exact = self.command_registry.find_by_alias(text)
        if exact is not None:
            return exact
        normalized_text = self.command_registry.normalize_alias(text)
        for command in self.command_registry.commands:
            for alias in command.aliases:
                normalized_alias = self.command_registry.normalize_alias(alias)
                if "<text>" not in normalized_alias:
                    continue
                prefix = normalized_alias.split("<text>", 1)[0].strip()
                if prefix and normalized_text.startswith(prefix):
                    return command
        return None

    @classmethod
    def _normalize_control_response(cls, normalized: str) -> str:
        return " ".join(re.sub(r"^[^\w]+|[^\w]+$", " ", normalized).split())

    def _semantic_read_only_match(
        self,
        normalized: str,
    ) -> tuple[CommandMetadata, str, str] | None:
        semantic_commands = {
            "покажи состояние системы": ("статус системы", "semantic_system_status"),
            "состояние системы": ("статус системы", "semantic_system_status"),
            "какие сервисы работают": ("статус app service", "semantic_appservice_status"),
            "покажи статус ai": ("статус ai", "semantic_ai_status"),
            "статус микрофона": ("статус микрофона", "semantic_microphone_status"),
        }
        target = semantic_commands.get(normalized)
        if target is None:
            return None
        command_text, reason = target
        metadata = self._match_registry_command(command_text)
        if metadata is not None and not metadata.read_only:
            return None
        if metadata is not None:
            return metadata, command_text, reason
        if command_text == "статус микрофона":
            return (
                CommandMetadata(
                    command_id="microphone.status",
                    title_ru="Статус микрофона",
                    description_ru="Статус микрофона через CommandProcessor.",
                    category=self.command_registry.find_by_alias("статус audio").category
                    if self.command_registry.find_by_alias("статус audio") is not None
                    else next(iter(self.command_registry.commands)).category,
                    aliases=("статус микрофона",),
                    risk_level=next(iter(self.command_registry.commands)).risk_level,
                    read_only=True,
                    voice_auto_allowed=True,
                    requires_confirmation=False,
                    requires_network=False,
                    requires_ai_key=False,
                    requires_privacy_check=False,
                    ui_visible=True,
                    app_ready=True,
                ),
                command_text,
                reason,
            )
        return None

    def _explicit_provider_request(self, text: str) -> CommandMetadata | None:
        metadata = self._match_registry_command(text)
        if metadata is not None and (metadata.requires_network or metadata.requires_ai_key):
            return metadata
        normalized = self.command_registry.normalize_alias(text)
        explicit_prefixes = (
            "ai реальный запрос:",
            "openai реальный запрос:",
            "gemini реальный запрос:",
            "groq реальный запрос:",
            "gigachat реальный запрос:",
            "ollama реальный запрос:",
            "консенсус ai:",
            "спроси все ai:",
            "сравни ответы ai:",
            "fallback ai запрос:",
        )
        if any(normalized.startswith(self.command_registry.normalize_alias(prefix)) for prefix in explicit_prefixes):
            return self._match_registry_command(text)
        return None

    @classmethod
    def _is_risky_question(cls, normalized: str) -> bool:
        if not any(normalized.startswith(prefix) for prefix in cls.RISKY_QUESTION_PREFIXES):
            return False
        return any(marker in normalized for marker in ("удал", "отправить письмо", "стереть"))

    @staticmethod
    def _looks_like_question(normalized: str) -> bool:
        return normalized.startswith(("как ", "что ", "почему ", "зачем ", "можно ли ", "какой ", "какая "))

    @classmethod
    def _is_exact_risky_existing_path(cls, normalized: str) -> bool:
        return any(normalized.startswith(prefix) for prefix in cls.EXACT_RISKY_PREFIXES)


def option_matches_text(option: AppClarificationOption, text: str, registry: CommandRegistry) -> bool:
    normalized = registry.normalize_alias(text)
    labels = {
        option.option_id,
        option.label_ru,
        option.command_text,
    }
    if option.option_id == "ai":
        labels.update({"ai", "ии"})
    if option.option_id == "system":
        labels.update({"система", "системы", "статус системы"})
    if option.option_id == "microphone":
        labels.update({"микрофон", "микрофона", "статус микрофона"})
    if option.option_id == "app_service":
        labels.update({"appservice", "app service", "сервис приложения"})
    if option.option_id == "language_ru":
        labels.update({"русский", "русский язык", "russian", "ru", "ru-ru"})
    if option.option_id == "language_en":
        labels.update({"английский", "английский язык", "english", "en", "en-us"})
    return any(normalized == registry.normalize_alias(label) for label in labels)


def contains_protected_text_shape(text: str) -> bool:
    raw = str(text or "")
    return bool(
        re.search(r"https?://|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|[A-Za-z]:\\|['\"].+['\"]", raw)
    )
