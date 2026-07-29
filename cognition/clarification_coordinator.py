"""Stateless deterministic clarification coordination.

Rule precedence:
1. Empty, unusable, redacted, or explicit cancellation returns not-needed.
2. Ambiguous references with two safe distinguishable options ask one choice question.
3. Ambiguous references without two distinguishable options are unavailable.
4. Unresolved references in action or information requests ask one referent question.
5. Unresolved references in ordinary conversation are not-needed.
6. Confirmation or rejection without a visible prior assistant question asks one target question.
7. Clarification responses without a visible prior assistant question are unavailable.
8. Otherwise clarification is not needed.
"""

from dataclasses import dataclass
import re
from typing import Protocol

from cognition.contracts import (
    ClarificationCoordinationInput,
    ClarificationOption,
    ClarificationReason,
    ClarificationRequest,
    ClarificationStatus,
    ConversationRole,
    IntentCategory,
    MAX_CLARIFICATION_OPTIONS,
    ReferenceCandidate,
    ReferenceResolutionStatus,
    ResolvedReference,
    safe_cognitive_text,
)


COORDINATOR_ID = "rule_based_clarification_coordinator"
COORDINATOR_VERSION = "1"


class ClarificationCoordinationError(RuntimeError):
    """Raised when clarification coordination fails without exposing raw text."""


class InvalidClarificationInputError(ClarificationCoordinationError):
    """Raised when the coordinator receives malformed input."""


class ClarificationCoordinator(Protocol):
    def coordinate(
        self,
        coordination_input: ClarificationCoordinationInput,
    ) -> ClarificationRequest:
        """Coordinate at most one safe clarification request without side effects."""


@dataclass(frozen=True)
class RuleBasedClarificationCoordinator:
    """Small turn-local coordinator over bounded context, intent, and references."""

    coordinator_id: str = COORDINATOR_ID
    coordinator_version: str = COORDINATOR_VERSION

    def coordinate(
        self,
        coordination_input: ClarificationCoordinationInput,
    ) -> ClarificationRequest:
        if not isinstance(coordination_input, ClarificationCoordinationInput):
            raise InvalidClarificationInputError("clarification input is invalid")

        intent = coordination_input.interpreted_intent
        references = coordination_input.reference_resolution.references
        context_count = coordination_input.context.included_turn_count
        text = _normalized_safe_text(coordination_input.current_user_turn.text)

        if (
            not text
            or _is_redacted_marker(text)
            or intent.category is IntentCategory.CANCELLATION
        ):
            return self._not_needed(context_count, "not_needed_empty_or_cancelled")

        ambiguous = tuple(
            item
            for item in references
            if item.status is ReferenceResolutionStatus.AMBIGUOUS
        )
        if ambiguous:
            return self._ambiguous_reference(
                ambiguous[0],
                related_reference_count=len(ambiguous),
                context_turn_count_used=context_count,
                russian=_looks_russian(text),
            )

        unresolved = tuple(
            item
            for item in references
            if item.status is ReferenceResolutionStatus.UNRESOLVED
        )
        if unresolved and _intent_allows_unresolved_question(intent.category):
            return self._needed(
                ClarificationReason.UNRESOLVED_REFERENCE,
                _referent_question(unresolved[0], text),
                (),
                len(unresolved),
                context_count,
                "needed_unresolved_actionable_reference",
            )
        if unresolved:
            return self._not_needed(
                context_count,
                "not_needed_unresolved_ordinary_conversation",
            )

        if intent.category is IntentCategory.CONFIRMATION:
            if _latest_prior_assistant_question(coordination_input):
                return self._not_needed(context_count, "not_needed_confirmation_has_target")
            return self._needed(
                ClarificationReason.UNCLEAR_CONFIRMATION,
                _question_text(text, "What are you confirming?", "Что именно вы подтверждаете?"),
                (),
                0,
                context_count,
                "needed_confirmation_without_target",
            )

        if intent.category is IntentCategory.REJECTION:
            if _latest_prior_assistant_question(coordination_input):
                return self._not_needed(context_count, "not_needed_rejection_has_target")
            return self._needed(
                ClarificationReason.UNCLEAR_REJECTION,
                _question_text(text, "What are you rejecting?", "Что именно вы отклоняете?"),
                (),
                0,
                context_count,
                "needed_rejection_without_target",
            )

        if intent.category is IntentCategory.CLARIFICATION_RESPONSE:
            if _latest_prior_assistant_question(coordination_input):
                return self._not_needed(context_count, "not_needed_clarification_response_has_question")
            return self._unavailable(
                ClarificationReason.INSUFFICIENT_CONTEXT,
                0,
                context_count,
                "unavailable_clarification_response_without_question",
            )

        return self._not_needed(context_count, "not_needed_no_deterministic_ambiguity")

    def _ambiguous_reference(
        self,
        reference: ResolvedReference,
        *,
        related_reference_count: int,
        context_turn_count_used: int,
        russian: bool,
    ) -> ClarificationRequest:
        options = _options_from_candidates(reference.candidates)
        if len(options) < 2:
            return self._unavailable(
                ClarificationReason.UNSUPPORTED_AMBIGUITY,
                related_reference_count,
                context_turn_count_used,
                "unavailable_ambiguous_reference_indistinguishable_options",
            )
        return self._needed(
            ClarificationReason.AMBIGUOUS_REFERENCE,
            "Что именно вы имеете в виду?" if russian else "Which one did you mean?",
            options,
            related_reference_count,
            context_turn_count_used,
            "needed_ambiguous_reference_options",
        )

    def _needed(
        self,
        reason: ClarificationReason,
        safe_question: str,
        options: tuple[ClarificationOption, ...],
        related_reference_count: int,
        context_turn_count_used: int,
        rule_id: str,
    ) -> ClarificationRequest:
        return ClarificationRequest(
            status=ClarificationStatus.NEEDED,
            reason=reason,
            safe_question=safe_question,
            options=options,
            related_reference_count=related_reference_count,
            context_turn_count_used=context_turn_count_used,
            coordinator_id=self.coordinator_id,
            coordinator_version=self.coordinator_version,
            rule_id=rule_id,
        )

    def _unavailable(
        self,
        reason: ClarificationReason,
        related_reference_count: int,
        context_turn_count_used: int,
        rule_id: str,
    ) -> ClarificationRequest:
        return ClarificationRequest(
            status=ClarificationStatus.UNAVAILABLE,
            reason=reason,
            safe_question=None,
            options=(),
            related_reference_count=related_reference_count,
            context_turn_count_used=context_turn_count_used,
            coordinator_id=self.coordinator_id,
            coordinator_version=self.coordinator_version,
            rule_id=rule_id,
        )

    def _not_needed(
        self,
        context_turn_count_used: int,
        rule_id: str,
    ) -> ClarificationRequest:
        return ClarificationRequest(
            status=ClarificationStatus.NOT_NEEDED,
            reason=ClarificationReason.NONE,
            safe_question=None,
            options=(),
            related_reference_count=0,
            context_turn_count_used=context_turn_count_used,
            coordinator_id=self.coordinator_id,
            coordinator_version=self.coordinator_version,
            rule_id=rule_id,
        )


def _options_from_candidates(
    candidates: tuple[ReferenceCandidate, ...],
) -> tuple[ClarificationOption, ...]:
    options: list[ClarificationOption] = []
    seen: set[tuple[str, str]] = set()
    for candidate in candidates:
        excerpt = _normalized_safe_text(candidate.safe_excerpt)
        if not excerpt or _is_redacted_marker(excerpt):
            continue
        label = _candidate_label(candidate)
        identity = (label.casefold(), excerpt.casefold())
        if identity in seen:
            continue
        seen.add(identity)
        options.append(
            ClarificationOption(
                safe_label=label,
                candidate_turn_sequence=candidate.turn_sequence,
                candidate_id=None,
                safe_excerpt=excerpt,
                source_reason=candidate.match_reason,
                ordinal=len(options) + 1,
            )
        )
        if len(options) >= MAX_CLARIFICATION_OPTIONS:
            break
    return tuple(options)


def _candidate_label(candidate: ReferenceCandidate) -> str:
    if candidate.role is ConversationRole.ASSISTANT:
        return "Previous assistant response"
    if candidate.role is ConversationRole.USER:
        return "Previous user request"
    return "Previous message"


def _intent_allows_unresolved_question(category: IntentCategory) -> bool:
    return category in {
        IntentCategory.ACTION_REQUEST,
        IntentCategory.INFORMATION_REQUEST,
    }


def _referent_question(reference: ResolvedReference, current_text: str) -> str:
    surface = reference.detected_reference.safe_surface_text
    normalized_surface = surface.casefold()
    if _looks_russian(current_text) or _looks_russian(surface):
        if normalized_surface in {"это", "этот", "эта", "то", "тот", "та", "оно", "он", "она"}:
            return f"К чему относится «{surface}»?"
        return "На какое предыдущее сообщение вы ссылаетесь?"
    if normalized_surface in {"it", "this", "that", "this one", "that one"}:
        return f"What does '{surface}' refer to?"
    return "Which previous message are you referring to?"


def _latest_prior_assistant_question(
    coordination_input: ClarificationCoordinationInput,
) -> bool:
    current_sequence = coordination_input.current_user_turn.sequence
    latest_text = None
    for turn in coordination_input.context.turns:
        if turn.sequence < current_sequence and turn.role is ConversationRole.ASSISTANT:
            latest_text = turn.safe_text
    if latest_text is None:
        return False
    normalized = latest_text.casefold()
    return (
        "?" in latest_text
        or normalized.startswith("could you clarify")
        or normalized.startswith("can you clarify")
        or normalized.startswith("which")
        or normalized.startswith("what are you")
        or normalized.startswith("уточните")
        or normalized.startswith("что именно")
        or normalized.startswith("к чему")
    )


def _question_text(current_text: str, english: str, russian: str) -> str:
    return russian if _looks_russian(current_text) else english


def _looks_russian(text: str) -> bool:
    return bool(re.search(r"[А-Яа-яЁё]", text))


def _normalized_safe_text(text: object) -> str:
    sanitized = safe_cognitive_text(text)
    normalized = " ".join(sanitized.replace("\r", " ").replace("\n", " ").split())
    return normalized.strip()


def _is_redacted_marker(text: str) -> bool:
    return text.casefold() in {"[redacted]", "[redacted sensitive content]"}
