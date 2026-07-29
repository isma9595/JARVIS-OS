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


class ConversationContextContentClassification(Enum):
    BOUNDED_SAFE_TEXT = "bounded_safe_text"
    REDACTED_SENSITIVE_CONTENT = "redacted_sensitive_content"


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


def _nonnegative_int(value: object, field_name: str) -> int:
    if type(value) is not int:
        raise InvalidConversationTurnError(f"{field_name} must be an integer")
    if value < 0:
        raise InvalidConversationTurnError(f"{field_name} must be nonnegative")
    return value


def _positive_int(value: object, field_name: str) -> int:
    if type(value) is not int:
        raise InvalidConversationTurnError(f"{field_name} must be an integer")
    if value < 1:
        raise InvalidConversationTurnError(f"{field_name} must be positive")
    return value


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
class ConversationContextTurn(CognitiveContractMixin):
    turn_id: str
    sequence: int
    role: ConversationRole
    source: str
    safe_text: str
    created_at: str
    content_classification: ConversationContextContentClassification
    redaction_reason: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "turn_id", _clean_required_text(self.turn_id, "turn_id"))
        object.__setattr__(self, "sequence", _positive_int(self.sequence, "sequence"))
        object.__setattr__(self, "role", _conversation_role(self.role))
        object.__setattr__(self, "source", _clean_required_text(self.source, "source"))
        object.__setattr__(self, "safe_text", _clean_required_text(self.safe_text, "safe_text"))
        object.__setattr__(self, "created_at", _clean_required_text(self.created_at, "created_at"))
        object.__setattr__(
            self,
            "content_classification",
            _context_content_classification(self.content_classification),
        )
        object.__setattr__(self, "redaction_reason", _optional_clean_text(self.redaction_reason))


@dataclass(frozen=True)
class ConversationContextSnapshot(CognitiveContractMixin):
    session_id: str
    session_status: ConversationSessionStatus
    projected_at: str
    turns: tuple[ConversationContextTurn, ...]
    total_turn_count: int
    included_turn_count: int
    omitted_turn_count: int
    first_included_sequence: int | None = None
    last_included_sequence: int | None = None
    truncation_reason: str | None = None

    def __post_init__(self) -> None:
        turns = tuple(self.turns)
        object.__setattr__(self, "session_id", _clean_required_text(self.session_id, "session_id"))
        object.__setattr__(self, "session_status", _session_status(self.session_status))
        object.__setattr__(self, "projected_at", _clean_required_text(self.projected_at, "projected_at"))
        object.__setattr__(self, "turns", turns)
        object.__setattr__(self, "total_turn_count", _nonnegative_int(self.total_turn_count, "total_turn_count"))
        object.__setattr__(self, "included_turn_count", _nonnegative_int(self.included_turn_count, "included_turn_count"))
        object.__setattr__(self, "omitted_turn_count", _nonnegative_int(self.omitted_turn_count, "omitted_turn_count"))
        object.__setattr__(self, "first_included_sequence", _optional_positive_int(self.first_included_sequence, "first_included_sequence"))
        object.__setattr__(self, "last_included_sequence", _optional_positive_int(self.last_included_sequence, "last_included_sequence"))
        object.__setattr__(self, "truncation_reason", _optional_clean_text(self.truncation_reason))
        if self.included_turn_count != len(turns):
            raise InvalidConversationTurnError("included_turn_count must match turns")
        if self.total_turn_count != self.included_turn_count + self.omitted_turn_count:
            raise InvalidConversationTurnError("context turn counts are inconsistent")
        sequences = tuple(turn.sequence for turn in turns)
        if sequences != tuple(sorted(sequences)):
            raise InvalidConversationTurnError("context turns must be chronological")
        expected_first = sequences[0] if sequences else None
        expected_last = sequences[-1] if sequences else None
        if self.first_included_sequence != expected_first:
            raise InvalidConversationTurnError("first_included_sequence does not match turns")
        if self.last_included_sequence != expected_last:
            raise InvalidConversationTurnError("last_included_sequence does not match turns")


@dataclass(frozen=True)
class ResponseCompositionInput(CognitiveContractMixin):
    current_user_turn: ConversationTurn
    context: ConversationContextSnapshot
    source: str
    locale: str | None = None
    session: ConversationSessionSnapshot | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "source", _clean_required_text(self.source, "source"))
        object.__setattr__(self, "locale", _optional_clean_text(self.locale))


@dataclass(frozen=True)
class ResponseCompositionResult(CognitiveContractMixin):
    response_type: AssistantResponseType
    text: str
    context_turn_count_used: int
    composition_source: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "response_type", _response_type(self.response_type))
        object.__setattr__(self, "text", _clean_required_text(self.text, "text"))
        object.__setattr__(
            self,
            "context_turn_count_used",
            _nonnegative_int(self.context_turn_count_used, "context_turn_count_used"),
        )
        object.__setattr__(
            self,
            "composition_source",
            _clean_required_text(self.composition_source, "composition_source"),
        )


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
    context: ConversationContextSnapshot | None = None
    composition: ResponseCompositionResult | None = None


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


def _context_content_classification(value: object) -> ConversationContextContentClassification:
    if isinstance(value, ConversationContextContentClassification):
        return value
    return ConversationContextContentClassification(str(value))


def _optional_positive_int(value: object | None, field_name: str) -> int | None:
    if value is None:
        return None
    return _positive_int(value, field_name)
