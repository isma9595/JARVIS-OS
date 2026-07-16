"""Windows-compatible local filesystem adapter for JARVIS document workflows."""

from __future__ import annotations

from hashlib import sha256
import os
from pathlib import Path
import tempfile

from platform_adapters.contracts import (
    AtomicWriteResult,
    LocalFileSystemError,
    LocalFileSystemErrorCode,
    SafePathInfo,
)


class WindowsLocalFileSystemAdapter:
    """Local filesystem adapter with conservative Windows-first safety checks."""

    def inspect_path(self, requested_path: str) -> SafePathInfo:
        raw = self._clean_requested_path(requested_path)
        if self._is_unc_or_network_path(raw):
            raise LocalFileSystemError(
                LocalFileSystemErrorCode.NETWORK_PATH_DENIED,
                "Network paths are not supported.",
            )
        path = Path(raw)
        is_absolute = path.is_absolute()
        if not is_absolute:
            resolved_text = raw
            parent_text = str(path.parent)
        else:
            try:
                resolved_text = str(path.resolve(strict=False))
                parent_text = str(path.parent.resolve(strict=False))
            except OSError as exc:
                raise self._safe_error(LocalFileSystemErrorCode.INVALID_PATH) from exc

        try:
            exists = path.exists()
            is_symlink = path.is_symlink()
            is_directory = path.is_dir()
            is_file = path.is_file()
            size = path.stat().st_size if exists and is_file else None
        except OSError as exc:
            raise self._safe_error(LocalFileSystemErrorCode.INVALID_PATH) from exc

        return SafePathInfo(
            requested_path=raw,
            resolved_path=resolved_text,
            exists=exists,
            is_file=is_file,
            is_directory=is_directory,
            is_symlink=is_symlink,
            is_local=is_absolute and not self._is_unc_or_network_path(resolved_text),
            is_absolute=is_absolute,
            size_bytes=size,
            filename=path.name,
            suffix=path.suffix,
            stem=path.stem,
            parent_path=parent_text,
        )

    def same_path(self, first_path: str, second_path: str) -> bool:
        first = self._normalized_local_path(first_path)
        second = self._normalized_local_path(second_path)
        return first == second

    def sibling_path(self, source_path: str, sibling_filename: str) -> str:
        info = self.inspect_path(source_path)
        if not info.is_absolute or not info.is_local:
            raise LocalFileSystemError(
                LocalFileSystemErrorCode.PATH_NOT_ABSOLUTE,
                "Path must be absolute and local.",
            )
        return str(Path(info.resolved_path).with_name(str(sibling_filename)))

    def read_bounded_bytes(self, path: str, max_bytes: int) -> bytes:
        info = self.inspect_path(path)
        if not info.is_absolute:
            raise LocalFileSystemError(
                LocalFileSystemErrorCode.PATH_NOT_ABSOLUTE,
                "Path must be absolute.",
            )
        if not info.is_local:
            raise LocalFileSystemError(
                LocalFileSystemErrorCode.NETWORK_PATH_DENIED,
                "Network paths are not supported.",
            )
        if info.is_symlink:
            raise LocalFileSystemError(
                LocalFileSystemErrorCode.SYMLINK_DENIED,
                "Symbolic links are not supported.",
            )
        if not info.exists:
            raise LocalFileSystemError(
                LocalFileSystemErrorCode.FILE_NOT_FOUND,
                "File was not found.",
            )
        if not info.is_file:
            raise LocalFileSystemError(
                LocalFileSystemErrorCode.NOT_A_FILE,
                "Path is not a regular file.",
            )
        if info.size_bytes is not None and info.size_bytes > int(max_bytes):
            raise LocalFileSystemError(
                LocalFileSystemErrorCode.FILE_TOO_LARGE,
                "File is too large.",
            )
        try:
            limit = int(max_bytes)
            with open(info.resolved_path, "rb") as handle:
                data = handle.read(limit + 1)
        except OSError as exc:
            raise self._safe_error(LocalFileSystemErrorCode.READ_FAILED) from exc
        if len(data) > limit:
            raise LocalFileSystemError(
                LocalFileSystemErrorCode.FILE_TOO_LARGE,
                "File is too large.",
            )
        return data

    def atomic_write_new_file(
        self,
        *,
        target_path: str,
        data: bytes,
        source_path: str | None = None,
    ) -> AtomicWriteResult:
        target_info = self.inspect_path(target_path)
        if not target_info.is_absolute:
            raise LocalFileSystemError(
                LocalFileSystemErrorCode.PATH_NOT_ABSOLUTE,
                "Target path must be absolute.",
            )
        if not target_info.is_local:
            raise LocalFileSystemError(
                LocalFileSystemErrorCode.NETWORK_PATH_DENIED,
                "Network paths are not supported.",
            )
        if source_path is not None and self.same_path(source_path, target_info.resolved_path):
            raise LocalFileSystemError(
                LocalFileSystemErrorCode.SOURCE_TARGET_CONFLICT,
                "Source and target paths must differ.",
            )
        if target_info.exists:
            raise LocalFileSystemError(
                LocalFileSystemErrorCode.TARGET_EXISTS,
                "Target already exists.",
            )

        target = Path(target_info.resolved_path)
        temp_name: str | None = None
        target_created = False
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=str(target.parent),
                prefix=f".{target.stem}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temp_name = handle.name
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())

            if target.exists():
                raise LocalFileSystemError(
                    LocalFileSystemErrorCode.TARGET_EXISTS,
                    "Target already exists.",
                )
            try:
                os.link(temp_name, target)
                target_created = True
            except FileExistsError as exc:
                raise LocalFileSystemError(
                    LocalFileSystemErrorCode.TARGET_EXISTS,
                    "Target already exists.",
                ) from exc
            except OSError:
                flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
                try:
                    fd = os.open(str(target), flags)
                except FileExistsError as exc:
                    raise LocalFileSystemError(
                        LocalFileSystemErrorCode.TARGET_EXISTS,
                        "Target already exists.",
                    ) from exc
                target_created = True
                with os.fdopen(fd, "wb") as handle:
                    handle.write(data)
                    handle.flush()
                    os.fsync(handle.fileno())

            output = self.read_bounded_bytes(str(target), len(data))
            if output != data:
                raise LocalFileSystemError(
                    LocalFileSystemErrorCode.VERIFICATION_FAILED,
                    "Written bytes did not verify.",
                )
            return AtomicWriteResult(
                target_path=str(target),
                bytes_written=len(output),
                verified=True,
                output_hash=self._hash_bytes(output),
                safe_message="File created and verified.",
            )
        except LocalFileSystemError:
            if target_created:
                self._remove_created_target(target)
            raise
        except OSError as exc:
            if target_created:
                self._remove_created_target(target)
            raise self._safe_error(LocalFileSystemErrorCode.WRITE_FAILED) from exc
        finally:
            if temp_name is not None:
                self._cleanup_temp_file(temp_name)

    @staticmethod
    def _clean_requested_path(requested_path: str) -> str:
        return str(requested_path or "").strip().strip('"')

    @staticmethod
    def _is_unc_or_network_path(path: str) -> bool:
        return path.startswith("\\\\") or path.startswith("//")

    def _normalized_local_path(self, path: str) -> str:
        info = self.inspect_path(path)
        if not info.is_absolute:
            raise LocalFileSystemError(
                LocalFileSystemErrorCode.PATH_NOT_ABSOLUTE,
                "Path must be absolute.",
            )
        if not info.is_local:
            raise LocalFileSystemError(
                LocalFileSystemErrorCode.NETWORK_PATH_DENIED,
                "Network paths are not supported.",
            )
        return os.path.normcase(os.path.abspath(info.resolved_path))

    @staticmethod
    def _hash_bytes(raw: bytes) -> str:
        return "sha256:" + sha256(raw).hexdigest()

    @staticmethod
    def _safe_error(code: LocalFileSystemErrorCode) -> LocalFileSystemError:
        return LocalFileSystemError(code, "Local filesystem operation failed safely.")

    @staticmethod
    def _cleanup_temp_file(temp_name: str) -> None:
        try:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
        except OSError as exc:
            raise LocalFileSystemError(
                LocalFileSystemErrorCode.TEMPORARY_CLEANUP_FAILED,
                "Temporary file cleanup failed.",
            ) from exc

    @staticmethod
    def _remove_created_target(target: Path) -> None:
        try:
            if target.exists():
                os.unlink(target)
        except OSError as exc:
            raise LocalFileSystemError(
                LocalFileSystemErrorCode.TEMPORARY_CLEANUP_FAILED,
                "Temporary file cleanup failed.",
            ) from exc
