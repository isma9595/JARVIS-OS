"""Deterministic, copy-only adoption of known local user-data stores.

This module deliberately owns only the bounded migration attempt.  Runtime
store contents and schemas remain owned by their existing repositories and
managers.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
import stat
import threading
import time
import uuid
from typing import Protocol

from platform_adapters.user_data_paths import UserDataPaths


LAYOUT_VERSION = "v1"
ORDINARY_STORE_IDS = (
    "conversation",
    "memory",
    "profile",
    "ideas",
    "vosk_settings",
)

_CANONICAL_ATTRIBUTE = {
    "conversation": "conversation_sessions",
    "memory": "memory",
    "profile": "profile",
    "ideas": "ideas",
    "vosk_settings": "vosk_settings",
}
_NON_BLOCKING_CODES = {"not_required", "migrated", "provenance_established"}
_PUBLIC_CODE = {
    "legacy_corrupt": "corrupt",
    "legacy_unsupported_version": "unsupported_version",
    "migration_unavailable": "unavailable",
}
_SESSION_ID = re.compile(r"^[A-Za-z0-9_.-]+$")
_SOURCE_CLASSIFICATION = re.compile(r"^[a-z0-9_.-]{1,64}$")
_JSON_PARSE_ERRORS = (
    UnicodeDecodeError,
    json.JSONDecodeError,
    ValueError,
    RecursionError,
)
_SESSION_KEYS = {
    "schema_version",
    "session_id",
    "status",
    "created_at",
    "updated_at",
    "turn_count",
    "last_turn_id",
    "turns",
    "revision",
}
_TURN_KEYS = {
    "turn_id",
    "sequence",
    "role",
    "source_classification",
    "created_at",
    "summary_text",
    "content_classification",
    "redaction_reason",
}


class _UnsafeFilesystemState(Exception):
    pass


class UserDataMigrationBlockedError(RuntimeError):
    """Safe composition failure raised before ordinary owners are created."""

    def __init__(self, store_id: str):
        self.code = "user_data_migration_blocked"
        self.store_id = store_id if store_id in ORDINARY_STORE_IDS else "unknown"
        super().__init__(f"{self.code}:{self.store_id}")

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(code={self.code!r}, "
            f"store_id={self.store_id!r})"
        )


@dataclass(frozen=True, slots=True)
class MigrationAttemptProjection:
    layout_version: str
    store_id: str
    code: str
    blocking: bool


@dataclass(frozen=True, slots=True)
class MigrationAttemptResult:
    internal_code: str
    projection: MigrationAttemptProjection


@dataclass(frozen=True, slots=True)
class CompositionMigrationReport:
    layout_version: str
    attempts: tuple[MigrationAttemptProjection, ...]
    completed: bool
    blocking_store_id: str | None


@dataclass(frozen=True, slots=True)
class DeterministicLegacyRegistry:
    _candidates: tuple[tuple[str, tuple[Path, ...]], ...] = field(repr=False)

    @classmethod
    def from_mapping(
        cls,
        candidates: Mapping[str, tuple[Path, ...]],
    ) -> "DeterministicLegacyRegistry":
        unknown = set(candidates).difference(ORDINARY_STORE_IDS)
        if unknown:
            raise ValueError("unsupported_store_id")
        normalized: list[tuple[str, tuple[Path, ...]]] = []
        for store_id in ORDINARY_STORE_IDS:
            selected: list[Path] = []
            for candidate in candidates.get(store_id, ()):
                try:
                    path = Path(os.fspath(candidate))
                except Exception:
                    raise ValueError("legacy_candidate_invalid") from None
                if not path.is_absolute():
                    raise ValueError("legacy_candidate_not_absolute")
                selected.append(Path(os.path.normpath(os.fspath(path))))
            normalized.append((store_id, tuple(selected)))
        return cls(tuple(normalized))

    @classmethod
    def from_user_data_paths(
        cls,
        paths: UserDataPaths,
        *,
        conversation_legacy: Path,
    ) -> "DeterministicLegacyRegistry":
        return cls.from_mapping(
            {
                "conversation": (conversation_legacy,),
                "memory": (paths.project_root / "memory" / "local" / "memory.json",),
                "profile": (
                    paths.project_root / "users" / "profiles" / "default_user.json",
                ),
                "ideas": (paths.project_root / "ideas" / "ideas.json",),
                "vosk_settings": (
                    paths.project_root / "config" / "local" / "vosk_settings.json",
                ),
            }
        )

    def candidates_for(self, store_id: str) -> tuple[Path, ...]:
        if store_id not in ORDINARY_STORE_IDS:
            raise ValueError("unsupported_store_id")
        return dict(self._candidates)[store_id]

    def __repr__(self) -> str:
        counts = tuple((store_id, len(paths)) for store_id, paths in self._candidates)
        return f"{type(self).__name__}(candidate_counts={counts!r})"


class MigrationPublicationAdapter(Protocol):
    def publish_file(self, target: Path, payload: bytes) -> bool: ...

    def publish_directory(
        self,
        target: Path,
        entries: tuple[tuple[str, bytes], ...],
    ) -> bool: ...


class MigrationLockAdapter(Protocol):
    def acquire(
        self,
        canonical_root: Path,
        store_id: str,
        timeout_seconds: float,
    ) -> Iterator[None]: ...


class LocalMigrationPublicationAdapter:
    """Publish immutable snapshots without replacing an existing target."""

    def __init__(self, canonical_root: Path):
        self._canonical_root = canonical_root

    def publish_file(self, target: Path, payload: bytes) -> bool:
        _ensure_safe_parent_directories(self._canonical_root, target.parent)
        staging = target.parent / f".{target.name}.{uuid.uuid4().hex}.migration"
        descriptor: int | None = None
        try:
            descriptor = os.open(
                staging,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0),
                0o600,
            )
            view = memoryview(payload)
            while view:
                written = os.write(descriptor, view)
                if written <= 0:
                    raise OSError("publication write failed")
                view = view[written:]
            os.fsync(descriptor)
            os.close(descriptor)
            descriptor = None
            try:
                os.link(staging, target, follow_symlinks=False)
            except FileExistsError:
                return False
            return True
        finally:
            if descriptor is not None:
                os.close(descriptor)
            try:
                staging.unlink()
            except FileNotFoundError:
                pass
            except OSError:
                pass

    def publish_directory(
        self,
        target: Path,
        entries: tuple[tuple[str, bytes], ...],
    ) -> bool:
        _ensure_safe_parent_directories(self._canonical_root, target.parent)
        staging = target.parent / f".{target.name}.{uuid.uuid4().hex}.migration"
        staging.mkdir(mode=0o700)
        try:
            for name, payload in entries:
                child = staging / name
                descriptor = os.open(
                    child,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0),
                    0o600,
                )
                try:
                    view = memoryview(payload)
                    while view:
                        written = os.write(descriptor, view)
                        if written <= 0:
                            raise OSError("publication write failed")
                        view = view[written:]
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
            try:
                os.rename(staging, target)
            except (FileExistsError, OSError):
                if _entry_kind(target) != "absent":
                    return False
                raise
            return True
        finally:
            if staging.exists():
                for child in staging.iterdir():
                    try:
                        child.unlink()
                    except OSError:
                        pass
                try:
                    staging.rmdir()
                except OSError:
                    pass


class LocalMigrationLockAdapter:
    """A bounded inter-process lock represented by one private exclusive file."""

    @contextmanager
    def acquire(
        self,
        canonical_root: Path,
        store_id: str,
        timeout_seconds: float,
    ) -> Iterator[None]:
        lock_directory = canonical_root / ".migration" / LAYOUT_VERSION / ".locks"
        _ensure_safe_parent_directories(canonical_root, lock_directory)
        lock_path = lock_directory / f"{store_id}.lock"
        deadline = time.monotonic() + max(0.0, timeout_seconds)
        descriptor: int | None = None
        while descriptor is None:
            try:
                descriptor = os.open(
                    lock_path,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0),
                    0o600,
                )
            except FileExistsError:
                if time.monotonic() >= deadline:
                    raise TimeoutError("migration lock timeout") from None
                time.sleep(min(0.01, max(0.0, deadline - time.monotonic())))
        try:
            yield
        finally:
            os.close(descriptor)
            try:
                lock_path.unlink()
            except FileNotFoundError:
                pass


@dataclass(frozen=True, slots=True)
class _Snapshot:
    kind: str
    file_bytes: bytes | None = field(default=None, repr=False)
    entries: tuple[tuple[str, bytes], ...] = field(default=(), repr=False)


class UserDataMigrationCoordinator:
    """Evaluate and publish one deterministic migration attempt at a time."""

    def __init__(
        self,
        paths: UserDataPaths,
        registry: DeterministicLegacyRegistry,
        *,
        external_overrides: Mapping[str, Path] | None = None,
        publication_adapter: MigrationPublicationAdapter | None = None,
        lock_adapter: MigrationLockAdapter | None = None,
        lock_timeout_seconds: float = 5.0,
    ) -> None:
        unknown = set(external_overrides or {}).difference(ORDINARY_STORE_IDS)
        if unknown:
            raise ValueError("unsupported_store_id")
        self._paths = paths
        self._registry = registry
        self._external_overrides = dict(external_overrides or {})
        self._publication = publication_adapter or LocalMigrationPublicationAdapter(paths.root)
        self._locks = lock_adapter or LocalMigrationLockAdapter()
        self._lock_timeout_seconds = float(lock_timeout_seconds)

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(layout_version={LAYOUT_VERSION!r}, "
            f"external_override_count={len(self._external_overrides)!r})"
        )

    def attempt_store(self, store_id: str) -> MigrationAttemptResult:
        if store_id not in ORDINARY_STORE_IDS:
            raise ValueError("unsupported_store_id")
        if store_id in self._external_overrides:
            return self._attempt_external_override(store_id)

        try:
            if not self._migration_state_may_exist(store_id):
                return _result(store_id, "not_required")
            with self._locks.acquire(
                self._paths.root,
                store_id,
                self._lock_timeout_seconds,
            ):
                return self._attempt_default_locked(store_id)
        except (OSError, TimeoutError, NotImplementedError, _UnsafeFilesystemState):
            return _result(store_id, "migration_unavailable")

    def migrate_all(self) -> CompositionMigrationReport:
        attempts: list[MigrationAttemptProjection] = []
        for store_id in ORDINARY_STORE_IDS:
            result = self.attempt_store(store_id)
            attempts.append(result.projection)
            if result.projection.blocking:
                return CompositionMigrationReport(
                    layout_version=LAYOUT_VERSION,
                    attempts=tuple(attempts),
                    completed=False,
                    blocking_store_id=store_id,
                )
        return CompositionMigrationReport(
            layout_version=LAYOUT_VERSION,
            attempts=tuple(attempts),
            completed=True,
            blocking_store_id=None,
        )

    def _migration_state_may_exist(self, store_id: str) -> bool:
        canonical = self._canonical_path(store_id)
        receipt = self._receipt_path(store_id)
        for path in (receipt, canonical, *self._registry.candidates_for(store_id)):
            if _entry_kind(path, inspect_ancestors=True) != "absent":
                return True
        return False

    def _attempt_external_override(self, store_id: str) -> MigrationAttemptResult:
        path = self._external_overrides[store_id]
        try:
            expected = "directory" if store_id == "conversation" else "file"
            kind = _entry_kind(path, inspect_ancestors=True)
            if kind == "absent":
                return _result(store_id, "skipped_external_override", blocking=False)
            if kind != expected:
                raise _UnsafeFilesystemState
            snapshot = _read_snapshot(path, store_id)
            validity = _validate_snapshot(store_id, snapshot)
            return _result(
                store_id,
                "skipped_external_override",
                blocking=validity != "valid",
            )
        except (OSError, _UnsafeFilesystemState):
            return _result(store_id, "migration_unavailable")

    def _attempt_default_locked(
        self,
        store_id: str,
        *,
        allow_publication: bool = True,
    ) -> MigrationAttemptResult:
        receipt_path = self._receipt_path(store_id)
        canonical_path = self._canonical_path(store_id)
        expected = "directory" if store_id == "conversation" else "file"

        receipt_kind = _entry_kind(receipt_path, inspect_ancestors=True)
        if receipt_kind != "absent":
            if receipt_kind != "file":
                raise _UnsafeFilesystemState
            receipt = _read_file_bytes(receipt_path)
            if not _valid_receipt(receipt, store_id):
                return _result(store_id, "migration_state_invalid")
            canonical_kind = _entry_kind(canonical_path, inspect_ancestors=True)
            if canonical_kind == "absent":
                return _result(store_id, "migration_state_invalid")
            if canonical_kind != expected:
                raise _UnsafeFilesystemState
            validity = _validate_snapshot(store_id, _read_snapshot(canonical_path, store_id))
            return _validation_result(store_id, validity, legacy=False, valid_code="not_required")

        canonical_kind = _entry_kind(canonical_path, inspect_ancestors=True)
        if canonical_kind not in {"absent", expected}:
            raise _UnsafeFilesystemState
        canonical_snapshot: _Snapshot | None = None
        if canonical_kind != "absent":
            canonical_snapshot = _read_snapshot(canonical_path, store_id)
            validity = _validate_snapshot(store_id, canonical_snapshot)
            if validity != "valid":
                return _validation_result(store_id, validity, legacy=False)

        candidates = self._safe_existing_candidates(store_id, expected)
        if len(candidates) > 1:
            return _result(store_id, "multiple_legacy_sources")
        if not candidates:
            if canonical_snapshot is None:
                return _result(store_id, "not_required")
            if not allow_publication:
                return _result(store_id, "migration_unavailable")
            if not self._publish_receipt(store_id):
                return self._attempt_default_locked(store_id, allow_publication=False)
            return _result(store_id, "provenance_established")

        legacy_snapshot = _read_snapshot(candidates[0], store_id)
        legacy_validity = _validate_snapshot(store_id, legacy_snapshot)
        if legacy_validity != "valid":
            return _validation_result(store_id, legacy_validity, legacy=True)

        if canonical_snapshot is not None:
            if canonical_snapshot != legacy_snapshot:
                return _result(store_id, "canonical_legacy_conflict")
            if not allow_publication:
                return _result(store_id, "migration_unavailable")
            if not self._publish_receipt(store_id):
                return self._attempt_default_locked(store_id, allow_publication=False)
            return _result(store_id, "provenance_established")

        if not allow_publication:
            return _result(store_id, "migration_unavailable")
        published = self._publish_snapshot(canonical_path, legacy_snapshot)
        if not published:
            return self._attempt_default_locked(store_id, allow_publication=False)
        if not self._publish_receipt(store_id):
            return self._attempt_default_locked(store_id, allow_publication=False)
        return _result(store_id, "migrated")

    def _safe_existing_candidates(self, store_id: str, expected: str) -> tuple[Path, ...]:
        existing: list[Path] = []
        for candidate in self._registry.candidates_for(store_id):
            kind = _entry_kind(candidate, inspect_ancestors=True)
            if kind == "absent":
                continue
            if kind != expected:
                raise _UnsafeFilesystemState
            existing.append(candidate)
        return tuple(existing)

    def _publish_snapshot(self, target: Path, snapshot: _Snapshot) -> bool:
        if snapshot.kind == "file":
            assert snapshot.file_bytes is not None
            return self._publication.publish_file(target, snapshot.file_bytes)
        return self._publication.publish_directory(target, snapshot.entries)

    def _publish_receipt(self, store_id: str) -> bool:
        payload = json.dumps(
            {
                "layout_version": LAYOUT_VERSION,
                "store_id": store_id,
                "established": True,
            },
            ensure_ascii=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return self._publication.publish_file(self._receipt_path(store_id), payload)

    def _canonical_path(self, store_id: str) -> Path:
        return getattr(self._paths, _CANONICAL_ATTRIBUTE[store_id])

    def _receipt_path(self, store_id: str) -> Path:
        return self._paths.root / ".migration" / LAYOUT_VERSION / f"{store_id}.json"


def _result(
    store_id: str,
    internal_code: str,
    *,
    blocking: bool | None = None,
) -> MigrationAttemptResult:
    public_code = _PUBLIC_CODE.get(internal_code, internal_code)
    if blocking is None:
        blocking = internal_code not in _NON_BLOCKING_CODES
    projection = MigrationAttemptProjection(
        layout_version=LAYOUT_VERSION,
        store_id=store_id,
        code=public_code,
        blocking=blocking,
    )
    return MigrationAttemptResult(internal_code=internal_code, projection=projection)


def _validation_result(
    store_id: str,
    validity: str,
    *,
    legacy: bool,
    valid_code: str = "not_required",
) -> MigrationAttemptResult:
    if validity == "valid":
        return _result(store_id, valid_code)
    if validity == "unsupported_version":
        return _result(
            store_id,
            "legacy_unsupported_version" if legacy else "unsupported_version",
        )
    return _result(store_id, "legacy_corrupt" if legacy else "corrupt")


def _valid_receipt(payload: bytes, store_id: str) -> bool:
    try:
        value = json.loads(payload.decode("utf-8"))
    except _JSON_PARSE_ERRORS:
        return False
    return (
        isinstance(value, dict)
        and set(value) == {"layout_version", "store_id", "established"}
        and value.get("layout_version") == LAYOUT_VERSION
        and value.get("store_id") == store_id
        and value.get("established") is True
    )


def _entry_kind(path: Path, *, inspect_ancestors: bool = False) -> str:
    if inspect_ancestors:
        _assert_safe_existing_ancestors(path)
    try:
        details = path.lstat()
    except FileNotFoundError:
        return "absent"
    if stat.S_ISLNK(details.st_mode) or _is_reparse(details):
        raise _UnsafeFilesystemState
    if stat.S_ISREG(details.st_mode):
        return "file"
    if stat.S_ISDIR(details.st_mode):
        return "directory"
    raise _UnsafeFilesystemState


def _assert_safe_existing_ancestors(path: Path) -> None:
    current = path.parent
    ancestors: list[Path] = []
    while current != current.parent:
        ancestors.append(current)
        current = current.parent
    for ancestor in reversed(ancestors):
        try:
            details = ancestor.lstat()
        except FileNotFoundError:
            continue
        if not stat.S_ISDIR(details.st_mode) or stat.S_ISLNK(details.st_mode) or _is_reparse(details):
            raise _UnsafeFilesystemState


def _is_reparse(details: os.stat_result) -> bool:
    attributes = getattr(details, "st_file_attributes", 0)
    flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(attributes & flag)


def _read_file_bytes(path: Path) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        details = os.fstat(descriptor)
        if not stat.S_ISREG(details.st_mode):
            raise _UnsafeFilesystemState
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _read_snapshot(path: Path, store_id: str) -> _Snapshot:
    if store_id != "conversation":
        return _Snapshot(kind="file", file_bytes=_read_file_bytes(path))
    entries: list[tuple[str, bytes]] = []
    with os.scandir(path) as iterator:
        selected = sorted(iterator, key=lambda entry: entry.name)
    for entry in selected:
        try:
            details = entry.stat(follow_symlinks=False)
        except OSError:
            raise _UnsafeFilesystemState from None
        if entry.is_symlink() or _is_reparse(details):
            raise _UnsafeFilesystemState
        if not stat.S_ISREG(details.st_mode):
            entries.append((entry.name + "/", b""))
            continue
        entries.append((entry.name, _read_file_bytes(Path(entry.path))))
    return _Snapshot(kind="directory", entries=tuple(entries))


def _validate_snapshot(store_id: str, snapshot: _Snapshot) -> str:
    if store_id == "conversation":
        return _validate_conversation(snapshot.entries)
    assert snapshot.file_bytes is not None
    try:
        value = json.loads(snapshot.file_bytes.decode("utf-8"))
    except _JSON_PARSE_ERRORS:
        return "corrupt"
    if not isinstance(value, dict):
        return "corrupt"
    if store_id == "memory":
        version = value.get("version")
        if not isinstance(version, str) or not version:
            return "corrupt"
        if version != "0.1":
            return "unsupported_version"
        return "valid" if isinstance(value.get("items"), list) else "corrupt"
    if store_id == "profile":
        return "valid"
    if store_id == "ideas":
        return "valid" if "ideas" not in value or isinstance(value["ideas"], list) else "corrupt"
    if store_id == "vosk_settings":
        model_path = value.get("model_path", None)
        if "model_path" in value and model_path is not None:
            if not isinstance(model_path, str) or not model_path.strip():
                return "corrupt"
        if "language" in value:
            language = value["language"]
            if not isinstance(language, str) or not language.strip():
                return "corrupt"
        return "valid"
    raise ValueError("unsupported_store_id")


def _validate_conversation(entries: tuple[tuple[str, bytes], ...]) -> str:
    found_unsupported = False
    for name, payload in entries:
        if name.endswith("/") or not name.endswith(".json"):
            return "corrupt"
        session_id = name[:-5]
        if not session_id or _SESSION_ID.fullmatch(session_id) is None:
            return "corrupt"
        try:
            value = json.loads(payload.decode("utf-8"))
        except _JSON_PARSE_ERRORS:
            return "corrupt"
        structural = _validate_session_envelope(value, session_id)
        if structural == "corrupt":
            return "corrupt"
        if structural == "unsupported_version":
            found_unsupported = True
    return "unsupported_version" if found_unsupported else "valid"


def _validate_session_envelope(value: object, filename_session_id: str) -> str:
    if not isinstance(value, dict) or set(value) != _SESSION_KEYS:
        return "corrupt"
    session_id = value.get("session_id")
    if (
        not isinstance(session_id, str)
        or not session_id
        or _SESSION_ID.fullmatch(session_id) is None
        or session_id != filename_session_id
    ):
        return "corrupt"
    schema_version = value.get("schema_version")
    if not _is_int(schema_version) or schema_version <= 0:
        return "corrupt"
    if schema_version != 1:
        return "unsupported_version"
    if value.get("status") not in {"active", "closed"}:
        return "corrupt"
    if not _nonempty_string(value.get("created_at")) or not _nonempty_string(value.get("updated_at")):
        return "corrupt"
    if not _is_int(value.get("turn_count")) or value["turn_count"] < 0:
        return "corrupt"
    if not _is_int(value.get("revision")) or value["revision"] < 1:
        return "corrupt"
    turns = value.get("turns")
    if not isinstance(turns, list) or value["turn_count"] != len(turns):
        return "corrupt"
    for index, turn in enumerate(turns, start=1):
        if not _valid_turn(turn, index):
            return "corrupt"
    expected_last = None if not turns else turns[-1]["turn_id"]
    if value.get("last_turn_id") != expected_last:
        return "corrupt"
    return "valid"


def _valid_turn(value: object, sequence: int) -> bool:
    if not isinstance(value, dict) or set(value) != _TURN_KEYS:
        return False
    if not _nonempty_string(value.get("turn_id")):
        return False
    if not _is_int(value.get("sequence")) or value["sequence"] != sequence:
        return False
    if value.get("role") not in {"user", "assistant"}:
        return False
    source = value.get("source_classification")
    if not isinstance(source, str) or _SOURCE_CLASSIFICATION.fullmatch(source) is None:
        return False
    if not _nonempty_string(value.get("created_at")):
        return False
    summary = value.get("summary_text")
    if not isinstance(summary, str) or not summary or len(summary) > 160:
        return False
    if value.get("content_classification") not in {
        "bounded_redacted_summary",
        "redacted_sensitive_content",
    }:
        return False
    reason = value.get("redaction_reason")
    return reason is None or _nonempty_string(reason)


def _nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value)


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _ensure_safe_parent_directories(root: Path, target: Path) -> None:
    try:
        relative = target.relative_to(root)
    except ValueError:
        raise _UnsafeFilesystemState from None
    _ensure_safe_directory_tree(root)
    current = root
    for part in relative.parts:
        current = current / part
        _assert_safe_existing_ancestors(current)
        kind = _entry_kind(current)
        if kind == "absent":
            try:
                current.mkdir()
            except FileExistsError:
                pass
            kind = _entry_kind(current)
        if kind != "directory":
            raise _UnsafeFilesystemState


def _ensure_safe_directory_tree(directory: Path) -> None:
    """Create one authorized directory path without following existing links."""

    _assert_safe_existing_ancestors(directory)
    missing: list[Path] = []
    current = directory
    kind = _entry_kind(current)
    while kind == "absent":
        missing.append(current)
        parent = current.parent
        if parent == current:
            raise _UnsafeFilesystemState
        current = parent
        kind = _entry_kind(current)
    if kind != "directory":
        raise _UnsafeFilesystemState

    for candidate in reversed(missing):
        _assert_safe_existing_ancestors(candidate)
        kind = _entry_kind(candidate)
        if kind == "absent":
            try:
                candidate.mkdir()
            except FileExistsError:
                pass
            kind = _entry_kind(candidate)
        if kind != "directory":
            raise _UnsafeFilesystemState
