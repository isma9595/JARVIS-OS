"""Deterministic reference resolution over bounded conversation context."""

from dataclasses import dataclass
import re
from typing import Protocol

from cognition.contracts import (
    ConversationContextTurn,
    ConversationRole,
    DetectedReference,
    IntentCategory,
    IntentConfidence,
    ReferenceCandidate,
    ReferenceKind,
    ReferenceResolutionInput,
    ReferenceResolutionResult,
    ReferenceResolutionStatus,
    ResolvedReference,
    safe_cognitive_text,
)


RESOLVER_ID = "rule_based_reference_resolver"
RESOLVER_VERSION = "1"
MAX_REFERENCE_CANDIDATES = 3


class ReferenceResolutionError(RuntimeError):
    """Raised when reference resolution fails without exposing raw text."""


class InvalidReferenceResolutionInputError(ReferenceResolutionError):
    """Raised when a resolver receives malformed input."""


class ReferenceResolver(Protocol):
    def resolve(
        self,
        resolution_input: ReferenceResolutionInput,
    ) -> ReferenceResolutionResult:
        """Resolve simple conversational references without side effects."""


@dataclass(frozen=True)
class RuleBasedReferenceResolver:
    """Small deterministic resolver for simple conversational references."""

    resolver_id: str = RESOLVER_ID
    resolver_version: str = RESOLVER_VERSION

    def resolve(
        self,
        resolution_input: ReferenceResolutionInput,
    ) -> ReferenceResolutionResult:
        if not isinstance(resolution_input, ReferenceResolutionInput):
            raise InvalidReferenceResolutionInputError("reference resolution input is invalid")

        context_turn_count_used = resolution_input.context.included_turn_count
        safe_text = _normalized_safe_text(resolution_input.current_user_turn.text)
        if (
            not safe_text
            or _is_redacted_marker(safe_text)
            or resolution_input.interpreted_intent.category is IntentCategory.CANCELLATION
        ):
            return self._result((), context_turn_count_used)

        normalized = safe_text.casefold()
        prior_turns = _prior_turns(resolution_input)

        explicit_quote = _first_quoted_excerpt(safe_text)
        if explicit_quote is not None:
            return self._result(
                (
                    self._resolve_matching_candidates(
                        kind=ReferenceKind.EXPLICIT_QUOTE,
                        surface_text=explicit_quote,
                        rule_id="explicit_quote",
                        candidates=_matching_quote_candidates(prior_turns, explicit_quote),
                        context_turn_count_used=context_turn_count_used,
                    ),
                ),
                context_turn_count_used,
            )

        if _contains_phrase(normalized, _PREVIOUS_RESPONSE_PHRASES):
            return self._result(
                (
                    self._resolve_nearest_role(
                        kind=ReferenceKind.PREVIOUS_RESPONSE,
                        surface_text="previous response",
                        rule_id="previous_response",
                        role=ConversationRole.ASSISTANT,
                        prior_turns=prior_turns,
                        context_turn_count_used=context_turn_count_used,
                    ),
                ),
                context_turn_count_used,
            )

        if _contains_phrase(normalized, _PREVIOUS_REQUEST_PHRASES):
            return self._result(
                (
                    self._resolve_nearest_role(
                        kind=ReferenceKind.PREVIOUS_REQUEST,
                        surface_text="previous request",
                        rule_id="previous_request",
                        role=ConversationRole.USER,
                        prior_turns=prior_turns,
                        context_turn_count_used=context_turn_count_used,
                    ),
                ),
                context_turn_count_used,
            )

        if _contains_phrase(normalized, _PREVIOUS_MESSAGE_PHRASES):
            return self._result(
                (
                    self._resolve_previous_message(
                        safe_text,
                        prior_turns,
                        context_turn_count_used,
                    ),
                ),
                context_turn_count_used,
            )

        if _contains_phrase(normalized, _PREVIOUS_QUESTION_PHRASES):
            return self._result(
                (
                    self._resolve_matching_candidates(
                        kind=ReferenceKind.PREVIOUS_MESSAGE,
                        surface_text="previous question",
                        rule_id="previous_question",
                        candidates=_question_candidates(prior_turns)[:1],
                        context_turn_count_used=context_turn_count_used,
                    ),
                ),
                context_turn_count_used,
            )

        if _contains_phrase(normalized, _PREVIOUS_RESULT_PHRASES):
            return self._result(
                (
                    self._resolve_matching_candidates(
                        kind=ReferenceKind.PREVIOUS_RESULT,
                        surface_text="previous result",
                        rule_id="previous_result",
                        candidates=_result_candidates(prior_turns)[:1],
                        context_turn_count_used=context_turn_count_used,
                    ),
                ),
                context_turn_count_used,
            )

        neutral_surface = _neutral_reference_surface(normalized)
        if neutral_surface is not None:
            return self._result(
                (
                    self._resolve_neutral_reference(
                        neutral_surface,
                        prior_turns,
                        resolution_input.context.omitted_turn_count,
                        context_turn_count_used,
                    ),
                ),
                context_turn_count_used,
            )

        return self._result((), context_turn_count_used)

    def _result(
        self,
        references: tuple[ResolvedReference, ...],
        context_turn_count_used: int,
    ) -> ReferenceResolutionResult:
        return ReferenceResolutionResult(
            references=references,
            has_unresolved_references=any(
                item.status is ReferenceResolutionStatus.UNRESOLVED for item in references
            ),
            has_ambiguous_references=any(
                item.status is ReferenceResolutionStatus.AMBIGUOUS for item in references
            ),
            context_turn_count_used=context_turn_count_used,
            resolver_id=self.resolver_id,
            resolver_version=self.resolver_version,
        )

    def _resolve_nearest_role(
        self,
        *,
        kind: ReferenceKind,
        surface_text: str,
        rule_id: str,
        role: ConversationRole,
        prior_turns: tuple[ConversationContextTurn, ...],
        context_turn_count_used: int,
    ) -> ResolvedReference:
        candidates = tuple(candidate for candidate in _eligible_candidates(prior_turns) if candidate.role is role)
        return self._resolve_matching_candidates(
            kind=kind,
            surface_text=surface_text,
            rule_id=rule_id,
            candidates=candidates[:1],
            context_turn_count_used=context_turn_count_used,
        )

    def _resolve_previous_message(
        self,
        safe_text: str,
        prior_turns: tuple[ConversationContextTurn, ...],
        context_turn_count_used: int,
    ) -> ResolvedReference:
        candidates = _eligible_candidates(prior_turns)
        immediate = candidates[:1]
        return self._resolve_matching_candidates(
            kind=ReferenceKind.PREVIOUS_MESSAGE,
            surface_text=safe_text,
            rule_id="previous_message",
            candidates=immediate,
            context_turn_count_used=context_turn_count_used,
        )

    def _resolve_neutral_reference(
        self,
        surface_text: str,
        prior_turns: tuple[ConversationContextTurn, ...],
        omitted_turn_count: int,
        context_turn_count_used: int,
    ) -> ResolvedReference:
        candidates = _eligible_candidates(prior_turns)
        if omitted_turn_count > 0 and candidates:
            return self._reference(
                kind=ReferenceKind.PRONOUN if surface_text == "it" else ReferenceKind.DEMONSTRATIVE,
                surface_text=surface_text,
                rule_id="neutral_reference_context_truncated",
                status=ReferenceResolutionStatus.AMBIGUOUS,
                selected_candidate=None,
                candidates=candidates[:MAX_REFERENCE_CANDIDATES],
                confidence=IntentConfidence.LOW,
                context_turn_count_used=context_turn_count_used,
            )
        return self._resolve_matching_candidates(
            kind=ReferenceKind.PRONOUN if surface_text == "it" else ReferenceKind.DEMONSTRATIVE,
            surface_text=surface_text,
            rule_id="neutral_reference",
            candidates=candidates,
            context_turn_count_used=context_turn_count_used,
        )

    def _resolve_matching_candidates(
        self,
        *,
        kind: ReferenceKind,
        surface_text: str,
        rule_id: str,
        candidates: tuple[ReferenceCandidate, ...],
        context_turn_count_used: int,
    ) -> ResolvedReference:
        if len(candidates) == 1:
            return self._reference(
                kind=kind,
                surface_text=surface_text,
                rule_id=rule_id,
                status=ReferenceResolutionStatus.RESOLVED,
                selected_candidate=candidates[0],
                candidates=candidates,
                confidence=IntentConfidence.MEDIUM,
                context_turn_count_used=context_turn_count_used,
            )
        if len(candidates) > 1:
            return self._reference(
                kind=kind,
                surface_text=surface_text,
                rule_id=rule_id,
                status=ReferenceResolutionStatus.AMBIGUOUS,
                selected_candidate=None,
                candidates=candidates[:MAX_REFERENCE_CANDIDATES],
                confidence=IntentConfidence.LOW,
                context_turn_count_used=context_turn_count_used,
            )
        return self._reference(
            kind=kind,
            surface_text=surface_text,
            rule_id=rule_id,
            status=ReferenceResolutionStatus.UNRESOLVED,
            selected_candidate=None,
            candidates=(),
            confidence=IntentConfidence.LOW,
            context_turn_count_used=context_turn_count_used,
        )

    def _reference(
        self,
        *,
        kind: ReferenceKind,
        surface_text: str,
        rule_id: str,
        status: ReferenceResolutionStatus,
        selected_candidate: ReferenceCandidate | None,
        candidates: tuple[ReferenceCandidate, ...],
        confidence: IntentConfidence,
        context_turn_count_used: int,
    ) -> ResolvedReference:
        return ResolvedReference(
            detected_reference=DetectedReference(
                kind=kind,
                safe_surface_text=surface_text,
                rule_id=rule_id,
            ),
            status=status,
            selected_candidate=selected_candidate,
            candidates=candidates,
            confidence=confidence,
            context_turn_count_used=context_turn_count_used,
            resolver_id=self.resolver_id,
            resolver_version=self.resolver_version,
        )


def _prior_turns(
    resolution_input: ReferenceResolutionInput,
) -> tuple[ConversationContextTurn, ...]:
    current_sequence = resolution_input.current_user_turn.sequence
    return tuple(
        turn
        for turn in resolution_input.context.turns
        if turn.sequence < current_sequence
    )


def _eligible_candidates(
    prior_turns: tuple[ConversationContextTurn, ...],
) -> tuple[ReferenceCandidate, ...]:
    candidates: list[ReferenceCandidate] = []
    for recency_rank, turn in enumerate(reversed(prior_turns), start=1):
        if _is_redacted_marker(turn.safe_text):
            continue
        candidates.append(
            ReferenceCandidate(
                turn_id=turn.turn_id,
                turn_sequence=turn.sequence,
                role=turn.role,
                safe_excerpt=turn.safe_text,
                match_reason="bounded_context_turn",
                recency_rank=recency_rank,
                confidence=IntentConfidence.LOW,
            )
        )
    return tuple(candidates)


def _matching_quote_candidates(
    prior_turns: tuple[ConversationContextTurn, ...],
    quoted_text: str,
) -> tuple[ReferenceCandidate, ...]:
    normalized_quote = _normalized_safe_text(quoted_text).casefold()
    return tuple(
        candidate
        for candidate in _eligible_candidates(prior_turns)
        if normalized_quote
        and normalized_quote in _normalized_safe_text(candidate.safe_excerpt).casefold()
    )


def _question_candidates(
    prior_turns: tuple[ConversationContextTurn, ...],
) -> tuple[ReferenceCandidate, ...]:
    return tuple(
        candidate
        for candidate in _eligible_candidates(prior_turns)
        if "?" in candidate.safe_excerpt
    )


def _result_candidates(
    prior_turns: tuple[ConversationContextTurn, ...],
) -> tuple[ReferenceCandidate, ...]:
    return tuple(
        candidate
        for candidate in _eligible_candidates(prior_turns)
        if _contains_phrase(
            _normalized_safe_text(candidate.safe_excerpt).casefold(),
            _RESULT_MARKERS,
        )
    )


def _normalized_safe_text(text: object) -> str:
    sanitized = safe_cognitive_text(text)
    normalized = " ".join(sanitized.replace("\r", " ").replace("\n", " ").split())
    return normalized.strip()


def _is_redacted_marker(text: str) -> bool:
    return text.casefold() in {"[redacted]", "[redacted sensitive content]"}


def _first_quoted_excerpt(text: str) -> str | None:
    match = re.search(r'"([^"]{1,120})"', text)
    if match is None:
        match = re.search(r"'([^']{1,120})'", text)
    if match is None:
        return None
    return _normalized_safe_text(match.group(1)) or None


def _contains_phrase(text: str, phrases: tuple[str, ...]) -> bool:
    normalized_text = " ".join(re.sub(r"[^\w\s]+", " ", text).split())
    padded = f" {normalized_text} "
    return any(f" {phrase} " in padded or normalized_text == phrase for phrase in phrases)


def _neutral_reference_surface(text: str) -> str | None:
    for phrase in _NEUTRAL_REFERENCE_PHRASES:
        if _contains_phrase(text, (phrase,)):
            return phrase
    return None


_PREVIOUS_RESPONSE_PHRASES = (
    "your previous response",
    "your last response",
    "previous response",
    "last response",
    "\u0442\u0432\u043e\u0439 \u043f\u0440\u0435\u0434\u044b\u0434\u0443\u0449\u0438\u0439 \u043e\u0442\u0432\u0435\u0442",
    "\u043f\u0440\u0435\u0434\u044b\u0434\u0443\u0449\u0438\u0439 \u043e\u0442\u0432\u0435\u0442",
)

_PREVIOUS_REQUEST_PHRASES = (
    "my previous request",
    "my last request",
    "previous request",
    "last request",
    "\u043c\u043e\u0439 \u043f\u0440\u0435\u0434\u044b\u0434\u0443\u0449\u0438\u0439 \u0437\u0430\u043f\u0440\u043e\u0441",
    "\u043f\u0440\u0435\u0434\u044b\u0434\u0443\u0449\u0438\u0439 \u0437\u0430\u043f\u0440\u043e\u0441",
)

_PREVIOUS_MESSAGE_PHRASES = (
    "previous message",
    "last message",
    "the previous message",
    "the last message",
    "\u043f\u0440\u0435\u0434\u044b\u0434\u0443\u0449\u0435\u0435 \u0441\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u0435",
    "\u043f\u043e\u0441\u043b\u0435\u0434\u043d\u0435\u0435 \u0441\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u0435",
)

_PREVIOUS_QUESTION_PHRASES = (
    "previous question",
    "last question",
    "the previous question",
    "the last question",
    "\u043f\u0440\u0435\u0434\u044b\u0434\u0443\u0449\u0438\u0439 \u0432\u043e\u043f\u0440\u043e\u0441",
    "\u043f\u043e\u0441\u043b\u0435\u0434\u043d\u0438\u0439 \u0432\u043e\u043f\u0440\u043e\u0441",
)

_PREVIOUS_RESULT_PHRASES = (
    "previous result",
    "last result",
    "the previous result",
    "the last result",
    "\u043f\u0440\u0435\u0434\u044b\u0434\u0443\u0449\u0438\u0439 \u0440\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442",
    "\u043f\u043e\u0441\u043b\u0435\u0434\u043d\u0438\u0439 \u0440\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442",
)

_RESULT_MARKERS = (
    "result",
    "completed",
    "finished",
    "\u0440\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442",
    "\u0433\u043e\u0442\u043e\u0432\u043e",
)

_NEUTRAL_REFERENCE_PHRASES = (
    "this one",
    "that one",
    "this",
    "that",
    "it",
    "\u044d\u0442\u043e \u0441\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u0435",
    "\u044d\u0442\u043e\u0442",
    "\u044d\u0442\u0430",
    "\u044d\u0442\u043e",
    "\u0442\u043e\u0442",
    "\u0442\u0430",
    "\u0442\u043e",
    "\u043e\u043d\u043e",
    "\u043e\u043d",
    "\u043e\u043d\u0430",
)
