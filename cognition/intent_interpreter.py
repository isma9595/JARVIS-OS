"""Deterministic provider-neutral intent interpretation boundary."""

from dataclasses import dataclass
from typing import Protocol

from cognition.contracts import (
    ConversationRole,
    IntentCategory,
    IntentConfidence,
    IntentEvidence,
    IntentInterpretationInput,
    InterpretedIntent,
    InvalidConversationTurnError,
    safe_cognitive_text,
)


INTERPRETER_ID = "rule_based_intent_interpreter"
INTERPRETER_VERSION = "1"


class IntentInterpretationError(RuntimeError):
    """Raised when intent interpretation fails without exposing raw text."""


class InvalidIntentInputError(IntentInterpretationError):
    """Raised when an interpreter receives malformed input."""


class IntentInterpreter(Protocol):
    def interpret(self, interpretation_input: IntentInterpretationInput) -> InterpretedIntent:
        """Interpret one safe user turn with bounded context."""


@dataclass(frozen=True)
class RuleBasedIntentInterpreter:
    """Small deterministic adapter that describes apparent user intent."""

    interpreter_id: str = INTERPRETER_ID
    interpreter_version: str = INTERPRETER_VERSION

    def interpret(self, interpretation_input: IntentInterpretationInput) -> InterpretedIntent:
        if not isinstance(interpretation_input, IntentInterpretationInput):
            raise InvalidIntentInputError("intent interpretation input is invalid")

        safe_user_text = _normalized_safe_text(interpretation_input.current_user_turn.text)
        context_turn_count_used = interpretation_input.context.included_turn_count
        clarification_turn = _latest_prior_assistant_question(interpretation_input)

        if not safe_user_text or _is_redacted_marker(safe_user_text):
            return self._intent(
                IntentCategory.UNKNOWN,
                IntentConfidence.LOW,
                "[empty content]",
                "empty_or_unusable_text",
                "empty or unusable safe text",
                context_turn_count_used,
            )

        normalized = safe_user_text.casefold()
        if normalized in _CANCELLATION_PHRASES:
            return self._intent(
                IntentCategory.CANCELLATION,
                IntentConfidence.HIGH,
                safe_user_text,
                "explicit_cancellation",
                safe_user_text,
                context_turn_count_used,
            )

        if clarification_turn is not None and _looks_like_short_reply(normalized):
            return self._intent(
                IntentCategory.CLARIFICATION_RESPONSE,
                IntentConfidence.MEDIUM,
                safe_user_text,
                "prior_assistant_question",
                clarification_turn.safe_text,
                context_turn_count_used,
                may_require_clarification=False,
            )

        if normalized in _CONFIRMATION_PHRASES:
            return self._intent(
                IntentCategory.CONFIRMATION,
                IntentConfidence.HIGH,
                safe_user_text,
                "explicit_confirmation",
                safe_user_text,
                context_turn_count_used,
            )

        if normalized in _REJECTION_PHRASES:
            return self._intent(
                IntentCategory.REJECTION,
                IntentConfidence.HIGH,
                safe_user_text,
                "explicit_rejection",
                safe_user_text,
                context_turn_count_used,
            )

        if _looks_like_question(normalized, safe_user_text):
            return self._intent(
                IntentCategory.QUESTION,
                IntentConfidence.MEDIUM,
                safe_user_text,
                "direct_question",
                safe_user_text,
                context_turn_count_used,
                may_require_clarification=False,
            )

        if _starts_with_phrase(normalized, _INFORMATION_REQUEST_PREFIXES):
            return self._intent(
                IntentCategory.INFORMATION_REQUEST,
                IntentConfidence.MEDIUM,
                safe_user_text,
                "information_request_prefix",
                safe_user_text,
                context_turn_count_used,
                may_require_clarification=False,
            )

        if _starts_with_phrase(normalized, _ACTION_REQUEST_PREFIXES):
            return self._intent(
                IntentCategory.ACTION_REQUEST,
                IntentConfidence.MEDIUM,
                safe_user_text,
                "action_request_prefix",
                safe_user_text,
                context_turn_count_used,
                may_require_clarification=True,
                is_actionable_request=True,
            )

        return self._intent(
            IntentCategory.CONVERSATION,
            IntentConfidence.LOW,
            safe_user_text,
            "conversation_fallback",
            safe_user_text,
            context_turn_count_used,
        )

    def _intent(
        self,
        category: IntentCategory,
        confidence: IntentConfidence,
        safe_user_text: str,
        rule_id: str,
        evidence_excerpt: str,
        context_turn_count_used: int,
        *,
        may_require_clarification: bool = False,
        is_actionable_request: bool = False,
    ) -> InterpretedIntent:
        try:
            evidence = (
                IntentEvidence(
                    evidence_type="rule",
                    safe_excerpt=evidence_excerpt,
                    rule_id=rule_id,
                ),
            )
            return InterpretedIntent(
                category=category,
                confidence=confidence,
                safe_user_text=safe_user_text,
                evidence=evidence,
                requires_reference_resolution=False,
                may_require_clarification=may_require_clarification,
                is_actionable_request=is_actionable_request,
                interpreter_id=self.interpreter_id,
                interpreter_version=self.interpreter_version,
                context_turn_count_used=context_turn_count_used,
            )
        except InvalidConversationTurnError as exc:
            raise InvalidIntentInputError("intent interpretation output is invalid") from exc


def _normalized_safe_text(text: object) -> str:
    sanitized = safe_cognitive_text(text)
    normalized = " ".join(sanitized.replace("\r", " ").replace("\n", " ").split())
    return normalized.strip()


def _is_redacted_marker(text: str) -> bool:
    return text.casefold() in {"[redacted]", "[redacted sensitive content]"}


def _latest_prior_assistant_question(interpretation_input: IntentInterpretationInput):
    current_sequence = interpretation_input.current_user_turn.sequence
    prior_turns = (
        turn
        for turn in interpretation_input.context.turns
        if turn.sequence < current_sequence and turn.role is ConversationRole.ASSISTANT
    )
    latest = None
    for turn in prior_turns:
        latest = turn
    if latest is None:
        return None
    normalized = latest.safe_text.casefold()
    if "?" in latest.safe_text or _starts_with_phrase(normalized, _ASSISTANT_CLARIFICATION_PREFIXES):
        return latest
    return None


def _looks_like_short_reply(normalized: str) -> bool:
    return normalized in _SHORT_REPLY_PHRASES or len(normalized) <= 40


def _looks_like_question(normalized: str, original: str) -> bool:
    return "?" in original or _starts_with_phrase(normalized, _QUESTION_PREFIXES)


def _starts_with_phrase(text: str, phrases: tuple[str, ...]) -> bool:
    return any(text == phrase or text.startswith(f"{phrase} ") for phrase in phrases)


_CANCELLATION_PHRASES = (
    "abort",
    "cancel",
    "never mind",
    "stop",
    "\u043e\u0442\u043c\u0435\u043d\u0430",
    "\u0441\u0442\u043e\u043f",
)

_CONFIRMATION_PHRASES = (
    "approve",
    "confirm",
    "i approve",
    "i confirm",
    "ok",
    "okay",
    "yes",
    "yep",
    "\u0434\u0430",
    "\u043f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0430\u044e",
)

_REJECTION_PHRASES = (
    "decline",
    "i decline",
    "i reject",
    "no",
    "nope",
    "reject",
    "\u043d\u0435\u0442",
    "\u043e\u0442\u043a\u043b\u043e\u043d\u044f\u044e",
)

_SHORT_REPLY_PHRASES = _CONFIRMATION_PHRASES + _REJECTION_PHRASES

_QUESTION_PREFIXES = (
    "can",
    "could",
    "how",
    "what",
    "when",
    "where",
    "who",
    "why",
    "\u0433\u0434\u0435",
    "\u043a\u0430\u043a",
    "\u043a\u043e\u0433\u0434\u0430",
    "\u043a\u0442\u043e",
    "\u043f\u043e\u0447\u0435\u043c\u0443",
    "\u0447\u0442\u043e",
)

_INFORMATION_REQUEST_PREFIXES = (
    "explain",
    "show me information",
    "tell me",
    "\u043e\u0431\u044a\u044f\u0441\u043d\u0438",
    "\u0440\u0430\u0441\u0441\u043a\u0430\u0436\u0438",
)

_ACTION_REQUEST_PREFIXES = (
    "create",
    "delete",
    "open",
    "remove",
    "run",
    "send",
    "start",
    "turn off",
    "turn on",
    "write",
    "\u0437\u0430\u043f\u0443\u0441\u0442\u0438",
    "\u043e\u0442\u043a\u0440\u043e\u0439",
    "\u0441\u043e\u0437\u0434\u0430\u0439",
    "\u0443\u0434\u0430\u043b\u0438",
)

_ASSISTANT_CLARIFICATION_PREFIXES = (
    "can you clarify",
    "could you clarify",
    "which",
    "what do you mean",
    "\u043c\u043e\u0436\u0435\u0442\u0435 \u0443\u0442\u043e\u0447\u043d\u0438\u0442\u044c",
    "\u0443\u0442\u043e\u0447\u043d\u0438\u0442\u0435",
)
