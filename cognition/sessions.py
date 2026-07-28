"""Cognitive conversation session ownership.

ConversationSessionService owns lifecycle, ordering, and authoritative
in-memory state. Optional persistence stores detached records only.
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
from cognition.persistence import (
    ConversationPersistenceLoadError,
    ConversationPersistenceLoadResult,
    ConversationPersistenceWriteError,
    ConversationSessionRepository,
    PersistedConversationSessionRecord,
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

    def __init__(
        self,
        repository: ConversationSessionRepository | None = None,
        *,
        load_persisted: bool = True,
    ):
        self._lock = RLock()
        self._sessions: dict[str, _SessionRecord] = {}
        self._repository = repository
        self._revisions: dict[str, int] = {}
        self._persistence_load_result = ConversationPersistenceLoadResult()
        if self._repository is not None and load_persisted:
            self.load_persisted_sessions()

    @property
    def persistence_load_result(self) -> ConversationPersistenceLoadResult:
        return self._persistence_load_result

    def load_persisted_sessions(self) -> ConversationPersistenceLoadResult:
        if self._repository is None:
            self._persistence_load_result = ConversationPersistenceLoadResult()
            return self._persistence_load_result
        load_result = self._repository.load_records()
        recovered: dict[str, _SessionRecord] = {}
        revisions: dict[str, int] = {}
        for persisted in load_result.records:
            if persisted.session_id in recovered:
                raise ConversationPersistenceLoadError(
                    f"duplicate persisted conversation session: {persisted.session_id}"
                )
            recovered[persisted.session_id] = _record_from_persisted(persisted)
            revisions[persisted.session_id] = persisted.revision
        with self._lock:
            self._sessions = recovered
            self._revisions = revisions
            self._persistence_load_result = load_result
        return load_result

    def create_session(self) -> ConversationSessionSnapshot:
        with self._lock:
            now = _utc_now_iso()
            session_id = f"cog-session-{uuid4().hex}"
            record = _SessionRecord(
                session_id=session_id,
                status=ConversationSessionStatus.ACTIVE,
                created_at=now,
                updated_at=now,
            )
            self._persist_record_locked(record)
            self._sessions[session_id] = record
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
            candidate = _SessionRecord(
                session_id=record.session_id,
                status=ConversationSessionStatus.CLOSED,
                created_at=record.created_at,
                updated_at=_utc_now_iso(),
                turns=list(record.turns),
            )
            self._persist_record_locked(candidate)
            record.status = candidate.status
            record.updated_at = candidate.updated_at
            return self._snapshot_for_record(record)

    def turns_snapshot(self, session_id: str) -> tuple[ConversationTurn, ...]:
        with self._lock:
            return tuple(self._record_locked(session_id).turns)

    def _persist_record_locked(self, record: _SessionRecord) -> None:
        if self._repository is None:
            return
        previous_revision = self._revisions.get(record.session_id, 0)
        persisted = PersistedConversationSessionRecord.from_session(
            session_id=record.session_id,
            status=record.status,
            created_at=record.created_at,
            updated_at=record.updated_at,
            turns=tuple(record.turns),
            previous_revision=previous_revision,
        )
        try:
            self._repository.save_record(persisted)
        except ConversationPersistenceWriteError:
            raise
        except Exception as exc:
            raise ConversationPersistenceWriteError(
                "conversation session persistence failed"
            ) from exc
        self._revisions[record.session_id] = persisted.revision

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
            candidate = _SessionRecord(
                session_id=record.session_id,
                status=record.status,
                created_at=record.created_at,
                updated_at=now,
                turns=[*record.turns, turn],
            )
            self._persist_record_locked(candidate)
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


def _record_from_persisted(persisted: PersistedConversationSessionRecord) -> _SessionRecord:
    turns = [
        ConversationTurn(
            turn_id=turn.turn_id,
            session_id=persisted.session_id,
            sequence=turn.sequence,
            role=turn.role,
            text=turn.summary_text,
            source=turn.source_classification,
            created_at=turn.created_at,
        )
        for turn in persisted.turns
    ]
    return _SessionRecord(
        session_id=persisted.session_id,
        status=persisted.status,
        created_at=persisted.created_at,
        updated_at=persisted.updated_at,
        turns=turns,
    )
