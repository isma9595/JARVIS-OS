from __future__ import annotations

from dataclasses import dataclass, fields
from enum import Enum


class MemoryKind(str, Enum):
    SESSION_CONTEXT = "session_context"
    PERSISTENT_USER_FACT = "persistent_user_fact"


@dataclass(frozen=True)
class MemoryEntrySnapshot:
    memory_id: str
    normalized_key: str
    display_key: str
    value: str
    kind: str
    created_at: str
    updated_at: str
    persisted: bool
    language_code: str
    metadata: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {field.name: getattr(self, field.name) for field in fields(self)}


@dataclass(frozen=True)
class MemoryOperationResult:
    ok: bool
    action: str
    memory_id: str | None
    key: str | None
    value: str | None
    changed: bool
    persisted: bool
    found: bool
    safe_message: str
    safe_error_code: str | None = None
    previous_value: str | None = None
    entries: tuple[MemoryEntrySnapshot, ...] = ()
    awaiting_confirmation: bool = False
    operation_id: str | None = None

    def to_dict(self) -> dict[str, object]:
        data = {field.name: getattr(self, field.name) for field in fields(self)}
        data["entries"] = tuple(entry.to_dict() for entry in self.entries)
        return data


@dataclass(frozen=True)
class ConversationTurnSnapshot:
    sequence: int
    user_summary: str
    assistant_summary: str
    intent_id: str | None
    topic_key: str | None
    read_only: bool
    side_effecting: bool
    outcome: str

    def to_dict(self) -> dict[str, object]:
        return {field.name: getattr(self, field.name) for field in fields(self)}


@dataclass(frozen=True)
class ConversationContextSnapshot:
    bounded_turn_count: int
    max_turns: int
    last_intent_id: str | None
    last_topic_key: str | None
    pending_reference: str | None
    turns: tuple[ConversationTurnSnapshot, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "bounded_turn_count": self.bounded_turn_count,
            "max_turns": self.max_turns,
            "last_intent_id": self.last_intent_id,
            "last_topic_key": self.last_topic_key,
            "pending_reference": self.pending_reference,
            "turns": tuple(turn.to_dict() for turn in self.turns),
        }
