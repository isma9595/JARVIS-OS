"""Application-facing service layer for JARVIS."""

from app.app_service import (
    AppCommandPreview,
    AppCommandResult,
    AppCommandSource,
    AppStatusSnapshot,
    JarvisAppService,
)
from app.app_contracts import (
    APP_CONTRACT_SCHEMA_NAME,
    APP_CONTRACT_VERSION,
    AppCommandCard,
    AppContractManifest,
    AppContractStatus,
    AppExecutionContract,
    AppPreviewContract,
    AppStatusCard,
)
from app.desktop_shell import (
    DesktopShellState,
    DesktopShellViewModel,
    JarvisDesktopShell,
    launch_desktop_shell,
)
from app.vertical_integration import (
    VerticalIntegrationCheck,
    VerticalIntegrationReport,
    VerticalIntegrationService,
)

__all__ = [
    "AppCommandPreview",
    "AppCommandResult",
    "AppCommandSource",
    "AppCommandCard",
    "AppContractManifest",
    "AppContractStatus",
    "AppExecutionContract",
    "AppPreviewContract",
    "AppStatusSnapshot",
    "AppStatusCard",
    "APP_CONTRACT_SCHEMA_NAME",
    "APP_CONTRACT_VERSION",
    "DesktopShellState",
    "DesktopShellViewModel",
    "JarvisAppService",
    "JarvisDesktopShell",
    "VerticalIntegrationCheck",
    "VerticalIntegrationReport",
    "VerticalIntegrationService",
    "launch_desktop_shell",
]
