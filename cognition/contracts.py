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


class IntentCategory(Enum):
    CONVERSATION = "conversation"
    QUESTION = "question"
    INFORMATION_REQUEST = "information_request"
    ACTION_REQUEST = "action_request"
    CLARIFICATION_RESPONSE = "clarification_response"
    CANCELLATION = "cancellation"
    CONFIRMATION = "confirmation"
    REJECTION = "rejection"
    UNKNOWN = "unknown"


class IntentConfidence(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ReferenceKind(Enum):
    PRONOUN = "pronoun"
    DEMONSTRATIVE = "demonstrative"
    PREVIOUS_MESSAGE = "previous_message"
    PREVIOUS_RESPONSE = "previous_response"
    PREVIOUS_REQUEST = "previous_request"
    PREVIOUS_RESULT = "previous_result"
    ORDINAL_TURN = "ordinal_turn"
    EXPLICIT_QUOTE = "explicit_quote"
    UNKNOWN = "unknown"


class ReferenceResolutionStatus(Enum):
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    AMBIGUOUS = "ambiguous"
    NOT_APPLICABLE = "not_applicable"


MAX_INTENT_SAFE_TEXT_LENGTH = 240
MAX_INTENT_EVIDENCE_TEXT_LENGTH = 120
MAX_REFERENCE_SURFACE_TEXT_LENGTH = 80
MAX_REFERENCE_CANDIDATE_EXCERPT_LENGTH = 160


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
class IntentEvidence(CognitiveContractMixin):
    evidence_type: str
    safe_excerpt: str
    rule_id: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "evidence_type",
            _clean_required_text(self.evidence_type, "evidence_type"),
        )
        object.__setattr__(
            self,
            "safe_excerpt",
            _bounded_required_text(
                self.safe_excerpt,
                "safe_excerpt",
                MAX_INTENT_EVIDENCE_TEXT_LENGTH,
            ),
        )
        object.__setattr__(self, "rule_id", _clean_required_text(self.rule_id, "rule_id"))


@dataclass(frozen=True)
class InterpretedIntent(CognitiveContractMixin):
    category: IntentCategory
    confidence: IntentConfidence
    safe_user_text: str
    evidence: tuple[IntentEvidence, ...]
    requires_reference_resolution: bool
    may_require_clarification: bool
    is_actionable_request: bool
    interpreter_id: str
    interpreter_version: str
    context_turn_count_used: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "category", _intent_category(self.category))
        object.__setattr__(self, "confidence", _intent_confidence(self.confidence))
        object.__setattr__(
            self,
            "safe_user_text",
            _bounded_required_text(
                self.safe_user_text,
                "safe_user_text",
                MAX_INTENT_SAFE_TEXT_LENGTH,
            ),
        )
        evidence = tuple(self.evidence)
        if not all(isinstance(item, IntentEvidence) for item in evidence):
            raise InvalidConversationTurnError("evidence must contain intent evidence")
        object.__setattr__(self, "evidence", evidence)
        object.__setattr__(
            self,
            "requires_reference_resolution",
            _strict_bool(
                self.requires_reference_resolution,
                "requires_reference_resolution",
            ),
        )
        object.__setattr__(
            self,
            "may_require_clarification",
            _strict_bool(self.may_require_clarification, "may_require_clarification"),
        )
        object.__setattr__(
            self,
            "is_actionable_request",
            _strict_bool(self.is_actionable_request, "is_actionable_request"),
        )
        object.__setattr__(
            self,
            "interpreter_id",
            _clean_required_text(self.interpreter_id, "interpreter_id"),
        )
        object.__setattr__(
            self,
            "interpreter_version",
            _clean_required_text(self.interpreter_version, "interpreter_version"),
        )
        object.__setattr__(
            self,
            "context_turn_count_used",
            _nonnegative_int(self.context_turn_count_used, "context_turn_count_used"),
        )


@dataclass(frozen=True)
class IntentInterpretationInput(CognitiveContractMixin):
    current_user_turn: ConversationTurn
    context: ConversationContextSnapshot
    source: str
    locale: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.current_user_turn, ConversationTurn):
            raise InvalidConversationTurnError("current_user_turn must be a conversation turn")
        if not isinstance(self.context, ConversationContextSnapshot):
            raise InvalidConversationTurnError("context must be a conversation context snapshot")
        object.__setattr__(self, "source", _clean_required_text(self.source, "source"))
        object.__setattr__(self, "locale", _optional_clean_text(self.locale))


@dataclass(frozen=True)
class ReferenceCandidate(CognitiveContractMixin):
    turn_id: str
    turn_sequence: int
    role: ConversationRole
    safe_excerpt: str
    match_reason: str
    recency_rank: int
    confidence: IntentConfidence

    def __post_init__(self) -> None:
        object.__setattr__(self, "turn_id", _clean_required_text(self.turn_id, "turn_id"))
        object.__setattr__(
            self,
            "turn_sequence",
            _positive_int(self.turn_sequence, "turn_sequence"),
        )
        object.__setattr__(self, "role", _conversation_role(self.role))
        object.__setattr__(
            self,
            "safe_excerpt",
            _bounded_required_text(
                self.safe_excerpt,
                "safe_excerpt",
                MAX_REFERENCE_CANDIDATE_EXCERPT_LENGTH,
            ),
        )
        object.__setattr__(
            self,
            "match_reason",
            _clean_required_text(self.match_reason, "match_reason"),
        )
        object.__setattr__(self, "recency_rank", _positive_int(self.recency_rank, "recency_rank"))
        object.__setattr__(self, "confidence", _intent_confidence(self.confidence))


@dataclass(frozen=True)
class DetectedReference(CognitiveContractMixin):
    kind: ReferenceKind
    safe_surface_text: str
    rule_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", _reference_kind(self.kind))
        object.__setattr__(
            self,
            "safe_surface_text",
            _bounded_required_text(
                self.safe_surface_text,
                "safe_surface_text",
                MAX_REFERENCE_SURFACE_TEXT_LENGTH,
            ),
        )
        object.__setattr__(self, "rule_id", _clean_required_text(self.rule_id, "rule_id"))


@dataclass(frozen=True)
class ResolvedReference(CognitiveContractMixin):
    detected_reference: DetectedReference
    status: ReferenceResolutionStatus
    selected_candidate: ReferenceCandidate | None
    candidates: tuple[ReferenceCandidate, ...]
    confidence: IntentConfidence
    context_turn_count_used: int
    resolver_id: str
    resolver_version: str

    def __post_init__(self) -> None:
        if not isinstance(self.detected_reference, DetectedReference):
            raise InvalidConversationTurnError("detected_reference must be a detected reference")
        object.__setattr__(self, "status", _reference_resolution_status(self.status))
        if self.selected_candidate is not None and not isinstance(
            self.selected_candidate,
            ReferenceCandidate,
        ):
            raise InvalidConversationTurnError("selected_candidate must be a reference candidate")
        candidates = tuple(self.candidates)
        if not all(isinstance(item, ReferenceCandidate) for item in candidates):
            raise InvalidConversationTurnError("candidates must contain reference candidates")
        object.__setattr__(self, "candidates", candidates)
        object.__setattr__(self, "confidence", _intent_confidence(self.confidence))
        object.__setattr__(
            self,
            "context_turn_count_used",
            _nonnegative_int(self.context_turn_count_used, "context_turn_count_used"),
        )
        object.__setattr__(
            self,
            "resolver_id",
            _clean_required_text(self.resolver_id, "resolver_id"),
        )
        object.__setattr__(
            self,
            "resolver_version",
            _clean_required_text(self.resolver_version, "resolver_version"),
        )
        if self.status is ReferenceResolutionStatus.RESOLVED and self.selected_candidate is None:
            raise InvalidConversationTurnError("resolved references require a selected candidate")
        if self.status is not ReferenceResolutionStatus.RESOLVED and self.selected_candidate is not None:
            raise InvalidConversationTurnError("unresolved references cannot select a candidate")


@dataclass(frozen=True)
class ReferenceResolutionInput(CognitiveContractMixin):
    current_user_turn: ConversationTurn
    context: ConversationContextSnapshot
    interpreted_intent: InterpretedIntent

    def __post_init__(self) -> None:
        if not isinstance(self.current_user_turn, ConversationTurn):
            raise InvalidConversationTurnError("current_user_turn must be a conversation turn")
        if not isinstance(self.context, ConversationContextSnapshot):
            raise InvalidConversationTurnError("context must be a conversation context snapshot")
        if not isinstance(self.interpreted_intent, InterpretedIntent):
            raise InvalidConversationTurnError("interpreted_intent must be an interpreted intent")


@dataclass(frozen=True)
class ReferenceResolutionResult(CognitiveContractMixin):
    references: tuple[ResolvedReference, ...]
    has_unresolved_references: bool
    has_ambiguous_references: bool
    context_turn_count_used: int
    resolver_id: str
    resolver_version: str

    def __post_init__(self) -> None:
        references = tuple(self.references)
        if not all(isinstance(item, ResolvedReference) for item in references):
            raise InvalidConversationTurnError("references must contain resolved references")
        object.__setattr__(self, "references", references)
        expected_unresolved = any(
            item.status is ReferenceResolutionStatus.UNRESOLVED for item in references
        )
        expected_ambiguous = any(
            item.status is ReferenceResolutionStatus.AMBIGUOUS for item in references
        )
        object.__setattr__(
            self,
            "has_unresolved_references",
            _strict_bool(self.has_unresolved_references, "has_unresolved_references"),
        )
        object.__setattr__(
            self,
            "has_ambiguous_references",
            _strict_bool(self.has_ambiguous_references, "has_ambiguous_references"),
        )
        if self.has_unresolved_references != expected_unresolved:
            raise InvalidConversationTurnError("unresolved reference diagnostics are inconsistent")
        if self.has_ambiguous_references != expected_ambiguous:
            raise InvalidConversationTurnError("ambiguous reference diagnostics are inconsistent")
        object.__setattr__(
            self,
            "context_turn_count_used",
            _nonnegative_int(self.context_turn_count_used, "context_turn_count_used"),
        )
        object.__setattr__(
            self,
            "resolver_id",
            _clean_required_text(self.resolver_id, "resolver_id"),
        )
        object.__setattr__(
            self,
            "resolver_version",
            _clean_required_text(self.resolver_version, "resolver_version"),
        )


@dataclass(frozen=True)
class ResponseCompositionInput(CognitiveContractMixin):
    current_user_turn: ConversationTurn
    context: ConversationContextSnapshot
    source: str
    locale: str | None = None
    session: ConversationSessionSnapshot | None = None
    interpreted_intent: InterpretedIntent | None = None
    reference_resolution: ReferenceResolutionResult | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.current_user_turn, ConversationTurn):
            raise InvalidConversationTurnError("current_user_turn must be a conversation turn")
        if not isinstance(self.context, ConversationContextSnapshot):
            raise InvalidConversationTurnError("context must be a conversation context snapshot")
        object.__setattr__(self, "source", _clean_required_text(self.source, "source"))
        object.__setattr__(self, "locale", _optional_clean_text(self.locale))
        if self.session is not None and not isinstance(self.session, ConversationSessionSnapshot):
            raise InvalidConversationTurnError("session must be a conversation session snapshot")
        if self.interpreted_intent is not None and not isinstance(
            self.interpreted_intent,
            InterpretedIntent,
        ):
            raise InvalidConversationTurnError("interpreted_intent must be an interpreted intent")
        if self.reference_resolution is not None and not isinstance(
            self.reference_resolution,
            ReferenceResolutionResult,
        ):
            raise InvalidConversationTurnError(
                "reference_resolution must be a reference resolution result"
            )


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
    intent: InterpretedIntent | None = None
    references: ReferenceResolutionResult | None = None


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


def _intent_category(value: object) -> IntentCategory:
    if isinstance(value, IntentCategory):
        return value
    return IntentCategory(str(value))


def _intent_confidence(value: object) -> IntentConfidence:
    if isinstance(value, IntentConfidence):
        return value
    return IntentConfidence(str(value))


def _reference_kind(value: object) -> ReferenceKind:
    if isinstance(value, ReferenceKind):
        return value
    return ReferenceKind(str(value))


def _reference_resolution_status(value: object) -> ReferenceResolutionStatus:
    if isinstance(value, ReferenceResolutionStatus):
        return value
    return ReferenceResolutionStatus(str(value))


def _optional_positive_int(value: object | None, field_name: str) -> int | None:
    if value is None:
        return None
    return _positive_int(value, field_name)


def _strict_bool(value: object, field_name: str) -> bool:
    if type(value) is not bool:
        raise InvalidConversationTurnError(f"{field_name} must be a boolean")
    return value


def _bounded_optional_text(value: object | None, max_length: int) -> str | None:
    cleaned = _optional_clean_text(value)
    if cleaned is None:
        return None
    return _truncate_contract_text(cleaned, max_length)


def _bounded_required_text(value: object, field_name: str, max_length: int) -> str:
    return _truncate_contract_text(_clean_required_text(value, field_name), max_length)


def _truncate_contract_text(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    if max_length <= 3:
        return "." * max_length
    return text[: max_length - 3].rstrip() + "..."
