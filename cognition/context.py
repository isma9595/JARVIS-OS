"""Bounded conversation context projection for cognitive sessions.

The projector is stateless. It consumes detached session snapshots and turns
from ConversationSessionService and produces a bounded safe context DTO.
"""

from dataclasses import dataclass

from cognition.contracts import (
    ConversationContextContentClassification,
    ConversationContextSnapshot,
    ConversationContextTurn,
    ConversationSessionSnapshot,
    ConversationTurn,
    InvalidConversationTurnError,
    safe_cognitive_text,
)
from cognition.sessions import _utc_now_iso


DEFAULT_CONTEXT_MAX_TURNS = 12
DEFAULT_CONTEXT_MAX_TURN_CHARS = 160
DEFAULT_CONTEXT_MAX_TOTAL_CHARS = 800


@dataclass(frozen=True)
class ConversationContextProjector:
    """Projects recent session turns into a provider-neutral bounded context."""

    max_turns: int = DEFAULT_CONTEXT_MAX_TURNS
    max_turn_chars: int = DEFAULT_CONTEXT_MAX_TURN_CHARS
    max_total_chars: int = DEFAULT_CONTEXT_MAX_TOTAL_CHARS

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "max_turns",
            _positive_bound(self.max_turns, "max_turns"),
        )
        object.__setattr__(
            self,
            "max_turn_chars",
            _positive_bound(self.max_turn_chars, "max_turn_chars"),
        )
        object.__setattr__(
            self,
            "max_total_chars",
            _positive_bound(self.max_total_chars, "max_total_chars"),
        )

    def project(
        self,
        session: ConversationSessionSnapshot,
        turns: tuple[ConversationTurn, ...],
    ) -> ConversationContextSnapshot:
        detached_turns = tuple(turns)
        total_turn_count = len(detached_turns)
        if total_turn_count == 0:
            return ConversationContextSnapshot(
                session_id=session.session_id,
                session_status=session.status,
                projected_at=_utc_now_iso(),
                turns=(),
                total_turn_count=0,
                included_turn_count=0,
                omitted_turn_count=0,
            )

        ordered_turns = tuple(sorted(detached_turns, key=lambda turn: turn.sequence))
        if tuple(turn.sequence for turn in ordered_turns) != tuple(
            turn.sequence for turn in detached_turns
        ):
            raise InvalidConversationTurnError("source turns must be chronological")

        candidate_turns = ordered_turns[-self.max_turns :]
        selected: list[ConversationContextTurn] = []
        used_chars = 0
        total_limited = False
        for turn in reversed(candidate_turns):
            projected = self._project_turn(turn, self.max_turn_chars)
            remaining = self.max_total_chars - used_chars
            if remaining <= 0:
                total_limited = True
                break
            if len(projected.safe_text) > remaining:
                projected = self._project_turn(turn, remaining)
                total_limited = True
            selected.append(projected)
            used_chars += len(projected.safe_text)

        included = tuple(reversed(selected))
        omitted_turn_count = total_turn_count - len(included)
        truncation_reason = _truncation_reason(
            turn_limited=total_turn_count > self.max_turns,
            total_limited=total_limited or len(candidate_turns) > len(included),
            omitted_turn_count=omitted_turn_count,
        )
        sequences = tuple(turn.sequence for turn in included)
        return ConversationContextSnapshot(
            session_id=session.session_id,
            session_status=session.status,
            projected_at=_utc_now_iso(),
            turns=included,
            total_turn_count=total_turn_count,
            included_turn_count=len(included),
            omitted_turn_count=omitted_turn_count,
            first_included_sequence=sequences[0] if sequences else None,
            last_included_sequence=sequences[-1] if sequences else None,
            truncation_reason=truncation_reason,
        )

    @staticmethod
    def _project_turn(turn: ConversationTurn, max_chars: int) -> ConversationContextTurn:
        normalized = " ".join(str(turn.text or "").replace("\r", " ").replace("\n", " ").split())
        sanitized = safe_cognitive_text(normalized)
        if sanitized != normalized or "[REDACTED]" in sanitized:
            safe_text = "[redacted sensitive content]"
            classification = ConversationContextContentClassification.REDACTED_SENSITIVE_CONTENT
            reason = "obvious_secret_pattern"
        else:
            safe_text = sanitized or "[empty content]"
            classification = ConversationContextContentClassification.BOUNDED_SAFE_TEXT
            reason = "bounded_projection"
        if len(safe_text) > max_chars:
            safe_text = _truncate_text(safe_text, max_chars)
        return ConversationContextTurn(
            turn_id=turn.turn_id,
            sequence=turn.sequence,
            role=turn.role,
            source=turn.source,
            safe_text=safe_text,
            created_at=turn.created_at,
            content_classification=classification,
            redaction_reason=reason,
        )


def _truncate_text(text: str, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    if len(text) <= max_chars:
        return text
    if max_chars <= 3:
        return "." * max_chars
    return text[: max_chars - 3].rstrip() + "..."


def _positive_bound(value: object, field_name: str) -> int:
    if type(value) is not int:
        raise InvalidConversationTurnError(f"{field_name} must be an integer")
    if value < 1:
        raise InvalidConversationTurnError(f"{field_name} must be positive")
    return value


def _truncation_reason(
    *,
    turn_limited: bool,
    total_limited: bool,
    omitted_turn_count: int,
) -> str | None:
    if omitted_turn_count <= 0 and not total_limited:
        return None
    if turn_limited and total_limited:
        return "turn_and_total_character_limit"
    if total_limited:
        return "total_character_limit"
    if turn_limited:
        return "turn_limit"
    return "context_limit"
