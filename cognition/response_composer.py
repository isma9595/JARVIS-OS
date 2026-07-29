"""Non-executing response composition boundary for cognitive turns."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from cognition.contracts import (
    AssistantResponseType,
    ClarificationStatus,
    ResponseCompositionInput,
    ResponseCompositionResult,
    safe_cognitive_text,
)


class ResponseComposer(Protocol):
    def compose(self, composition_input: ResponseCompositionInput) -> ResponseCompositionResult:
        """Compose one assistant response without executing or persisting anything."""


CompatibilityResponseDelegate = Callable[[ResponseCompositionInput], str]


@dataclass(frozen=True)
class CompatibilityResponseComposer:
    """Adapter around existing AppService-owned safe conversational behavior."""

    delegate: CompatibilityResponseDelegate
    composition_source: str = "compatibility_delegate"

    def compose(self, composition_input: ResponseCompositionInput) -> ResponseCompositionResult:
        clarification = composition_input.clarification_request
        if clarification is not None:
            if clarification.status is ClarificationStatus.NEEDED:
                return ResponseCompositionResult(
                    response_type=AssistantResponseType.MESSAGE,
                    text=safe_cognitive_text(clarification.safe_question),
                    context_turn_count_used=composition_input.context.included_turn_count,
                    composition_source=(
                        f"{self.composition_source}:clarification="
                        f"{clarification.status.value},reason={clarification.reason.value},"
                        f"options={len(clarification.options)},rule={clarification.rule_id}"
                    ),
                )
            if clarification.status is ClarificationStatus.UNAVAILABLE:
                return ResponseCompositionResult(
                    response_type=AssistantResponseType.MESSAGE,
                    text=_generic_unavailable_prompt(composition_input.current_user_turn.text),
                    context_turn_count_used=composition_input.context.included_turn_count,
                    composition_source=(
                        f"{self.composition_source}:clarification="
                        f"{clarification.status.value},reason={clarification.reason.value},"
                        f"options=0,rule={clarification.rule_id}"
                    ),
                )
        response_text = self.delegate(composition_input)
        composition_source = self.composition_source
        if composition_input.interpreted_intent is not None:
            composition_source = (
                f"{composition_source}:"
                f"{composition_input.interpreted_intent.category.value}"
            )
        if composition_input.reference_resolution is not None:
            references = composition_input.reference_resolution.references
            resolved_count = sum(
                1 for item in references if item.status.value == "resolved"
            )
            ambiguous_count = sum(
                1 for item in references if item.status.value == "ambiguous"
            )
            unresolved_count = sum(
                1 for item in references if item.status.value == "unresolved"
            )
            composition_source = (
                f"{composition_source}:refs={len(references)},"
                f"resolved={resolved_count},ambiguous={ambiguous_count},"
                f"unresolved={unresolved_count}"
            )
        return ResponseCompositionResult(
            response_type=AssistantResponseType.MESSAGE,
            text=safe_cognitive_text(response_text),
            context_turn_count_used=composition_input.context.included_turn_count,
            composition_source=composition_source,
        )


def _generic_unavailable_prompt(text: object) -> str:
    if any("\u0400" <= char <= "\u04ff" for char in str(text or "")):
        return "\u0423\u0442\u043e\u0447\u043d\u0438\u0442\u0435, \u043f\u043e\u0436\u0430\u043b\u0443\u0439\u0441\u0442\u0430, \u0447\u0442\u043e \u0438\u043c\u0435\u043d\u043d\u043e \u0432\u044b \u0438\u043c\u0435\u0435\u0442\u0435 \u0432 \u0432\u0438\u0434\u0443."
    return "Could you clarify what you mean?"
