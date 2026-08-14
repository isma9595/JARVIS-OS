"""Platform adapter boundaries for local operating-system operations."""

from platform_adapters.contracts import (
    AtomicWriteResult,
    LocalFileSystemError,
    LocalFileSystemErrorCode,
    LocalFileSystemPort,
    SafePathInfo,
)
from platform_adapters.local_filesystem import WindowsLocalFileSystemAdapter
from platform_adapters.user_data_migration import (
    CompositionMigrationReport,
    DeterministicLegacyRegistry,
    MigrationAttemptProjection,
    UserDataMigrationBlockedError,
    UserDataMigrationCoordinator,
)
from platform_adapters.user_data_paths import (
    USER_DATA_LAYOUT_VERSION,
    UserDataPathResolutionError,
    UserDataPaths,
)

__all__ = [
    "AtomicWriteResult",
    "LocalFileSystemError",
    "LocalFileSystemErrorCode",
    "LocalFileSystemPort",
    "SafePathInfo",
    "WindowsLocalFileSystemAdapter",
    "CompositionMigrationReport",
    "DeterministicLegacyRegistry",
    "MigrationAttemptProjection",
    "USER_DATA_LAYOUT_VERSION",
    "UserDataMigrationBlockedError",
    "UserDataMigrationCoordinator",
    "UserDataPathResolutionError",
    "UserDataPaths",
]
