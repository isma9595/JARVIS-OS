from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class AssistantResponseEntry:
    id: int
    text: str
    source_command: str | None
    source: str
    speakable: bool
    created_at: str


class AssistantResponseHistory:
    DEFAULT_MAX_ENTRIES = 20
    DEFAULT_MAX_TEXT_LENGTH = 1000

    def __init__(self, max_entries=DEFAULT_MAX_ENTRIES, max_text_length=DEFAULT_MAX_TEXT_LENGTH):
        self.max_entries = max(1, int(max_entries))
        self.max_text_length = max(1, int(max_text_length))
        self._entries = []
        self._next_id = 1

    def add_response(
        self,
        text,
        source_command=None,
        speakable=True,
        source="command_processor",
    ):
        normalized_text = self._normalize_text(text)
        if not normalized_text:
            return None

        entry = AssistantResponseEntry(
            id=self._next_id,
            text=normalized_text,
            source_command=source_command,
            source=source,
            speakable=bool(speakable),
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._next_id += 1
        self._entries.append(entry)
        if len(self._entries) > self.max_entries:
            self._entries = self._entries[-self.max_entries :]
        return entry

    def last_response(self):
        if not self._entries:
            return None
        return self._entries[-1]

    def last_speakable_response(self):
        for entry in reversed(self._entries):
            if entry.speakable:
                return entry
        return None

    def list_recent(self, limit=5):
        normalized_limit = max(0, int(limit))
        if normalized_limit == 0:
            return []
        return list(self._entries[-normalized_limit:])

    def clear(self):
        self._entries.clear()

    def count(self):
        return len(self._entries)

    def _normalize_text(self, text):
        normalized = str(text or "").strip()
        if not normalized:
            return ""
        if len(normalized) > self.max_text_length:
            return normalized[: self.max_text_length].rstrip()
        return normalized
