"""In-memory cognitive conversation session ownership.

TASK-113 deliberately keeps sessions in memory only. Restart-safe persistence
belongs to a later approved task.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from uuid import uuid4

from cognition.contracts import (
    ConversationRole,
    ConversationSessionSnapshot,
    ConversationSessionStatus,
    ConversationTurn,
    InvalidConversationTurnError,
    safe_cognitive_text,
)


class ConversationSessionError(Exception):
    """Base error for cognitive session lifecycle failures."""


class ConversationSessionNotFoundError(ConversationSessionError):
    """Raised when a requested conversation session does not exist."""


class ConversationSessionClosedError(ConversationSessionError):
    """Raised when a caller tries to append to a closed session."""


@dataclass
class _SessionRecord:
    session_id: str
    status: ConversationSessionStatus
    created_at: str
    updated_at: str
    turns: list[ConversationTurn] = field(default_factory=list)


class ConversationSessionService:
    """Owns in-memory cognitive session lifecycle and turn ordering."""

    def __init__(self):
        self._lock = RLock()
        self._sessions: dict[str, _SessionRecord] = {}

    def create_session(self) -> ConversationSessionSnapshot:
        with self._lock:
            now = _utc_now_iso()
            session_id = f"cog-session-{uuid4().hex}"
            self._sessions[session_id] = _SessionRecord(
                session_id=session_id,
                status=ConversationSessionStatus.ACTIVE,
                created_at=now,
                updated_at=now,
            )
            return self._snapshot_locked(session_id)

    def get_snapshot(self, session_id: str) -> ConversationSessionSnapshot:
        with self._lock:
            return self._snapshot_locked(session_id)

    def append_user_turn(self, session_id: str, text: str, source: str) -> ConversationTurn:
        return self._append_turn(session_id, ConversationRole.USER, text, source)

    def append_assistant_turn(self, session_id: str, text: str, source: str) -> ConversationTurn:
        return self._append_turn(session_id, ConversationRole.ASSISTANT, text, source)

    def close_session(self, session_id: str) -> ConversationSessionSnapshot:
        with self._lock:
            record = self._record_locked(session_id)
            now = _utc_now_iso()
            record.status = ConversationSessionStatus.CLOSED
            record.updated_at = now
            return self._snapshot_for_record(record)

    def turns_snapshot(self, session_id: str) -> tuple[ConversationTurn, ...]:
        with self._lock:
            return tuple(self._record_locked(session_id).turns)

    def _append_turn(
        self,
        session_id: str,
        role: ConversationRole,
        text: str,
        source: str,
    ) -> ConversationTurn:
        safe_text = safe_cognitive_text(str(text or "").strip())
        safe_source = safe_cognitive_text(str(source or "").strip())
        if not safe_text:
            raise InvalidConversationTurnError("text must not be empty")
        if not safe_source:
            raise InvalidConversationTurnError("source must not be empty")
        with self._lock:
            record = self._record_locked(session_id)
            if record.status is ConversationSessionStatus.CLOSED:
                raise ConversationSessionClosedError(f"conversation session is closed: {session_id}")
            now = _utc_now_iso()
            turn = ConversationTurn(
                turn_id=f"cog-turn-{uuid4().hex}",
                session_id=record.session_id,
                sequence=len(record.turns) + 1,
                role=role,
                text=safe_text,
                source=safe_source,
                created_at=now,
            )
            record.turns.append(turn)
            record.updated_at = now
            return turn

    def _record_locked(self, session_id: str) -> _SessionRecord:
        record = self._sessions.get(str(session_id or "").strip())
        if record is None:
            raise ConversationSessionNotFoundError(f"conversation session not found: {session_id}")
        return record

    def _snapshot_locked(self, session_id: str) -> ConversationSessionSnapshot:
        return self._snapshot_for_record(self._record_locked(session_id))

    @staticmethod
    def _snapshot_for_record(record: _SessionRecord) -> ConversationSessionSnapshot:
        last_turn_id = record.turns[-1].turn_id if record.turns else None
        return ConversationSessionSnapshot(
            session_id=record.session_id,
            status=record.status,
            created_at=record.created_at,
            updated_at=record.updated_at,
            turn_count=len(record.turns),
            last_turn_id=last_turn_id,
        )


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
