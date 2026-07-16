"""Typed local filesystem port used by document workflows."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol, runtime_checkable


class LocalFileSystemErrorCode(Enum):
    INVALID_PATH = "invalid_path"
    PATH_NOT_ABSOLUTE = "path_not_absolute"
    NETWORK_PATH_DENIED = "network_path_denied"
    FILE_NOT_FOUND = "file_not_found"
    NOT_A_FILE = "not_a_file"
    SYMLINK_DENIED = "symlink_denied"
    FILE_TOO_LARGE = "file_too_large"
    TARGET_EXISTS = "target_exists"
    SOURCE_TARGET_CONFLICT = "source_target_conflict"
    READ_FAILED = "read_failed"
    WRITE_FAILED = "write_failed"
    VERIFICATION_FAILED = "verification_failed"
    TEMPORARY_CLEANUP_FAILED = "temporary_cleanup_failed"


class LocalFileSystemError(OSError):
    """Safe filesystem error that does not expose raw OS exception text."""

    def __init__(self, code: LocalFileSystemErrorCode, safe_message: str):
        super().__init__(safe_message)
        self.code = code.value
        self.safe_message = safe_message


@dataclass(frozen=True)
class SafePathInfo:
    requested_path: str
    resolved_path: str
    exists: bool
    is_file: bool
    is_directory: bool
    is_symlink: bool
    is_local: bool
    is_absolute: bool
    size_bytes: int | None
    filename: str
    suffix: str
    stem: str
    parent_path: str

    def to_dict(self) -> dict[str, object]:
        return {
            "requested_path": self.requested_path,
            "resolved_path": self.resolved_path,
            "exists": self.exists,
            "is_file": self.is_file,
            "is_directory": self.is_directory,
            "is_symlink": self.is_symlink,
            "is_local": self.is_local,
            "is_absolute": self.is_absolute,
            "size_bytes": self.size_bytes,
            "filename": self.filename,
            "suffix": self.suffix,
            "stem": self.stem,
            "parent_path": self.parent_path,
        }


@dataclass(frozen=True)
class AtomicWriteResult:
    target_path: str
    bytes_written: int
    verified: bool
    output_hash: str
    safe_error_code: str | None = None
    safe_message: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "target_path": self.target_path,
            "bytes_written": self.bytes_written,
            "verified": self.verified,
            "output_hash": self.output_hash,
            "safe_error_code": self.safe_error_code,
            "safe_message": self.safe_message,
        }


@runtime_checkable
class LocalFileSystemPort(Protocol):
    def inspect_path(self, requested_path: str) -> SafePathInfo:
        """Return safe local path metadata without file contents."""

    def same_path(self, first_path: str, second_path: str) -> bool:
        """Return whether two local paths resolve to the same filesystem target."""

    def sibling_path(self, source_path: str, sibling_filename: str) -> str:
        """Return a sibling path using local platform path semantics."""

    def read_bounded_bytes(self, path: str, max_bytes: int) -> bytes:
        """Read file bytes only when the bounded size check passes."""

    def atomic_write_new_file(
        self,
        *,
        target_path: str,
        data: bytes,
        source_path: str | None = None,
    ) -> AtomicWriteResult:
        """Atomically create a new local file without overwriting an existing target."""
