"""Deterministic CommandProcessor text resolution.

This module is an internal interpretation boundary. It normalizes input,
selects known deterministic command routes, projects clarification options,
and extracts safe text arguments. It does not execute commands or mutate
application state.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import TypeAlias, Mapping

from app.app_contracts import AppClarificationOption
from app.intent_resolver import (
    ClarificationState,
    HybridIntentResolver,
    ResolutionStatus as HybridResolutionStatus,
    option_matches_text,
)
from core.command_registry import CommandMetadata, CommandRegistry


class CommandResolutionStatus(Enum):
    EMPTY = "empty"
    RESOLVED = "resolved"
    LEGACY_PASSTHROUGH = "legacy_passthrough"
    REQUIRES_CLARIFICATION = "requires_clarification"
    UNKNOWN = "unknown"


CommandGroupValue: TypeAlias = Mapping[str, object] | tuple[str, ...] | frozenset[str]


@dataclass(frozen=True)
class CommandResolution:
    original_text: str
    normalized_text: str
    resolution_status: CommandResolutionStatus
    command_id: str | None
    category: str | None
    safe_args: Mapping[str, object]
    clarification_required: bool
    clarification_prompt: str | None
    clarification_candidates: tuple[AppClarificationOption, ...]
    confidence: str | None
    match_source: str | None
    safe_reason_code: str | None
    unknown: bool
    command_text: str | None = None
    metadata: CommandMetadata | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "safe_args",
            MappingProxyType(dict(self.safe_args)),
        )
        object.__setattr__(
            self,
            "clarification_candidates",
            tuple(self.clarification_candidates),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "original_text": self.original_text,
            "normalized_text": self.normalized_text,
            "resolution_status": self.resolution_status.value,
            "command_id": self.command_id,
            "category": self.category,
            "safe_args": dict(self.safe_args),
            "clarification_required": self.clarification_required,
            "clarification_prompt": self.clarification_prompt,
            "clarification_candidates": tuple(
                candidate.to_dict() for candidate in self.clarification_candidates
            ),
            "confidence": self.confidence,
            "match_source": self.match_source,
            "safe_reason_code": self.safe_reason_code,
            "unknown": self.unknown,
            "command_text": self.command_text,
        }


class CommandResolutionService:
    """Resolve command text without executing the resulting command."""

    _DISPATCHED_REGISTRY_IDS = frozenset(
        {
            "system.status",
            "profile.language.status",
            "profile.language.set",
            "profile.language.reset",
        }
    )

    def __init__(
        self,
        *,
        command_registry: CommandRegistry,
        command_groups: Mapping[str, object],
        hybrid_intent_resolver: HybridIntentResolver | None = None,
    ):
        self.command_registry = command_registry
        self.command_groups = MappingProxyType(
            {
                str(name): self._freeze_group_value(value)
                for name, value in command_groups.items()
            }
        )
        self.hybrid_intent_resolver = hybrid_intent_resolver or HybridIntentResolver(
            command_registry
        )

    def normalize(self, command_text: object) -> str:
        if command_text is None:
            return ""
        return " ".join(str(command_text).strip().lower().split())

    def resolve(
        self,
        command_text: object,
        *,
        pending_clarification: ClarificationState | None = None,
        source: str = "command_processor",
    ) -> CommandResolution:
        original = str(command_text or "").strip()
        normalized = self.normalize(command_text)
        if not normalized:
            return self._empty(original, normalized)

        if pending_clarification is not None:
            selected = self.select_clarification(
                pending_clarification,
                normalized,
            )
            if selected is not None:
                return self._resolved(
                    original,
                    self.normalize(selected.command_text),
                    selected.command_id,
                    "clarification",
                    "clarification_selection",
                    {"option_id": selected.option_id},
                    command_text=selected.command_text,
                )
            independent = self._resolve_independent(original, normalized, source)
            if independent.resolution_status != CommandResolutionStatus.UNKNOWN:
                return independent
            return self._pending_clarification_still_required(
                original,
                normalized,
                pending_clarification,
            )

        return self._resolve_independent(original, normalized, source)

    def _resolve_independent(
        self,
        original: str,
        normalized: str,
        source: str,
    ) -> CommandResolution:
        direct = self._resolve_direct(original, normalized)
        if direct is not None:
            return direct

        hybrid = self.hybrid_intent_resolver.resolve(
            original,
            source=source,
            processing_text=normalized,
        )
        if (
            hybrid.resolution_status == HybridResolutionStatus.REQUIRES_CLARIFICATION
            and hybrid.requires_clarification
        ):
            return CommandResolution(
                original_text=original,
                normalized_text=normalized,
                resolution_status=CommandResolutionStatus.REQUIRES_CLARIFICATION,
                command_id=None,
                category="clarification",
                safe_args={},
                clarification_required=True,
                clarification_prompt=hybrid.clarification_question,
                clarification_candidates=hybrid.clarification_options,
                confidence=hybrid.confidence.value,
                match_source="hybrid_intent_resolver",
                safe_reason_code=self._first_reason(hybrid.reason_codes),
                unknown=False,
                command_text=None,
                metadata=None,
            )

        metadata = self.command_registry.find_by_alias(normalized)
        if metadata is not None:
            if metadata.command_id not in self._DISPATCHED_REGISTRY_IDS:
                return self._legacy_passthrough(
                    original,
                    normalized,
                    "registry_alias_legacy_passthrough",
                    metadata=metadata,
                )
            return self._resolved(
                original,
                normalized,
                metadata.command_id,
                metadata.category.value,
                "registry_alias",
                {},
                command_text=normalized,
                metadata=metadata,
            )

        legacy = self._resolve_legacy_passthrough(original, normalized)
        if legacy is not None:
            return legacy

        return CommandResolution(
            original_text=original,
            normalized_text=normalized,
            resolution_status=CommandResolutionStatus.UNKNOWN,
            command_id=None,
            category="unknown",
            safe_args={},
            clarification_required=False,
            clarification_prompt=None,
            clarification_candidates=(),
            confidence="low",
            match_source="action_router_fallback",
            safe_reason_code="legacy_unknown_fallback",
            unknown=True,
            command_text=normalized,
            metadata=None,
        )

    def select_clarification(
        self,
        pending_clarification: ClarificationState,
        text: str,
    ) -> AppClarificationOption | None:
        for option in pending_clarification.options:
            if option_matches_text(option, text, self.command_registry):
                return option
        return None

    def _resolve_direct(
        self,
        original: str,
        normalized: str,
    ) -> CommandResolution | None:
        exact_groups = {
            "system.status": ("system_status", "system"),
            "command_registry.status": ("command_registry_status", "command_registry"),
            "command_registry.list": ("command_registry_list", "command_registry"),
            "command_registry.categories": (
                "command_registry_categories",
                "command_registry",
            ),
            "desktop_shell.status": ("desktop_shell_status", "app"),
            "desktop_shell.capabilities": ("desktop_shell_capabilities", "app"),
            "app_service.status": ("app_service_status", "app"),
            "app_service.capabilities": ("app_service_capabilities", "app"),
            "app_service.commands": ("app_service_commands", "app"),
            "conversation.status": ("conversation_status", "conversation"),
            "conversation.capabilities": ("conversation_capabilities", "conversation"),
            "vertical_integration.status": ("vertical_integration_status", "integration"),
            "vertical_integration.checklist": (
                "vertical_integration_checklist",
                "integration",
            ),
            "vertical_integration.summary": ("vertical_integration_summary", "integration"),
            "audio_lifecycle.status": ("audio_lifecycle_status", "audio"),
            "audio_lifecycle.capabilities": ("audio_lifecycle_capabilities", "audio"),
            "audio_lifecycle.reset_metadata_only": ("audio_lifecycle_reset", "audio"),
            "app_contracts.status": ("app_contracts_status", "app"),
            "app_contracts.manifest": ("app_contracts_manifest", "app"),
            "app_contracts.status_cards": ("app_contracts_status_cards", "app"),
            "app_contracts.command_cards": ("app_contracts_command_cards", "app"),
            "memory.delete.requested": ("memory_delete", "memory"),
            "memory.count": ("memory_count", "memory"),
            "memory.recent": ("memory_recent", "memory"),
            "memory.about_user": ("memory_about_user", "memory"),
            "memory.list": ("memory_list", "memory"),
            "idea.list": ("idea_list", "ideas"),
            "idea.count": ("idea_count", "ideas"),
            "profile.language.status": ("language_status", "profile"),
            "profile.language.reset": ("language_reset", "profile"),
        }
        for command_id, (group_name, category) in exact_groups.items():
            if normalized in self._set(group_name):
                return self._resolved(
                    original,
                    normalized,
                    command_id,
                    category,
                    "exact_command_group",
                    {},
                )

        category = self._dict("command_registry_category").get(normalized)
        if category is not None:
            return self._resolved(
                original,
                normalized,
                "command_registry.category",
                "command_registry",
                "exact_command_group",
                {"category": category},
            )

        provider = self._dict("provider_runtime_provider").get(normalized)
        if provider is not None:
            return self._resolved(
                original,
                normalized,
                "ai.provider_runtime.provider_status",
                "provider_runtime",
                "exact_command_group",
                {"provider": provider},
            )

        language = self._dict("language_set").get(normalized)
        if language is not None:
            return self._resolved(
                original,
                normalized,
                "profile.language.set",
                "profile",
                "exact_command_group",
                {"language": language},
            )

        prefixed = (
            ("command_registry.search", "command_registry_search", "command_registry", "query"),
            ("app_service.preview", "app_service_preview", "app", "preview_text"),
            ("conversation.preview", "conversation_preview", "conversation", "conversation_text"),
            ("idea.add", "idea_add", "ideas", "content"),
            ("memory.add", "memory_add", "memory", "content"),
            ("memory.search", "memory_search", "memory", "query"),
        )
        for command_id, group_name, category, arg_name in prefixed:
            value = self._extract_prefixed_text(normalized, self._tuple(group_name))
            if value is not None:
                return self._resolved(
                    original,
                    normalized,
                    command_id,
                    category,
                    "prefix_command_group",
                    {arg_name: value},
                )
        return None

    def _resolve_legacy_passthrough(
        self,
        original: str,
        normalized: str,
    ) -> CommandResolution | None:
        if normalized in self._set("legacy_passthrough_exact"):
            return self._legacy_passthrough(
                original,
                normalized,
                "legacy_command_group",
            )
        if normalized in self._dict("legacy_passthrough_mapping"):
            return self._legacy_passthrough(
                original,
                normalized,
                "legacy_command_group",
            )
        if self._extract_prefixed_text(
            normalized,
            self._tuple("legacy_passthrough_prefix"),
        ) is not None:
            return self._legacy_passthrough(
                original,
                normalized,
                "legacy_command_group",
            )
        return None

    def _resolved(
        self,
        original: str,
        normalized: str,
        command_id: str | None,
        category: str | None,
        match_source: str,
        safe_args: Mapping[str, object],
        *,
        command_text: str | None = None,
        metadata: CommandMetadata | None = None,
    ) -> CommandResolution:
        if metadata is None and command_id is not None:
            metadata = self.command_registry.find_by_id(command_id)
        if category is None and metadata is not None:
            category = metadata.category.value
        return CommandResolution(
            original_text=original,
            normalized_text=normalized,
            resolution_status=CommandResolutionStatus.RESOLVED,
            command_id=command_id,
            category=category,
            safe_args=dict(safe_args),
            clarification_required=False,
            clarification_prompt=None,
            clarification_candidates=(),
            confidence="high",
            match_source=match_source,
            safe_reason_code=None,
            unknown=False,
            command_text=command_text or normalized,
            metadata=metadata,
        )

    def _legacy_passthrough(
        self,
        original: str,
        normalized: str,
        match_source: str,
        *,
        metadata: CommandMetadata | None = None,
    ) -> CommandResolution:
        return CommandResolution(
            original_text=original,
            normalized_text=normalized,
            resolution_status=CommandResolutionStatus.LEGACY_PASSTHROUGH,
            command_id=metadata.command_id if metadata is not None else None,
            category=metadata.category.value if metadata is not None else "legacy",
            safe_args={},
            clarification_required=False,
            clarification_prompt=None,
            clarification_candidates=(),
            confidence="medium",
            match_source=match_source,
            safe_reason_code="phase1_legacy_passthrough",
            unknown=False,
            command_text=normalized,
            metadata=metadata,
        )

    @staticmethod
    def _pending_clarification_still_required(
        original: str,
        normalized: str,
        pending_clarification: ClarificationState,
    ) -> CommandResolution:
        return CommandResolution(
            original_text=original,
            normalized_text=normalized,
            resolution_status=CommandResolutionStatus.REQUIRES_CLARIFICATION,
            command_id=None,
            category="clarification",
            safe_args={},
            clarification_required=True,
            clarification_prompt=pending_clarification.question_ru,
            clarification_candidates=pending_clarification.options,
            confidence="low",
            match_source="invalid_clarification_answer",
            safe_reason_code="clarification_answer_not_matched",
            unknown=False,
            command_text=normalized,
            metadata=None,
        )

    @staticmethod
    def _empty(original: str, normalized: str) -> CommandResolution:
        return CommandResolution(
            original_text=original,
            normalized_text=normalized,
            resolution_status=CommandResolutionStatus.EMPTY,
            command_id="empty",
            category="system",
            safe_args={},
            clarification_required=False,
            clarification_prompt=None,
            clarification_candidates=(),
            confidence="high",
            match_source="normalization",
            safe_reason_code="empty_input",
            unknown=False,
            command_text=normalized,
            metadata=None,
        )

    def _set(self, name: str) -> set[str]:
        value = self.command_groups.get(name, ())
        if isinstance(value, Mapping):
            return set(value)
        return set(value or ())

    def _tuple(self, name: str) -> tuple[str, ...]:
        value = self.command_groups.get(name, ())
        if isinstance(value, tuple):
            return value
        return tuple(value or ())

    def _dict(self, name: str) -> Mapping[str, object]:
        value = self.command_groups.get(name, {})
        return value if isinstance(value, Mapping) else {}

    @staticmethod
    def _freeze_group_value(value: object) -> CommandGroupValue:
        """Supported command-group values: exact iterables, prefix tuples, and mappings."""
        if isinstance(value, Mapping):
            return MappingProxyType(dict(value))
        if isinstance(value, tuple):
            return tuple(value)
        return frozenset(value or ())

    @staticmethod
    def _extract_prefixed_text(command: str, prefixes: tuple[str, ...]) -> str | None:
        for prefix in prefixes:
            if command == prefix:
                return ""
            if prefix.endswith(":") and command.startswith(prefix):
                return command[len(prefix) :].strip()
            if command.startswith(prefix + " "):
                return command[len(prefix) :].strip()
        return None

    @staticmethod
    def _first_reason(reason_codes: tuple[str, ...]) -> str | None:
        return reason_codes[0] if reason_codes else None
