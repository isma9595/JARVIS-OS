"""Encrypted local API key storage foundation.

The default persistent backend uses Windows DPAPI through ctypes. If DPAPI is
not available, persistent storage stays unavailable instead of writing secrets
as plain text.
"""

from __future__ import annotations

import base64
import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from typing import Protocol


DEFAULT_SECRET_NAME = "api_key"


@dataclass(frozen=True)
class SecureKeyStoreStatus:
    available: bool
    backend_name: str
    persistent: bool
    encrypted_at_rest: bool
    storage_path: str | None
    safe_to_store: bool
    detail_ru: str


@dataclass(frozen=True)
class SecureKeyRecord:
    provider: str
    secret_name: str
    present: bool
    masked_hint: str | None
    source: str
    updated_at: str | None


class _SecureKeyBackend(Protocol):
    def status(self) -> SecureKeyStoreStatus:
        ...

    def read_entries(self) -> dict[str, dict[str, str]]:
        ...

    def write_entries(self, entries: dict[str, dict[str, str]]) -> None:
        ...

    def encrypt(self, value: str) -> str:
        ...

    def decrypt(self, encrypted_value: str) -> str:
        ...


class SecureKeyStore:
    """Provider/secret-name key store with encrypted-at-rest backends."""

    def __init__(self, backend: _SecureKeyBackend | None = None):
        self._backend = backend or _default_backend()

    def status(self) -> SecureKeyStoreStatus:
        return self._backend.status()

    def has_secret(self, provider: str, secret_name: str = DEFAULT_SECRET_NAME) -> bool:
        key = self._entry_key(provider, secret_name)
        return key in self._backend.read_entries()

    def set_secret(
        self,
        provider: str,
        value: str,
        secret_name: str = DEFAULT_SECRET_NAME,
    ) -> None:
        status = self.status()
        if not status.safe_to_store:
            raise RuntimeError(status.detail_ru)
        normalized_provider = self._normalize_part(provider, "provider")
        normalized_secret_name = self._normalize_part(secret_name, "secret_name")
        if not value:
            raise ValueError("Secret value is empty.")

        entries = self._backend.read_entries()
        entries[self._entry_key(normalized_provider, normalized_secret_name)] = {
            "provider": normalized_provider,
            "secret_name": normalized_secret_name,
            "encrypted_value": self._backend.encrypt(value),
            "masked_hint": self._masked_hint(value),
            "source": "stored",
            "updated_at": self._now_iso(),
        }
        self._backend.write_entries(entries)

    def delete_secret(
        self,
        provider: str,
        secret_name: str = DEFAULT_SECRET_NAME,
    ) -> bool:
        key = self._entry_key(provider, secret_name)
        entries = self._backend.read_entries()
        if key not in entries:
            return False
        del entries[key]
        self._backend.write_entries(entries)
        return True

    def list_records(self) -> list[SecureKeyRecord]:
        records = []
        for entry in sorted(
            self._backend.read_entries().values(),
            key=lambda item: (item.get("provider", ""), item.get("secret_name", "")),
        ):
            records.append(
                SecureKeyRecord(
                    provider=str(entry.get("provider", "")),
                    secret_name=str(entry.get("secret_name", DEFAULT_SECRET_NAME)),
                    present=True,
                    masked_hint=self._safe_stored_hint(entry.get("masked_hint")),
                    source=str(entry.get("source", "stored")),
                    updated_at=entry.get("updated_at"),
                )
            )
        return records

    def get_secret(
        self,
        provider: str,
        secret_name: str = DEFAULT_SECRET_NAME,
    ) -> str | None:
        """Return decrypted secret for internal use only; never print this."""

        entry = self._backend.read_entries().get(self._entry_key(provider, secret_name))
        if entry is None:
            return None
        return self._backend.decrypt(str(entry.get("encrypted_value", "")))

    @classmethod
    def _entry_key(cls, provider: str, secret_name: str) -> str:
        return f"{cls._normalize_part(provider, 'provider')}::{cls._normalize_part(secret_name, 'secret_name')}"

    @staticmethod
    def _normalize_part(value: str, field_name: str) -> str:
        normalized = str(value or "").strip().lower()
        if not normalized:
            raise ValueError(f"{field_name} is required.")
        if not all(char.isalnum() or char in {"_", "-"} for char in normalized):
            raise ValueError(f"{field_name} contains unsupported characters.")
        return normalized

    @staticmethod
    def _masked_hint(value: str) -> str:
        tail = str(value)[-4:] if value else ""
        return f"***{tail}" if tail else "***"

    @staticmethod
    def _safe_stored_hint(value: object) -> str | None:
        if not value:
            return None
        text = str(value)
        if not text.startswith("***"):
            return None
        tail = text[3:]
        if len(tail) > 4:
            return "***" + tail[-4:]
        return text

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class UnavailableSecureKeyBackend:
    def __init__(self, detail_ru: str = "Защищенное хранилище недоступно."):
        self._detail_ru = detail_ru

    def status(self) -> SecureKeyStoreStatus:
        return SecureKeyStoreStatus(
            available=False,
            backend_name="unavailable",
            persistent=False,
            encrypted_at_rest=False,
            storage_path=None,
            safe_to_store=False,
            detail_ru=self._detail_ru,
        )

    def read_entries(self) -> dict[str, dict[str, str]]:
        return {}

    def write_entries(self, entries: dict[str, dict[str, str]]) -> None:
        raise RuntimeError(self._detail_ru)

    def encrypt(self, value: str) -> str:
        raise RuntimeError(self._detail_ru)

    def decrypt(self, encrypted_value: str) -> str:
        raise RuntimeError(self._detail_ru)


class MemorySecureKeyBackend:
    """Test-only encrypted-at-rest fake. It is not persistent."""

    def __init__(self):
        self._entries: dict[str, dict[str, str]] = {}

    def status(self) -> SecureKeyStoreStatus:
        return SecureKeyStoreStatus(
            available=True,
            backend_name="memory-test",
            persistent=False,
            encrypted_at_rest=True,
            storage_path=None,
            safe_to_store=True,
            detail_ru="Тестовое in-memory хранилище доступно.",
        )

    def read_entries(self) -> dict[str, dict[str, str]]:
        return json.loads(json.dumps(self._entries))

    def write_entries(self, entries: dict[str, dict[str, str]]) -> None:
        self._entries = json.loads(json.dumps(entries))

    def encrypt(self, value: str) -> str:
        payload = str(value).encode("utf-8")
        return "mem:" + base64.b64encode(payload[::-1]).decode("ascii")

    def decrypt(self, encrypted_value: str) -> str:
        if not str(encrypted_value).startswith("mem:"):
            raise ValueError("Unsupported test payload.")
        payload = base64.b64decode(str(encrypted_value)[4:].encode("ascii"))[::-1]
        return payload.decode("utf-8")


class WindowsDpapiSecureKeyBackend:
    def __init__(self, storage_path: Path | None = None):
        self.storage_path = storage_path or _default_storage_path()

    def status(self) -> SecureKeyStoreStatus:
        available = sys.platform.startswith("win") and hasattr(ctypes, "windll")
        return SecureKeyStoreStatus(
            available=available,
            backend_name="windows-dpapi" if available else "unavailable",
            persistent=available,
            encrypted_at_rest=available,
            storage_path=str(self.storage_path) if available else None,
            safe_to_store=available,
            detail_ru=(
                "Windows DPAPI доступен; секреты шифруются для текущего пользователя."
                if available
                else "Windows DPAPI недоступен; plain-text fallback отключен."
            ),
        )

    def read_entries(self) -> dict[str, dict[str, str]]:
        if not self.storage_path.exists():
            return {}
        with self.storage_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        entries = payload.get("entries", {})
        return entries if isinstance(entries, dict) else {}

    def write_entries(self, entries: dict[str, dict[str, str]]) -> None:
        status = self.status()
        if not status.safe_to_store:
            raise RuntimeError(status.detail_ru)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.storage_path.with_suffix(self.storage_path.suffix + ".tmp")
        payload = {
            "version": 1,
            "backend": "windows-dpapi",
            "entries": entries,
        }
        with temp_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temp_path, self.storage_path)

    def encrypt(self, value: str) -> str:
        blob = _dpapi_crypt_protect_data(str(value).encode("utf-8"))
        return "dpapi:" + base64.b64encode(blob).decode("ascii")

    def decrypt(self, encrypted_value: str) -> str:
        text = str(encrypted_value)
        if not text.startswith("dpapi:"):
            raise ValueError("Unsupported encrypted payload.")
        blob = base64.b64decode(text[6:].encode("ascii"))
        return _dpapi_crypt_unprotect_data(blob).decode("utf-8")


class _DataBlob(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_byte)),
    ]


def _dpapi_crypt_protect_data(data: bytes) -> bytes:
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    input_buffer = ctypes.create_string_buffer(data)
    input_blob = _DataBlob(len(data), ctypes.cast(input_buffer, ctypes.POINTER(ctypes.c_byte)))
    output_blob = _DataBlob()
    if not crypt32.CryptProtectData(
        ctypes.byref(input_blob),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(output_blob),
    ):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(output_blob.pbData, output_blob.cbData)
    finally:
        kernel32.LocalFree(output_blob.pbData)


def _dpapi_crypt_unprotect_data(data: bytes) -> bytes:
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    input_buffer = ctypes.create_string_buffer(data)
    input_blob = _DataBlob(len(data), ctypes.cast(input_buffer, ctypes.POINTER(ctypes.c_byte)))
    output_blob = _DataBlob()
    if not crypt32.CryptUnprotectData(
        ctypes.byref(input_blob),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(output_blob),
    ):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(output_blob.pbData, output_blob.cbData)
    finally:
        kernel32.LocalFree(output_blob.pbData)


def _default_backend() -> _SecureKeyBackend:
    backend = WindowsDpapiSecureKeyBackend()
    if backend.status().safe_to_store:
        return backend
    return UnavailableSecureKeyBackend(backend.status().detail_ru)


def _default_storage_path() -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "JARVIS-OS" / "secure_keys.json"
    return Path.home() / "AppData" / "Roaming" / "JARVIS-OS" / "secure_keys.json"
