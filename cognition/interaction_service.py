"""Turn-local cognitive interaction orchestration."""

from collections.abc import Callable
from dataclasses import dataclass
from uuid import uuid4

from cognition.contracts import (
    AssistantResponse,
    AssistantResponseType,
    CognitiveInteractionResult,
    ConversationTurn,
    ConversationTurnInput,
    ResponseCompositionInput,
    ResponseCompositionResult,
    safe_cognitive_text,
)
from cognition.context import ConversationContextProjector
from cognition.response_composer import CompatibilityResponseComposer, ResponseComposer
from cognition.sessions import ConversationSessionService
from cognition.sessions import _utc_now_iso


CompatibilityResponseDelegate = Callable[[ConversationTurnInput, ConversationTurn], str]


@dataclass(frozen=True)
class CognitiveInteractionService:
    """Coordinates one interaction without owning durable domain state."""

    session_service: ConversationSessionService
    response_delegate: CompatibilityResponseDelegate | None = None
    context_projector: ConversationContextProjector = ConversationContextProjector()
    response_composer: ResponseComposer | None = None
    assistant_source: str = "cognitive_interaction_service"

    def __post_init__(self) -> None:
        if self.response_composer is None:
            if self.response_delegate is None:
                raise ValueError("response_composer or response_delegate is required")
            object.__setattr__(
                self,
                "response_composer",
                CompatibilityResponseComposer(
                    lambda composition_input: self.response_delegate(
                        _turn_input_from_composition(composition_input),
                        composition_input.current_user_turn,
                    )
                ),
            )

    def handle_turn(self, turn_input: ConversationTurnInput) -> CognitiveInteractionResult:
        session = (
            self.session_service.create_session()
            if turn_input.session_id is None
            else self.session_service.get_snapshot(turn_input.session_id)
        )
        user_turn = self.session_service.append_user_turn(
            session.session_id,
            turn_input.text,
            turn_input.source,
        )
        source_session, source_turns = self.session_service.context_source(session.session_id)
        context = self.context_projector.project(source_session, source_turns)
        composition_input = ResponseCompositionInput(
            current_user_turn=user_turn,
            context=context,
            source=turn_input.source,
            locale=turn_input.locale,
            session=source_session,
        )
        try:
            composition = self.response_composer.compose(composition_input)
        except Exception:
            composition = ResponseCompositionResult(
                response_type=AssistantResponseType.ERROR,
                text="Conversation response generation failed safely.",
                context_turn_count_used=context.included_turn_count,
                composition_source="safe_error_fallback",
            )
        assistant_turn = self.session_service.append_assistant_turn(
            session.session_id,
            safe_cognitive_text(composition.text),
            self.assistant_source,
        )
        response = AssistantResponse(
            response_id=f"cog-response-{uuid4().hex}",
            session_id=session.session_id,
            turn_id=assistant_turn.turn_id,
            response_type=composition.response_type,
            text=assistant_turn.text,
            created_at=_utc_now_iso(),
        )
        return CognitiveInteractionResult(
            response=response,
            session=self.session_service.get_snapshot(session.session_id),
            context=context,
            composition=composition,
        )


def _turn_input_from_composition(composition_input: ResponseCompositionInput) -> ConversationTurnInput:
    return ConversationTurnInput(
        text=composition_input.current_user_turn.text,
        source=composition_input.source,
        session_id=composition_input.current_user_turn.session_id,
        locale=composition_input.locale,
    )
