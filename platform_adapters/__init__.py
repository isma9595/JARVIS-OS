"""Platform adapter boundaries for local operating-system operations."""

from platform_adapters.contracts import (
    AtomicWriteResult,
    LocalFileSystemError,
    LocalFileSystemErrorCode,
    LocalFileSystemPort,
    SafePathInfo,
)
from platform_adapters.local_filesystem import WindowsLocalFileSystemAdapter

__all__ = [
    "AtomicWriteResult",
    "LocalFileSystemError",
    "LocalFileSystemErrorCode",
    "LocalFileSystemPort",
    "SafePathInfo",
    "WindowsLocalFileSystemAdapter",
]
