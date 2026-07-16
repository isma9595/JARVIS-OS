from __future__ import annotations

import re
from collections import deque

from memory.contracts import ConversationContextSnapshot, ConversationTurnSnapshot


_SECRET_PATTERN = re.compile(
    r"(?i)(sk-[a-z0-9_-]{8,}|api[_ -]?key\s*[:=]?\s*\S+|token\s*[:=]?\s*\S+|password\s*[:=]?\s*\S+)"
)


class SessionConversationContext:
    DEFAULT_MAX_TURNS = 8
    DEFAULT_MAX_SUMMARY_LENGTH = 240

    def __init__(
        self,
        max_turns: int = DEFAULT_MAX_TURNS,
        max_summary_length: int = DEFAULT_MAX_SUMMARY_LENGTH,
    ):
        self.max_turns = max(1, int(max_turns))
        self.max_summary_length = max(40, int(max_summary_length))
        self._turns: deque[ConversationTurnSnapshot] = deque(maxlen=self.max_turns)
        self._next_sequence = 1

    def add_turn(
        self,
        *,
        user_text: str,
        assistant_text: str,
        intent_id: str | None,
        topic_key: str | None = None,
        read_only: bool = True,
        side_effecting: bool = False,
        outcome: str = "answered",
    ) -> ConversationTurnSnapshot:
        turn = ConversationTurnSnapshot(
            sequence=self._next_sequence,
            user_summary=self._safe_summary(user_text),
            assistant_summary=self._safe_summary(assistant_text),
            intent_id=self._safe_optional(intent_id),
            topic_key=self._safe_optional(topic_key),
            read_only=bool(read_only),
            side_effecting=bool(side_effecting),
            outcome=self._safe_summary(outcome, limit=80),
        )
        self._next_sequence += 1
        self._turns.append(turn)
        return turn

    def last_read_only_memory_turn(self) -> ConversationTurnSnapshot | None:
        for turn in reversed(self._turns):
            if turn.read_only and not turn.side_effecting and turn.intent_id == "memory.recall":
                return turn
        return None

    def snapshot(self) -> ConversationContextSnapshot:
        turns = tuple(self._turns)
        last = turns[-1] if turns else None
        pending_reference = None
        memory_turn = self.last_read_only_memory_turn()
        if memory_turn is not None:
            pending_reference = memory_turn.topic_key
        return ConversationContextSnapshot(
            bounded_turn_count=len(turns),
            max_turns=self.max_turns,
            last_intent_id=last.intent_id if last is not None else None,
            last_topic_key=last.topic_key if last is not None else None,
            pending_reference=pending_reference,
            turns=turns,
        )

    def clear(self) -> None:
        self._turns.clear()

    def _safe_summary(self, text: str, *, limit: int | None = None) -> str:
        summary = " ".join(str(text or "").replace("\r", " ").replace("\n", " ").split())
        summary = _SECRET_PATTERN.sub("[REDACTED]", summary)
        max_length = limit or self.max_summary_length
        if len(summary) > max_length:
            summary = summary[: max_length - 3].rstrip() + "..."
        return summary

    def _safe_optional(self, text: str | None) -> str | None:
        if text is None:
            return None
        value = self._safe_summary(text, limit=120)
        return value or None
