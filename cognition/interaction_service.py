"""Turn-local cognitive interaction orchestration for TASK-113."""

from collections.abc import Callable
from dataclasses import dataclass
from uuid import uuid4

from cognition.contracts import (
    AssistantResponse,
    AssistantResponseType,
    CognitiveInteractionResult,
    ConversationTurn,
    ConversationTurnInput,
    safe_cognitive_text,
)
from cognition.sessions import ConversationSessionService
from cognition.sessions import _utc_now_iso


CompatibilityResponseDelegate = Callable[[ConversationTurnInput, ConversationTurn], str]


@dataclass(frozen=True)
class CognitiveInteractionService:
    """Coordinates one interaction without owning durable domain state."""

    session_service: ConversationSessionService
    response_delegate: CompatibilityResponseDelegate
    assistant_source: str = "cognitive_interaction_service"

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
        response_type = AssistantResponseType.MESSAGE
        try:
            response_text = self.response_delegate(turn_input, user_turn)
        except Exception:
            response_type = AssistantResponseType.ERROR
            response_text = "Conversation response generation failed safely."
        assistant_turn = self.session_service.append_assistant_turn(
            session.session_id,
            safe_cognitive_text(response_text),
            self.assistant_source,
        )
        response = AssistantResponse(
            response_id=f"cog-response-{uuid4().hex}",
            session_id=session.session_id,
            turn_id=assistant_turn.turn_id,
            response_type=response_type,
            text=assistant_turn.text,
            created_at=_utc_now_iso(),
        )
        return CognitiveInteractionResult(
            response=response,
            session=self.session_service.get_snapshot(session.session_id),
        )
