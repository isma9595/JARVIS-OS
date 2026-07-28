"""Minimal cognitive contracts for conversation session orchestration.

These contracts are immutable, JSON-safe DTOs. They intentionally do not carry
execution, workflow, provider, memory, knowledge, goal, or plan payloads.
"""

from dataclasses import dataclass, fields
from enum import Enum
import re
from typing import Any


_SECRET_PATTERN = re.compile(
    r"(?i)(sk-[a-z0-9_-]{8,}|api[_ -]?key\s*[:=]?\s*\S+|token\s*[:=]?\s*\S+)"
)


class CognitiveContractError(ValueError):
    """Base error for invalid cognitive contract values."""


class InvalidConversationTurnError(CognitiveContractError):
    """Raised when a conversation turn input is not valid."""


class ConversationSessionStatus(Enum):
    ACTIVE = "active"
    CLOSED = "closed"


class ConversationRole(Enum):
    USER = "user"
    ASSISTANT = "assistant"


class AssistantResponseType(Enum):
    MESSAGE = "message"
    ERROR = "error"


def safe_cognitive_text(text: object) -> str:
    return _SECRET_PATTERN.sub("[REDACTED]", str(text or ""))


def _safe_value(value: Any) -> object:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, str):
        return safe_cognitive_text(value)
    if isinstance(value, tuple):
        return tuple(_safe_value(item) for item in value)
    if isinstance(value, list):
        return tuple(_safe_value(item) for item in value)
    if hasattr(value, "to_dict"):
        return value.to_dict()
    return value


class CognitiveContractMixin:
    def to_dict(self) -> dict[str, object]:
        return {field.name: _safe_value(getattr(self, field.name)) for field in fields(self)}


def _clean_required_text(value: object, field_name: str) -> str:
    cleaned = str(value or "").strip()
    if not cleaned:
        raise InvalidConversationTurnError(f"{field_name} must not be empty")
    return safe_cognitive_text(cleaned)


def _optional_clean_text(value: object | None) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return safe_cognitive_text(cleaned) if cleaned else None


@dataclass(frozen=True)
class ConversationTurnInput(CognitiveContractMixin):
    text: str
    source: str
    session_id: str | None = None
    locale: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "text", _clean_required_text(self.text, "text"))
        object.__setattr__(self, "source", _clean_required_text(self.source, "source"))
        object.__setattr__(self, "session_id", _optional_clean_text(self.session_id))
        object.__setattr__(self, "locale", _optional_clean_text(self.locale))


@dataclass(frozen=True)
class ConversationSessionSnapshot(CognitiveContractMixin):
    session_id: str
    status: ConversationSessionStatus
    created_at: str
    updated_at: str
    turn_count: int
    last_turn_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "session_id", _clean_required_text(self.session_id, "session_id"))
        object.__setattr__(self, "status", _session_status(self.status))
        object.__setattr__(self, "created_at", _clean_required_text(self.created_at, "created_at"))
        object.__setattr__(self, "updated_at", _clean_required_text(self.updated_at, "updated_at"))
        object.__setattr__(self, "turn_count", max(0, int(self.turn_count)))
        object.__setattr__(self, "last_turn_id", _optional_clean_text(self.last_turn_id))


@dataclass(frozen=True)
class ConversationTurn(CognitiveContractMixin):
    turn_id: str
    session_id: str
    sequence: int
    role: ConversationRole
    text: str
    source: str
    created_at: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "turn_id", _clean_required_text(self.turn_id, "turn_id"))
        object.__setattr__(self, "session_id", _clean_required_text(self.session_id, "session_id"))
        object.__setattr__(self, "sequence", int(self.sequence))
        if self.sequence < 1:
            raise InvalidConversationTurnError("sequence must be positive")
        object.__setattr__(self, "role", _conversation_role(self.role))
        object.__setattr__(self, "text", _clean_required_text(self.text, "text"))
        object.__setattr__(self, "source", _clean_required_text(self.source, "source"))
        object.__setattr__(self, "created_at", _clean_required_text(self.created_at, "created_at"))


@dataclass(frozen=True)
class AssistantResponse(CognitiveContractMixin):
    response_id: str
    session_id: str
    turn_id: str
    response_type: AssistantResponseType
    text: str
    created_at: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "response_id", _clean_required_text(self.response_id, "response_id"))
        object.__setattr__(self, "session_id", _clean_required_text(self.session_id, "session_id"))
        object.__setattr__(self, "turn_id", _clean_required_text(self.turn_id, "turn_id"))
        object.__setattr__(self, "response_type", _response_type(self.response_type))
        object.__setattr__(self, "text", _clean_required_text(self.text, "text"))
        object.__setattr__(self, "created_at", _clean_required_text(self.created_at, "created_at"))


@dataclass(frozen=True)
class CognitiveInteractionResult(CognitiveContractMixin):
    response: AssistantResponse
    session: ConversationSessionSnapshot


def _session_status(value: object) -> ConversationSessionStatus:
    if isinstance(value, ConversationSessionStatus):
        return value
    return ConversationSessionStatus(str(value))


def _conversation_role(value: object) -> ConversationRole:
    if isinstance(value, ConversationRole):
        return value
    return ConversationRole(str(value))


def _response_type(value: object) -> AssistantResponseType:
    if isinstance(value, AssistantResponseType):
        return value
    return AssistantResponseType(str(value))
