"""Pure policy decision boundary for side-effect-capable requests.

This module is intentionally deterministic and metadata-only. It does not
execute commands, call ActionRouter, call providers, read credentials, touch
audio, or use GUI objects.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from enum import Enum
import re
from typing import Any

from core.command_registry import CommandMetadata, CommandRiskLevel


class PolicyDecisionType(Enum):
    ALLOW = "allow"
    REQUIRE_CONFIRMATION = "require_confirmation"
    DENY = "deny"


class PolicyCapability(Enum):
    READ_SYSTEM_STATE = "read_system_state"
    MICROPHONE_CAPTURE = "microphone_capture"
    NETWORK_PROVIDER_REQUEST = "network_provider_request"
    CREDENTIAL_USE = "credential_use"
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    FILE_DELETE = "file_delete"
    EMAIL_SEND = "email_send"
    PROCESS_LAUNCH = "process_launch"
    SYSTEM_CONTROL = "system_control"


@dataclass(frozen=True)
class PolicyRequest:
    source: str
    command_id: str | None = None
    action_id: str | None = None
    intent_kind: str | None = None
    risk: str | None = None
    required_capabilities: tuple[str, ...] = ()
    requires_network: bool = False
    confirmation_present: bool = False
    clarification_resolved: bool = True
    metadata: dict[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            field.name: _safe_value(getattr(self, field.name))
            for field in fields(self)
        }


@dataclass(frozen=True)
class PolicyDecision:
    decision: PolicyDecisionType
    reason_codes: tuple[str, ...]
    required_capabilities: tuple[str, ...]
    requires_confirmation: bool
    user_message: str
    safe_to_execute: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "decision": self.decision.value,
            "reason_codes": self.reason_codes,
            "required_capabilities": self.required_capabilities,
            "requires_confirmation": self.requires_confirmation,
            "user_message": _safe_text(self.user_message),
            "safe_to_execute": self.safe_to_execute,
        }


class PolicyDecisionBoundary:
    """Evaluate one safe metadata request into a deterministic decision."""

    FORBIDDEN_PATTERNS = (
        re.compile(r"\bsystem32\b", re.IGNORECASE),
        re.compile(r"форматир", re.IGNORECASE),
        re.compile(r"отключи\s+защит", re.IGNORECASE),
        re.compile(r"отключи\s+антивирус", re.IGNORECASE),
        re.compile(r"удали\s+все\s+файл", re.IGNORECASE),
    )
    VAGUE_DELETE_PATTERNS = (
        re.compile(r"^\s*удали\s+это\s*$", re.IGNORECASE),
        re.compile(r"^\s*удалить\s+это\s*$", re.IGNORECASE),
        re.compile(r"^\s*сотри\s+это\s*$", re.IGNORECASE),
    )
    FILE_DELETE_PATTERN = re.compile(r"^\s*удали\s+файл\s+\S+", re.IGNORECASE)

    def evaluate(self, request: PolicyRequest) -> PolicyDecision:
        text = _safe_text((request.metadata or {}).get("normalized_text", ""))
        reasons: list[str] = []
        capabilities = tuple(str(item) for item in request.required_capabilities)

        if not request.clarification_resolved:
            return self._deny(
                (*capabilities,),
                ("clarification_unresolved",),
                "Требуется уточнение. Команда не выполнялась.",
            )

        if any(pattern.search(text) for pattern in self.FORBIDDEN_PATTERNS):
            return self._deny(
                _merge_capabilities(capabilities, (PolicyCapability.SYSTEM_CONTROL.value,)),
                ("forbidden_command", "dangerous_system_target"),
                "Я не могу выполнить это действие. Запрос запрещён политикой безопасности. Команда не выполнялась.",
            )

        if any(pattern.search(text) for pattern in self.VAGUE_DELETE_PATTERNS):
            return self._deny(
                _merge_capabilities(capabilities, (PolicyCapability.FILE_DELETE.value,)),
                ("vague_risky_action", "missing_action_target"),
                "Нужна точная команда и цель действия. Команда не выполнялась.",
            )

        if request.requires_network:
            capabilities = _merge_capabilities(
                capabilities,
                (
                    PolicyCapability.NETWORK_PROVIDER_REQUEST.value,
                    PolicyCapability.CREDENTIAL_USE.value,
                ),
            )
            reasons.append("network_provider_request")

        if self.FILE_DELETE_PATTERN.search(text):
            capabilities = _merge_capabilities(
                capabilities,
                (PolicyCapability.FILE_DELETE.value,),
            )
            reasons.append("file_delete_request")

        read_only = "read_system_state" in capabilities and not request.requires_network
        risky = (
            not read_only
            and (
                request.risk
                in {
                    CommandRiskLevel.CONFIRMATION_REQUIRED.value,
                    CommandRiskLevel.NETWORK_EXPLICIT.value,
                    CommandRiskLevel.SENSITIVE.value,
                    CommandRiskLevel.LOCAL_RUNTIME.value,
                }
                or bool(reasons)
            )
        )
        if risky and not request.confirmation_present:
            return PolicyDecision(
                decision=PolicyDecisionType.REQUIRE_CONFIRMATION,
                reason_codes=tuple(reasons or ("risk_requires_confirmation",)),
                required_capabilities=capabilities,
                requires_confirmation=True,
                user_message="Требуется подтверждение. Команда не выполнена.",
                safe_to_execute=False,
            )

        return PolicyDecision(
            decision=PolicyDecisionType.ALLOW,
            reason_codes=tuple(reasons or ("safe_read_only",)),
            required_capabilities=capabilities,
            requires_confirmation=False,
            user_message="Разрешено политикой безопасности.",
            safe_to_execute=True,
        )

    @staticmethod
    def _deny(
        capabilities: tuple[str, ...],
        reasons: tuple[str, ...],
        message: str,
    ) -> PolicyDecision:
        return PolicyDecision(
            decision=PolicyDecisionType.DENY,
            reason_codes=reasons,
            required_capabilities=capabilities,
            requires_confirmation=False,
            user_message=message,
            safe_to_execute=False,
        )


def policy_request_from_metadata(
    *,
    source: str,
    text: str,
    metadata: CommandMetadata | None = None,
    intent_kind: str | None = None,
    confirmation_present: bool = False,
    clarification_resolved: bool = True,
) -> PolicyRequest:
    capabilities = _capabilities_for_metadata(metadata, text)
    return PolicyRequest(
        source=str(source or "unknown"),
        command_id=metadata.command_id if metadata is not None else None,
        action_id=None if metadata is not None else _action_id_for_text(text),
        intent_kind=intent_kind,
        risk=metadata.risk_level.value if metadata is not None else _risk_for_text(text),
        required_capabilities=capabilities,
        requires_network=bool(metadata.requires_network) if metadata is not None else False,
        confirmation_present=confirmation_present,
        clarification_resolved=clarification_resolved,
        metadata={"normalized_text": _safe_text(text)},
    )


def _capabilities_for_metadata(
    metadata: CommandMetadata | None,
    text: str,
) -> tuple[str, ...]:
    capabilities: list[str] = []
    if metadata is not None:
        if metadata.read_only:
            capabilities.append(PolicyCapability.READ_SYSTEM_STATE.value)
        if metadata.requires_network:
            capabilities.append(PolicyCapability.NETWORK_PROVIDER_REQUEST.value)
        if metadata.requires_ai_key:
            capabilities.append(PolicyCapability.CREDENTIAL_USE.value)
        if metadata.command_id.startswith("secure_keys.delete"):
            capabilities.append(PolicyCapability.CREDENTIAL_USE.value)
        if metadata.command_id == "system.exit":
            capabilities.append(PolicyCapability.SYSTEM_CONTROL.value)
    normalized = str(text or "").strip().lower()
    if normalized.startswith(("удали файл ", "удалить файл ")):
        capabilities.append(PolicyCapability.FILE_DELETE.value)
    if "отправь письмо" in normalized:
        capabilities.append(PolicyCapability.EMAIL_SEND.value)
    if "открой браузер" in normalized or "открой приложение" in normalized:
        capabilities.append(PolicyCapability.PROCESS_LAUNCH.value)
    return tuple(dict.fromkeys(capabilities))


def _action_id_for_text(text: str) -> str | None:
    normalized = str(text or "").strip().lower()
    if normalized.startswith(("удали файл ", "удалить файл ")):
        return "file.delete"
    if "system32" in normalized:
        return "system.delete_protected_path"
    return None


def _risk_for_text(text: str) -> str:
    normalized = str(text or "").strip().lower()
    if "system32" in normalized:
        return CommandRiskLevel.DESTRUCTIVE_BLOCKED.value
    if normalized.startswith(("удали файл ", "удалить файл ")):
        return CommandRiskLevel.CONFIRMATION_REQUIRED.value
    return CommandRiskLevel.READ_ONLY.value


def _safe_text(value: Any) -> str:
    text = str(value or "")
    return re.sub(
        r"(?i)(sk-[a-z0-9_-]{8,}|api[_ -]?key\s*[:=]?\s*\S+|token\s*[:=]?\s*\S+)",
        "[REDACTED]",
        text,
    )


def _safe_value(value: Any) -> object:
    if isinstance(value, str):
        return _safe_text(value)
    if isinstance(value, tuple):
        return tuple(_safe_value(item) for item in value)
    if isinstance(value, list):
        return tuple(_safe_value(item) for item in value)
    if isinstance(value, dict):
        return {str(key): _safe_value(item) for key, item in value.items()}
    if isinstance(value, Enum):
        return value.value
    return value


def _merge_capabilities(
    current: tuple[str, ...],
    additional: tuple[str, ...],
) -> tuple[str, ...]:
    return tuple(dict.fromkeys((*current, *additional)))
