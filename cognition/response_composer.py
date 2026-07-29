"""Non-executing response composition boundary for cognitive turns."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from cognition.contracts import (
    AssistantResponseType,
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
