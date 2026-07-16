"""Typed in-memory execution journal for AppService operations.

The journal stores redacted metadata only. It intentionally does not persist
operations; durable workflow history is deferred until workflow contracts
stabilize.
"""

from __future__ import annotations

from collections import OrderedDict, deque
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from threading import RLock
from types import MappingProxyType
from typing import Any, Mapping
import re


class ExecutionStatus(Enum):
    CREATED = "created"
    AWAITING_CLARIFICATION = "awaiting_clarification"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DENIED = "denied"
    DUPLICATE_SUPPRESSED = "duplicate_suppressed"


TERMINAL_EXECUTION_STATUSES = {
    ExecutionStatus.SUCCEEDED,
    ExecutionStatus.FAILED,
    ExecutionStatus.CANCELLED,
    ExecutionStatus.DENIED,
    ExecutionStatus.DUPLICATE_SUPPRESSED,
}


_SECRET_PATTERN = re.compile(
    r"(?i)(sk-[a-z0-9_-]{8,}|api[_ -]?key\s*[:=]?\s*\S+|authorization\s*:\s*\S+|bearer\s+\S+|token\s*[:=]?\s*\S+)"
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def safe_journal_text(value: Any, *, max_length: int = 160) -> str:
    text = _SECRET_PATTERN.sub("[REDACTED]", str(value or ""))
    text = text.replace("\r", " ").replace("\n", " ").strip()
    if len(text) > max_length:
        return text[: max_length - 3].rstrip() + "..."
    return text


def safe_journal_metadata(metadata: Mapping[str, Any] | None) -> Mapping[str, object]:
    if not metadata:
        return MappingProxyType({})
    safe: dict[str, object] = {}
    blocked_keys = {
        "api_key",
        "authorization",
        "authorization_header",
        "client",
        "credentials",
        "document",
        "document_contents",
        "exception",
        "file_contents",
        "gui_object",
        "microphone",
        "provider_client",
        "provider_response",
        "raw_audio",
        "token",
    }
    for key, value in metadata.items():
        key_text = safe_journal_text(key, max_length=64)
        if key_text.lower() in blocked_keys:
            safe[key_text] = "[REDACTED]"
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            safe[key_text] = safe_journal_text(value)
        elif isinstance(value, Enum):
            safe[key_text] = value.value
        elif isinstance(value, (tuple, list)):
            safe[key_text] = tuple(safe_journal_text(item, max_length=80) for item in value[:12])
        else:
            safe[key_text] = safe_journal_text(type(value).__name__)
    return MappingProxyType(safe)


@dataclass(frozen=True)
class ExecutionOperation:
    operation_id: str
    idempotency_key: str
    source: str
    request_fingerprint: str
    status: ExecutionStatus
    created_at: str
    updated_at: str
    command_id: str | None = None
    action_id: str | None = None
    policy_decision: Mapping[str, object] | None = None
    cancellable: bool = True
    duplicate_suppressed: bool = False
    safe_result_summary: str | None = None
    safe_error_code: str | None = None
    metadata: Mapping[str, object] = field(default_factory=lambda: MappingProxyType({}))

    def to_dict(self) -> dict[str, object]:
        return {
            "operation_id": self.operation_id,
            "idempotency_key": self.idempotency_key,
            "source": self.source,
            "command_id": self.command_id,
            "action_id": self.action_id,
            "request_fingerprint": self.request_fingerprint,
            "status": self.status.value,
            "policy_decision": dict(self.policy_decision or {}),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "cancellable": self.cancellable,
            "duplicate_suppressed": self.duplicate_suppressed,
            "safe_result_summary": self.safe_result_summary,
            "safe_error_code": self.safe_error_code,
            "metadata": dict(self.metadata),
        }


class ExecutionJournal:
    """Bounded thread-safe journal exposing immutable snapshots."""

    def __init__(self, max_size: int = 200):
        if max_size < 1:
            raise ValueError("max_size must be positive")
        self.max_size = int(max_size)
        self._lock = RLock()
        self._operations: OrderedDict[str, ExecutionOperation] = OrderedDict()
        self._ids_by_idempotency_key: dict[str, deque[str]] = {}

    def add(self, operation: ExecutionOperation) -> ExecutionOperation:
        with self._lock:
            self._operations[operation.operation_id] = self._copy(operation)
            self._ids_by_idempotency_key.setdefault(
                operation.idempotency_key,
                deque(),
            ).append(operation.operation_id)
            self._trim_locked()
            return self._operations[operation.operation_id]

    def update(self, operation_id: str, **changes: Any) -> ExecutionOperation:
        with self._lock:
            operation = self._operations[operation_id]
            sanitized = self._sanitize_changes(changes)
            updated = replace(operation, updated_at=utc_now_iso(), **sanitized)
            self._operations[operation_id] = self._copy(updated)
            return self._operations[operation_id]

    def get(self, operation_id: str) -> ExecutionOperation | None:
        with self._lock:
            operation = self._operations.get(operation_id)
            return self._copy(operation) if operation is not None else None

    def find_by_idempotency_key(self, idempotency_key: str) -> tuple[ExecutionOperation, ...]:
        with self._lock:
            ids = tuple(self._ids_by_idempotency_key.get(idempotency_key, ()))
            return tuple(
                self._copy(self._operations[operation_id])
                for operation_id in ids
                if operation_id in self._operations
            )

    def recent(self, limit: int | None = None) -> tuple[ExecutionOperation, ...]:
        with self._lock:
            operations = tuple(self._operations.values())
            if limit is not None:
                operations = operations[-max(0, int(limit)) :]
            return tuple(self._copy(operation) for operation in operations)

    def recent_dicts(self, limit: int | None = None) -> tuple[dict[str, object], ...]:
        return tuple(operation.to_dict() for operation in self.recent(limit))

    def _trim_locked(self) -> None:
        while len(self._operations) > self.max_size:
            old_id, old_operation = self._operations.popitem(last=False)
            ids = self._ids_by_idempotency_key.get(old_operation.idempotency_key)
            if ids is not None:
                try:
                    ids.remove(old_id)
                except ValueError:
                    pass
                if not ids:
                    self._ids_by_idempotency_key.pop(old_operation.idempotency_key, None)

    @staticmethod
    def _sanitize_changes(changes: Mapping[str, Any]) -> dict[str, Any]:
        sanitized = dict(changes)
        if "status" in sanitized and isinstance(sanitized["status"], str):
            sanitized["status"] = ExecutionStatus(sanitized["status"])
        if "metadata" in sanitized:
            sanitized["metadata"] = safe_journal_metadata(sanitized["metadata"])
        if "policy_decision" in sanitized and sanitized["policy_decision"] is not None:
            sanitized["policy_decision"] = safe_journal_metadata(sanitized["policy_decision"])
        if "safe_result_summary" in sanitized and sanitized["safe_result_summary"] is not None:
            sanitized["safe_result_summary"] = safe_journal_text(
                sanitized["safe_result_summary"],
                max_length=220,
            )
        if "safe_error_code" in sanitized and sanitized["safe_error_code"] is not None:
            sanitized["safe_error_code"] = safe_journal_text(
                sanitized["safe_error_code"],
                max_length=80,
            )
        return sanitized

    @staticmethod
    def _copy(operation: ExecutionOperation | None) -> ExecutionOperation | None:
        if operation is None:
            return None
        return replace(
            operation,
            policy_decision=MappingProxyType(dict(operation.policy_decision or {})),
            metadata=MappingProxyType(dict(operation.metadata or {})),
        )
