"""Application-facing service layer for JARVIS."""

from app.app_contracts import (
    APP_CONTRACT_SCHEMA_NAME,
    APP_CONTRACT_VERSION,
    AppCommandCard,
    AppCommandPreview,
    AppCommandResult,
    AppCommandSource,
    ApplicationActivityDto,
    ApplicationActivityKind,
    ApplicationActivitySnapshotDto,
    ApplicationActivityState,
    AppClarificationOption,
    AppContractManifest,
    AppContractStatus,
    AppDesktopChatStatus,
    AppDesktopTurnDiagnostics,
    AppDesktopTurnResult,
    AppExecutionContract,
    AppExecutionHistoryEntry,
    AppExecutionHistoryResult,
    AppIntentResolutionContract,
    AppPreviewContract,
    AppStatusCard,
    AppVoiceRequestResult,
)

__all__ = [
    "AppCommandPreview",
    "AppCommandResult",
    "AppCommandSource",
    "AppCommandCard",
    "ApplicationActivityDto",
    "ApplicationActivityKind",
    "ApplicationActivitySnapshotDto",
    "ApplicationActivityState",
    "AppClarificationOption",
    "AppContractManifest",
    "AppContractStatus",
    "AppDesktopChatStatus",
    "AppDesktopTurnDiagnostics",
    "AppDesktopTurnResult",
    "AppExecutionContract",
    "AppExecutionHistoryEntry",
    "AppExecutionHistoryResult",
    "AppIntentResolutionContract",
    "AppPreviewContract",
    "AppStatusSnapshot",
    "AppStatusCard",
    "AppVoiceRequestResult",
    "WorkflowHistoryResult",
    "WorkflowRunHistory",
    "WorkflowRunHistoryState",
    "WorkflowStepHistory",
    "WorkflowStepHistoryState",
    "APP_CONTRACT_SCHEMA_NAME",
    "APP_CONTRACT_VERSION",
    "ConversationIntent",
    "ConversationRoute",
    "ConversationSafetyLevel",
    "ConversationalRequest",
    "ConversationalResult",
    "DesktopShellState",
    "DesktopShellViewModel",
    "JarvisAppService",
    "JarvisDesktopShell",
    "ClarificationState",
    "HybridIntentResolver",
    "IntentConfidence",
    "IntentKind",
    "IntentResolution",
    "ResolutionStatus",
    "SafeConversationalLoop",
    "VerticalIntegrationCheck",
    "VerticalIntegrationReport",
    "VerticalIntegrationService",
    "launch_desktop_shell",
]


def __getattr__(name: str):
    if name in {"AppStatusSnapshot", "JarvisAppService"}:
        from app.app_service import AppStatusSnapshot, JarvisAppService

        values = {
            "AppStatusSnapshot": AppStatusSnapshot,
            "JarvisAppService": JarvisAppService,
        }
    elif name in {
        "ConversationIntent",
        "ConversationRoute",
        "ConversationSafetyLevel",
        "ConversationalRequest",
        "ConversationalResult",
        "SafeConversationalLoop",
    }:
        from app.conversational_loop import (
            ConversationIntent,
            ConversationRoute,
            ConversationSafetyLevel,
            ConversationalRequest,
            ConversationalResult,
            SafeConversationalLoop,
        )

        values = {
            "ConversationIntent": ConversationIntent,
            "ConversationRoute": ConversationRoute,
            "ConversationSafetyLevel": ConversationSafetyLevel,
            "ConversationalRequest": ConversationalRequest,
            "ConversationalResult": ConversationalResult,
            "SafeConversationalLoop": SafeConversationalLoop,
        }
    elif name in {
        "ClarificationState",
        "HybridIntentResolver",
        "IntentConfidence",
        "IntentKind",
        "IntentResolution",
        "ResolutionStatus",
    }:
        from app.intent_resolver import (
            ClarificationState,
            HybridIntentResolver,
            IntentConfidence,
            IntentKind,
            IntentResolution,
            ResolutionStatus,
        )

        values = {
            "ClarificationState": ClarificationState,
            "HybridIntentResolver": HybridIntentResolver,
            "IntentConfidence": IntentConfidence,
            "IntentKind": IntentKind,
            "IntentResolution": IntentResolution,
            "ResolutionStatus": ResolutionStatus,
        }
    elif name in {
        "DesktopShellState",
        "DesktopShellViewModel",
        "JarvisDesktopShell",
        "launch_desktop_shell",
    }:
        from app.desktop_shell import (
            DesktopShellState,
            DesktopShellViewModel,
            JarvisDesktopShell,
            launch_desktop_shell,
        )

        values = {
            "DesktopShellState": DesktopShellState,
            "DesktopShellViewModel": DesktopShellViewModel,
            "JarvisDesktopShell": JarvisDesktopShell,
            "launch_desktop_shell": launch_desktop_shell,
        }
    elif name in {
        "WorkflowHistoryResult",
        "WorkflowRunHistory",
        "WorkflowRunHistoryState",
        "WorkflowStepHistory",
        "WorkflowStepHistoryState",
    }:
        from workflows.contracts import (
            WorkflowHistoryResult,
            WorkflowRunHistory,
            WorkflowRunHistoryState,
            WorkflowStepHistory,
            WorkflowStepHistoryState,
        )

        values = {
            "WorkflowHistoryResult": WorkflowHistoryResult,
            "WorkflowRunHistory": WorkflowRunHistory,
            "WorkflowRunHistoryState": WorkflowRunHistoryState,
            "WorkflowStepHistory": WorkflowStepHistory,
            "WorkflowStepHistoryState": WorkflowStepHistoryState,
        }
    elif name in {
        "VerticalIntegrationCheck",
        "VerticalIntegrationReport",
        "VerticalIntegrationService",
    }:
        from app.vertical_integration import (
            VerticalIntegrationCheck,
            VerticalIntegrationReport,
            VerticalIntegrationService,
        )

        values = {
            "VerticalIntegrationCheck": VerticalIntegrationCheck,
            "VerticalIntegrationReport": VerticalIntegrationReport,
            "VerticalIntegrationService": VerticalIntegrationService,
        }
    else:
        raise AttributeError(f"module 'app' has no attribute {name!r}")

    globals().update(values)
    return values[name]
