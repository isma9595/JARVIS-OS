"""Cognitive layer contracts, session services, and persistence boundaries."""

from cognition.contracts import (
    AssistantResponse,
    AssistantResponseType,
    CognitiveInteractionResult,
    ConversationRole,
    ConversationSessionSnapshot,
    ConversationSessionStatus,
    ConversationTurn,
    ConversationTurnInput,
    InvalidConversationTurnError,
)
from cognition.interaction_service import CognitiveInteractionService
from cognition.persistence import (
    CONVERSATION_SESSION_SCHEMA_VERSION,
    MAX_PERSISTED_TURN_SUMMARY_LENGTH,
    ConversationPersistenceCorruptionError,
    ConversationPersistenceError,
    ConversationPersistenceLoadError,
    ConversationPersistenceLoadResult,
    ConversationPersistenceWriteError,
    ConversationSessionRepository,
    LocalConversationSessionRepository,
    PersistedConversationSessionRecord,
    PersistedConversationTurnSummary,
    PersistedTurnContentClassification,
)
from cognition.sessions import (
    ConversationSessionClosedError,
    ConversationSessionNotFoundError,
    ConversationSessionService,
)

__all__ = [
    "AssistantResponse",
    "AssistantResponseType",
    "CognitiveInteractionResult",
    "CognitiveInteractionService",
    "CONVERSATION_SESSION_SCHEMA_VERSION",
    "MAX_PERSISTED_TURN_SUMMARY_LENGTH",
    "ConversationPersistenceCorruptionError",
    "ConversationPersistenceError",
    "ConversationPersistenceLoadError",
    "ConversationPersistenceLoadResult",
    "ConversationPersistenceWriteError",
    "ConversationRole",
    "ConversationSessionClosedError",
    "ConversationSessionNotFoundError",
    "ConversationSessionRepository",
    "ConversationSessionService",
    "ConversationSessionSnapshot",
    "ConversationSessionStatus",
    "ConversationTurn",
    "ConversationTurnInput",
    "InvalidConversationTurnError",
    "LocalConversationSessionRepository",
    "PersistedConversationSessionRecord",
    "PersistedConversationTurnSummary",
    "PersistedTurnContentClassification",
]
