"""Read-only, privacy-safe persistence health projection."""

from __future__ import annotations

import base64
from collections.abc import Callable, Mapping
import json
from pathlib import Path
from typing import Any

from app.app_contracts import AppPersistenceHealthSnapshot, AppPersistenceStoreHealth
from platform_adapters.user_data_migration import (
    LAYOUT_VERSION,
    ORDINARY_STORE_IDS,
    DeterministicLegacyRegistry,
    _UnsafeFilesystemState,
    _entry_kind,
    _read_file_bytes,
    _read_snapshot,
    _validate_snapshot,
    _valid_receipt,
)
from platform_adapters.user_data_paths import UserDataPaths


PERSISTENCE_STORE_IDS = (*ORDINARY_STORE_IDS, "secure_keys")
_JSON_PARSE_ERRORS = (
    UnicodeDecodeError,
    json.JSONDecodeError,
    ValueError,
    RecursionError,
)
_CANONICAL_ATTRIBUTE = {
    "conversation": "conversation_sessions",
    "memory": "memory",
    "profile": "profile",
    "ideas": "ideas",
    "vosk_settings": "vosk_settings",
}


class PersistenceHealthService:
    """Recompute an advisory snapshot without mutating persistence state."""

    def __init__(
        self,
        paths: UserDataPaths,
        registry: DeterministicLegacyRegistry,
        *,
        external_overrides: Mapping[str, Path] | None = None,
        secure_keys_path: Path | None = None,
        secure_keys_backend_available: bool = False,
        after_receipt_observation: Callable[[str, bool], None] | None = None,
    ) -> None:
        unknown = set(external_overrides or {}).difference(ORDINARY_STORE_IDS)
        if unknown:
            raise ValueError("unsupported_store_id")
        self._paths = paths
        self._registry = registry
        self._external_overrides = dict(external_overrides or {})
        self._secure_keys_path = secure_keys_path
        self._secure_keys_backend_available = bool(secure_keys_backend_available)
        self._after_receipt_observation = after_receipt_observation

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(layout_version={LAYOUT_VERSION!r}, "
            f"external_override_count={len(self._external_overrides)!r})"
        )

    def snapshot(self) -> AppPersistenceHealthSnapshot:
        stores = [self._ordinary_store(store_id) for store_id in ORDINARY_STORE_IDS]
        stores.append(self._secure_keys())
        return AppPersistenceHealthSnapshot(
            layout_version=LAYOUT_VERSION,
            stores=tuple(stores),
        )

    def _ordinary_store(self, store_id: str) -> AppPersistenceStoreHealth:
        if store_id in self._external_overrides:
            return self._external_override(store_id)

        receipt_path = self._receipt_path(store_id)
        receipt_present = False
        try:
            receipt_kind = _entry_kind(receipt_path, inspect_ancestors=True)
            receipt_present = receipt_kind != "absent"
            if receipt_present:
                result = self._receipt_branch(store_id, receipt_path, receipt_kind)
            else:
                result = self._pre_receipt_branch(store_id)
        except (OSError, _UnsafeFilesystemState):
            result = self._health(store_id, "unavailable")

        if self._after_receipt_observation is not None:
            self._after_receipt_observation(store_id, receipt_present)
        return result

    def _receipt_branch(
        self,
        store_id: str,
        receipt_path: Path,
        receipt_kind: str,
    ) -> AppPersistenceStoreHealth:
        if receipt_kind != "file":
            raise _UnsafeFilesystemState
        if not _valid_receipt(_read_file_bytes(receipt_path), store_id):
            return self._health(store_id, "migration_state_invalid")
        canonical = self._canonical_path(store_id)
        expected = "directory" if store_id == "conversation" else "file"
        canonical_kind = _entry_kind(canonical, inspect_ancestors=True)
        if canonical_kind == "absent":
            return self._health(store_id, "migration_state_invalid")
        if canonical_kind != expected:
            raise _UnsafeFilesystemState
        return self._validated_health(store_id, _read_snapshot(canonical, store_id))

    def _pre_receipt_branch(self, store_id: str) -> AppPersistenceStoreHealth:
        canonical = self._canonical_path(store_id)
        expected = "directory" if store_id == "conversation" else "file"
        canonical_kind = _entry_kind(canonical, inspect_ancestors=True)
        if canonical_kind not in {"absent", expected}:
            raise _UnsafeFilesystemState
        canonical_snapshot = None
        if canonical_kind != "absent":
            canonical_snapshot = _read_snapshot(canonical, store_id)
            canonical_health = self._validated_health(store_id, canonical_snapshot)
            if canonical_health.code != "ready":
                return canonical_health

        candidates: list[Path] = []
        for candidate in self._registry.candidates_for(store_id):
            kind = _entry_kind(candidate, inspect_ancestors=True)
            if kind == "absent":
                continue
            if kind != expected:
                raise _UnsafeFilesystemState
            candidates.append(candidate)
        if len(candidates) > 1:
            return self._health(store_id, "multiple_legacy_sources")
        if not candidates:
            return self._health(
                store_id,
                "not_initialized" if canonical_snapshot is None else "ready",
            )

        legacy_snapshot = _read_snapshot(candidates[0], store_id)
        legacy_health = self._validated_health(store_id, legacy_snapshot)
        if legacy_health.code != "ready":
            return legacy_health
        if canonical_snapshot is None:
            return self._health(store_id, "migration_required")
        if canonical_snapshot != legacy_snapshot:
            return self._health(store_id, "canonical_legacy_conflict")
        return self._health(store_id, "ready")

    def _external_override(self, store_id: str) -> AppPersistenceStoreHealth:
        path = self._external_overrides[store_id]
        expected = "directory" if store_id == "conversation" else "file"
        try:
            kind = _entry_kind(path, inspect_ancestors=True)
            if kind == "absent":
                return self._health(store_id, "missing")
            if kind != expected:
                raise _UnsafeFilesystemState
            return self._validated_health(store_id, _read_snapshot(path, store_id))
        except (OSError, _UnsafeFilesystemState):
            return self._health(store_id, "unavailable")

    def _validated_health(self, store_id: str, snapshot: Any) -> AppPersistenceStoreHealth:
        validity = _validate_snapshot(store_id, snapshot)
        code = "ready" if validity == "valid" else validity
        schema: str | int | None = None
        if code == "ready":
            if store_id == "conversation":
                schema = 1
            elif store_id == "memory":
                schema = "0.1"
        return self._health(store_id, code, schema_version=schema)

    def _secure_keys(self) -> AppPersistenceStoreHealth:
        if not self._secure_keys_backend_available or self._secure_keys_path is None:
            return self._health("secure_keys", "unavailable")
        try:
            kind = _entry_kind(self._secure_keys_path, inspect_ancestors=True)
            if kind == "absent":
                return self._health("secure_keys", "not_initialized")
            if kind != "file":
                raise _UnsafeFilesystemState
            code, count = _validate_secure_keys(_read_file_bytes(self._secure_keys_path))
            return self._health(
                "secure_keys",
                code,
                schema_version=1 if code == "ready" else None,
                item_count=count if code == "ready" else None,
            )
        except (OSError, _UnsafeFilesystemState):
            return self._health("secure_keys", "unavailable")

    def _canonical_path(self, store_id: str) -> Path:
        return getattr(self._paths, _CANONICAL_ATTRIBUTE[store_id])

    def _receipt_path(self, store_id: str) -> Path:
        return self._paths.root / ".migration" / LAYOUT_VERSION / f"{store_id}.json"

    @staticmethod
    def _health(
        store_id: str,
        code: str,
        *,
        schema_version: str | int | None = None,
        item_count: int | None = None,
    ) -> AppPersistenceStoreHealth:
        return AppPersistenceStoreHealth(
            layout_version=LAYOUT_VERSION,
            store_id=store_id,
            code=code,
            schema_version=schema_version,
            item_count=item_count,
        )


def _validate_secure_keys(payload: bytes) -> tuple[str, int | None]:
    try:
        value = json.loads(payload.decode("utf-8"))
    except _JSON_PARSE_ERRORS:
        return "corrupt", None
    if not isinstance(value, dict) or set(value) != {"version", "backend", "entries"}:
        return "corrupt", None
    version = value.get("version")
    if not isinstance(version, int) or isinstance(version, bool) or version <= 0:
        return "corrupt", None
    if version != 1:
        return "unsupported_version", None
    if value.get("backend") != "windows-dpapi" or not isinstance(value.get("entries"), dict):
        return "corrupt", None
    entries = value["entries"]
    for key, entry in entries.items():
        if not _valid_secure_entry(key, entry):
            return "corrupt", None
    return "ready", len(entries)


def _valid_secure_entry(key: object, entry: object) -> bool:
    required = {
        "provider",
        "secret_name",
        "encrypted_value",
        "masked_hint",
        "source",
        "updated_at",
    }
    if not isinstance(key, str) or not isinstance(entry, dict) or set(entry) != required:
        return False
    provider = entry.get("provider")
    secret_name = entry.get("secret_name")
    if not _normalized_secure_part(provider) or not _normalized_secure_part(secret_name):
        return False
    if key != f"{provider}::{secret_name}":
        return False
    encrypted = entry.get("encrypted_value")
    if not isinstance(encrypted, str) or not encrypted.startswith("dpapi:"):
        return False
    encoded = encrypted[6:]
    if not encoded:
        return False
    try:
        if not base64.b64decode(encoded, validate=True):
            return False
    except (ValueError, base64.binascii.Error):
        return False
    hint = entry.get("masked_hint")
    if not isinstance(hint, str) or not hint.startswith("***") or len(hint) > 7:
        return False
    return entry.get("source") == "stored" and _nonempty_string(entry.get("updated_at"))


def _normalized_secure_part(value: object) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and value == value.strip().lower()
        and all(character.isalnum() or character in {"_", "-"} for character in value)
    )


def _nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value)
