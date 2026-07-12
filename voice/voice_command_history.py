"""In-memory session history for voice command recognition events."""

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class VoiceCommandHistoryEntry:
    id: int
    recognized_text: str | None
    corrected_text: str | None
    normalized_text: str | None
    canonical_command: str | None
    source: str
    status: str
    reason: str | None = None
    safety_notes: list[str] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class VoiceCommandSessionHistory:
    """Session-only voice command history with no persistence or audio storage."""

    def __init__(self, max_entries=20):
        if max_entries < 1:
            raise ValueError("max_entries must be at least 1")
        self.max_entries = max_entries
        self._entries = []
        self._next_id = 1

    def add_entry(
        self,
        recognized_text=None,
        corrected_text=None,
        normalized_text=None,
        canonical_command=None,
        source="one_shot_vosk",
        status="recognized",
        reason=None,
        safety_notes=None,
    ):
        entry = VoiceCommandHistoryEntry(
            id=self._next_id,
            recognized_text=self._clean_optional_text(recognized_text),
            corrected_text=self._clean_optional_text(corrected_text),
            normalized_text=self._clean_optional_text(normalized_text),
            canonical_command=self._clean_optional_text(canonical_command),
            source=str(source or "unknown"),
            status=str(status or "recognized"),
            reason=self._clean_optional_text(reason),
            safety_notes=list(safety_notes or []),
        )
        self._next_id += 1
        self._entries.append(entry)
        if len(self._entries) > self.max_entries:
            self._entries = self._entries[-self.max_entries :]
        return entry

    def last_entry(self):
        if not self._entries:
            return None
        return self._entries[-1]

    def list_recent(self, limit=5):
        if limit <= 0:
            return []
        return list(self._entries[-limit:])

    def clear(self):
        self._entries.clear()

    def count(self):
        return len(self._entries)

    @staticmethod
    def _clean_optional_text(value):
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None
