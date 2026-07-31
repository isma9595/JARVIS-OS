"""Safe local persistence boundary for cognitive conversation sessions.

Persistence stores versioned, redacted records. It does not own session
lifecycle, turn ordering, or authoritative in-memory state.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
import os
from pathlib import Path
import re
from typing import Protocol

from cognition.contracts import (
    ConversationRole,
    ConversationSessionStatus,
    ConversationTurn,
    safe_cognitive_text,
)


CONVERSATION_SESSION_SCHEMA_VERSION = 1
CONVERSATION_SESSION_STORAGE_LAYOUT_VERSION = 1
MAX_PERSISTED_TURN_SUMMARY_LENGTH = 160

_SOURCE_PATTERN = re.compile(r"[^a-z0-9_.-]+")


class ConversationPersistenceError(Exception):
    """Base error for cognitive conversation persistence failures."""


class ConversationPersistenceLoadError(ConversationPersistenceError):
    """Raised when persisted conversation records cannot be loaded safely."""


class ConversationPersistenceWriteError(ConversationPersistenceError):
    """Raised when a conversation record cannot be written durably."""


class ConversationPersistenceCorruptionError(ConversationPersistenceLoadError):
    """Raised when a persisted conversation record is malformed."""


class PersistedTurnContentClassification(Enum):
    BOUNDED_REDACTED_SUMMARY = "bounded_redacted_summary"
    REDACTED_SENSITIVE_CONTENT = "redacted_sensitive_content"


@dataclass(frozen=True)
class PersistedConversationTurnSummary:
    turn_id: str
    sequence: int
    role: ConversationRole
    source_classification: str
    created_at: str
    summary_text: str
    content_classification: PersistedTurnContentClassification
    redaction_reason: str | None = None

    @classmethod
    def from_turn(cls, turn: ConversationTurn) -> "PersistedConversationTurnSummary":
        summary_text, classification, reason = _persisted_turn_summary(turn.text)
        return cls(
            turn_id=_required_text(turn.turn_id, "turn_id"),
            sequence=_positive_int(turn.sequence, "sequence"),
            role=_role(turn.role),
            source_classification=_source_classification(turn.source),
            created_at=_required_text(turn.created_at, "created_at"),
            summary_text=summary_text,
            content_classification=classification,
            redaction_reason=reason,
        )

    @classmethod
    def from_dict(cls, data: object) -> "PersistedConversationTurnSummary":
        if not isinstance(data, dict):
            raise ConversationPersistenceCorruptionError("persisted turn must be an object")
        _reject_unexpected_keys(
            data,
            {
                "turn_id",
                "sequence",
                "role",
                "source_classification",
                "created_at",
                "summary_text",
                "content_classification",
                "redaction_reason",
            },
            "persisted turn",
        )
        return cls(
            turn_id=_required_text(data.get("turn_id"), "turn_id"),
            sequence=_positive_int(data.get("sequence"), "sequence"),
            role=_role(data.get("role")),
            source_classification=_source_classification(data.get("source_classification")),
            created_at=_required_text(data.get("created_at"), "created_at"),
            summary_text=_summary_text(data.get("summary_text")),
            content_classification=_content_classification(data.get("content_classification")),
            redaction_reason=_optional_text(data.get("redaction_reason")),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "turn_id": self.turn_id,
            "sequence": self.sequence,
            "role": self.role.value,
            "source_classification": self.source_classification,
            "created_at": self.created_at,
            "summary_text": self.summary_text,
            "content_classification": self.content_classification.value,
            "redaction_reason": self.redaction_reason,
        }


@dataclass(frozen=True)
class PersistedConversationSessionRecord:
    schema_version: int
    session_id: str
    status: ConversationSessionStatus
    created_at: str
    updated_at: str
    turn_count: int
    last_turn_id: str | None
    turns: tuple[PersistedConversationTurnSummary, ...]
    revision: int

    @classmethod
    def from_session(
        cls,
        *,
        session_id: str,
        status: ConversationSessionStatus,
        created_at: str,
        updated_at: str,
        turns: tuple[ConversationTurn, ...],
        previous_revision: int = 0,
    ) -> "PersistedConversationSessionRecord":
        persisted_turns = tuple(PersistedConversationTurnSummary.from_turn(turn) for turn in turns)
        return cls(
            schema_version=CONVERSATION_SESSION_SCHEMA_VERSION,
            session_id=_required_text(session_id, "session_id"),
            status=_status(status),
            created_at=_required_text(created_at, "created_at"),
            updated_at=_required_text(updated_at, "updated_at"),
            turn_count=len(persisted_turns),
            last_turn_id=persisted_turns[-1].turn_id if persisted_turns else None,
            turns=persisted_turns,
            revision=max(1, int(previous_revision) + 1),
        )

    @classmethod
    def from_dict(cls, data: object) -> "PersistedConversationSessionRecord":
        if not isinstance(data, dict):
            raise ConversationPersistenceCorruptionError("persisted session must be an object")
        _reject_unexpected_keys(
            data,
            {
                "schema_version",
                "session_id",
                "status",
                "created_at",
                "updated_at",
                "turn_count",
                "last_turn_id",
                "turns",
                "revision",
            },
            "persisted session",
        )
        schema_version = _positive_int(data.get("schema_version"), "schema_version")
        if schema_version != CONVERSATION_SESSION_SCHEMA_VERSION:
            raise ConversationPersistenceLoadError(
                f"unsupported conversation session schema version: {schema_version}"
            )
        turns = tuple(
            PersistedConversationTurnSummary.from_dict(item)
            for item in _required_list(data.get("turns"), "turns")
        )
        record = cls(
            schema_version=schema_version,
            session_id=_required_text(data.get("session_id"), "session_id"),
            status=_status(data.get("status")),
            created_at=_required_text(data.get("created_at"), "created_at"),
            updated_at=_required_text(data.get("updated_at"), "updated_at"),
            turn_count=_nonnegative_int(data.get("turn_count"), "turn_count"),
            last_turn_id=_optional_text(data.get("last_turn_id")),
            turns=turns,
            revision=_positive_int(data.get("revision"), "revision"),
        )
        _validate_record(record)
        return record

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "session_id": self.session_id,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "turn_count": self.turn_count,
            "last_turn_id": self.last_turn_id,
            "turns": [turn.to_dict() for turn in self.turns],
            "revision": self.revision,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


@dataclass(frozen=True)
class ConversationPersistenceLoadResult:
    records: tuple[PersistedConversationSessionRecord, ...] = ()
    corrupt_record_ids: tuple[str, ...] = ()
    unsupported_schema_record_ids: tuple[str, ...] = ()

    @property
    def loaded_count(self) -> int:
        return len(self.records)

    @property
    def rejected_count(self) -> int:
        return len(self.corrupt_record_ids) + len(self.unsupported_schema_record_ids)


class ConversationSessionRepository(Protocol):
    def load_records(self) -> ConversationPersistenceLoadResult:
        """Load recoverable records and observable rejection diagnostics."""

    def save_record(self, record: PersistedConversationSessionRecord) -> None:
        """Upsert one detached persisted session record."""

    def delete_record(self, session_id: str) -> None:
        """Delete one persisted record if lifecycle semantics require it."""

    def close(self) -> None:
        """Release repository resources if any."""


class LocalConversationSessionRepository:
    """One-file-per-session JSON repository with atomic replace writes."""

    def __init__(self, storage_dir: str | Path | None = None):
        self.storage_dir = Path(storage_dir) if storage_dir is not None else _default_storage_dir()

    def load_records(self) -> ConversationPersistenceLoadResult:
        if not self.storage_dir.exists():
            return ConversationPersistenceLoadResult()
        if not self.storage_dir.is_dir():
            raise ConversationPersistenceLoadError("conversation session storage is not a directory")

        records: list[PersistedConversationSessionRecord] = []
        corrupt_ids: list[str] = []
        unsupported_ids: list[str] = []
        for path in sorted(self.storage_dir.glob("*.json")):
            record_id = _safe_record_id(path)
            try:
                with path.open("r", encoding="utf-8") as handle:
                    payload = json.load(handle)
                record = PersistedConversationSessionRecord.from_dict(payload)
                if _record_filename(record.session_id) != path.name:
                    raise ConversationPersistenceCorruptionError(
                        "persisted session id does not match record filename"
                    )
                records.append(record)
            except ConversationPersistenceLoadError as exc:
                if "unsupported conversation session schema version" in str(exc):
                    unsupported_ids.append(record_id)
                else:
                    corrupt_ids.append(record_id)
            except Exception:
                corrupt_ids.append(record_id)
        return ConversationPersistenceLoadResult(
            records=tuple(records),
            corrupt_record_ids=tuple(corrupt_ids),
            unsupported_schema_record_ids=tuple(unsupported_ids),
        )

    def save_record(self, record: PersistedConversationSessionRecord) -> None:
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            target = self.storage_dir / _record_filename(record.session_id)
            temporary = target.with_name(target.name + ".tmp")
            with temporary.open("w", encoding="utf-8") as handle:
                handle.write(record.to_json())
            os.replace(temporary, target)
        except Exception as exc:
            raise ConversationPersistenceWriteError("conversation session record write failed") from exc

    def delete_record(self, session_id: str) -> None:
        try:
            path = self.storage_dir / _record_filename(_required_text(session_id, "session_id"))
            if path.exists():
                path.unlink()
        except Exception as exc:
            raise ConversationPersistenceWriteError("conversation session record delete failed") from exc

    def close(self) -> None:
        return None


def _persisted_turn_summary(
    text: object,
) -> tuple[str, PersistedTurnContentClassification, str | None]:
    normalized = " ".join(str(text or "").replace("\r", " ").replace("\n", " ").split())
    sanitized = safe_cognitive_text(normalized)
    if sanitized != normalized or "[REDACTED]" in sanitized:
        return (
            "[redacted sensitive content]",
            PersistedTurnContentClassification.REDACTED_SENSITIVE_CONTENT,
            "obvious_secret_pattern",
        )
    if len(sanitized) > MAX_PERSISTED_TURN_SUMMARY_LENGTH:
        sanitized = sanitized[: MAX_PERSISTED_TURN_SUMMARY_LENGTH - 3].rstrip() + "..."
    return (
        sanitized or "[empty content]",
        PersistedTurnContentClassification.BOUNDED_REDACTED_SUMMARY,
        "bounded_redacted_projection",
    )


def _default_storage_dir() -> Path:
    configured = os.environ.get("JARVIS_COGNITIVE_SESSION_DIR")
    if configured:
        return Path(configured)
    versioned_data_path = (
        Path("data")
        / f"v{CONVERSATION_SESSION_STORAGE_LAYOUT_VERSION}"
        / "cognition"
        / "sessions"
    )
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "JARVIS-OS" / versioned_data_path
    return Path.home() / ".jarvis-os" / versioned_data_path


def _record_filename(session_id: str) -> str:
    safe_session_id = _required_text(session_id, "session_id")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", safe_session_id):
        raise ConversationPersistenceCorruptionError("session_id contains unsupported characters")
    return f"{safe_session_id}.json"


def _safe_record_id(path: Path) -> str:
    return _SOURCE_PATTERN.sub("_", path.stem.lower()).strip("_") or "unknown"


def _source_classification(value: object) -> str:
    cleaned = safe_cognitive_text(str(value or "unknown").strip().lower())
    cleaned = _SOURCE_PATTERN.sub("_", cleaned).strip("._-")
    return (cleaned or "unknown")[:64]


def _required_text(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise ConversationPersistenceCorruptionError(f"{field_name} must be text")
    cleaned = safe_cognitive_text(value.strip())
    if not cleaned:
        raise ConversationPersistenceCorruptionError(f"{field_name} must not be empty")
    return cleaned


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    return _required_text(value, "optional_text")


def _required_list(value: object, field_name: str) -> list[object]:
    if not isinstance(value, list):
        raise ConversationPersistenceCorruptionError(f"{field_name} must be a list")
    return value


def _reject_unexpected_keys(data: dict[str, object], allowed: set[str], label: str) -> None:
    unexpected = set(data) - allowed
    if unexpected:
        raise ConversationPersistenceCorruptionError(f"{label} contains unsupported fields")


def _summary_text(value: object) -> str:
    summary = _required_text(value, "summary_text")
    if len(summary) > MAX_PERSISTED_TURN_SUMMARY_LENGTH:
        raise ConversationPersistenceCorruptionError("summary_text exceeds persisted bound")
    return summary


def _positive_int(value: object, field_name: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ConversationPersistenceCorruptionError(f"{field_name} must be an integer") from exc
    if parsed < 1:
        raise ConversationPersistenceCorruptionError(f"{field_name} must be positive")
    return parsed


def _nonnegative_int(value: object, field_name: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ConversationPersistenceCorruptionError(f"{field_name} must be an integer") from exc
    if parsed < 0:
        raise ConversationPersistenceCorruptionError(f"{field_name} must be nonnegative")
    return parsed


def _role(value: object) -> ConversationRole:
    try:
        return value if isinstance(value, ConversationRole) else ConversationRole(str(value))
    except ValueError as exc:
        raise ConversationPersistenceCorruptionError("role is unsupported") from exc


def _status(value: object) -> ConversationSessionStatus:
    try:
        return (
            value
            if isinstance(value, ConversationSessionStatus)
            else ConversationSessionStatus(str(value))
        )
    except ValueError as exc:
        raise ConversationPersistenceCorruptionError("status is unsupported") from exc


def _content_classification(value: object) -> PersistedTurnContentClassification:
    try:
        return (
            value
            if isinstance(value, PersistedTurnContentClassification)
            else PersistedTurnContentClassification(str(value))
        )
    except ValueError as exc:
        raise ConversationPersistenceCorruptionError("content_classification is unsupported") from exc


def _validate_record(record: PersistedConversationSessionRecord) -> None:
    if record.turn_count != len(record.turns):
        raise ConversationPersistenceCorruptionError("turn_count does not match persisted turns")
    expected_sequences = tuple(range(1, len(record.turns) + 1))
    observed_sequences = tuple(turn.sequence for turn in record.turns)
    if observed_sequences != expected_sequences:
        raise ConversationPersistenceCorruptionError("persisted turn sequences are not contiguous")
    expected_last_turn_id = record.turns[-1].turn_id if record.turns else None
    if record.last_turn_id != expected_last_turn_id:
        raise ConversationPersistenceCorruptionError("last_turn_id does not match persisted turns")
