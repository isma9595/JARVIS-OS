"""Application-level execution coordination for AppService.

The coordinator owns operation registration, idempotency checks, and
cooperative cancellation tokens. It does not execute commands or call policy.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from threading import Event, RLock
from uuid import uuid4

from core.execution_journal import (
    ExecutionJournal,
    ExecutionOperation,
    ExecutionStatus,
    TERMINAL_EXECUTION_STATUSES,
    safe_journal_metadata,
    safe_journal_text,
    utc_now_iso,
)


@dataclass(frozen=True)
class CancellationToken:
    operation_id: str
    _event: Event

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

    def raise_if_cancelled(self) -> None:
        if self.cancelled:
            raise OperationCancelled(self.operation_id)


class OperationCancelled(RuntimeError):
    pass


@dataclass(frozen=True)
class OperationRegistration:
    operation: ExecutionOperation
    token: CancellationToken
    duplicate: bool = False
    conflict: bool = False


class ExecutionCoordinator:
    """Coordinate one AppService operation without executing side effects."""

    def __init__(self, journal: ExecutionJournal | None = None):
        self.journal = journal or ExecutionJournal()
        self._lock = RLock()
        self._tokens: dict[str, Event] = {}

    def create_idempotency_key(self) -> str:
        return "idem-" + uuid4().hex

    def create_request_fingerprint(
        self,
        *,
        source: str,
        text: str,
        command_id: str | None = None,
        action_id: str | None = None,
    ) -> str:
        safe_text = safe_journal_text(text, max_length=240)
        payload = "\n".join(
            (
                str(source or "unknown"),
                str(command_id or ""),
                str(action_id or ""),
                safe_text,
            )
        )
        return "sha256:" + sha256(payload.encode("utf-8")).hexdigest()

    def register(
        self,
        *,
        source: str,
        idempotency_key: str | None,
        request_fingerprint: str,
        command_id: str | None = None,
        action_id: str | None = None,
        metadata: dict[str, object] | None = None,
        operation_id: str | None = None,
    ) -> OperationRegistration:
        with self._lock:
            key = str(idempotency_key or self.create_idempotency_key())
            matches = self.journal.find_by_idempotency_key(key)
            exact_matches = tuple(
                operation
                for operation in matches
                if operation.request_fingerprint == request_fingerprint
                and operation.safe_error_code != "idempotency_conflict"
            )
            if exact_matches:
                existing = exact_matches[-1]
                duplicate = self.journal.update(
                    existing.operation_id,
                    duplicate_suppressed=True,
                )
                return OperationRegistration(
                    operation=duplicate,
                    token=self.token_for(duplicate.operation_id),
                    duplicate=True,
                )
            conflicting_matches = tuple(
                operation
                for operation in matches
                if operation.safe_error_code != "idempotency_conflict"
            )
            if conflicting_matches:
                now = utc_now_iso()
                event = Event()
                conflict_operation = ExecutionOperation(
                    operation_id=operation_id or self._new_operation_id(),
                    idempotency_key=key,
                    source=str(source or "unknown"),
                    command_id=command_id,
                    action_id=action_id,
                    request_fingerprint=request_fingerprint,
                    status=ExecutionStatus.DENIED,
                    policy_decision={
                        "decision": "deny",
                        "reason_codes": ("idempotency_conflict",),
                        "safe_to_execute": False,
                    },
                    created_at=now,
                    updated_at=now,
                    cancellable=False,
                    duplicate_suppressed=False,
                    safe_error_code="idempotency_conflict",
                    metadata=safe_journal_metadata(metadata),
                )
                self._tokens[conflict_operation.operation_id] = event
                added = self.journal.add(conflict_operation)
                return OperationRegistration(
                    operation=added,
                    token=CancellationToken(added.operation_id, event),
                    conflict=True,
                )

            now = utc_now_iso()
            event = Event()
            operation = ExecutionOperation(
                operation_id=operation_id or self._new_operation_id(),
                idempotency_key=key,
                source=str(source or "unknown"),
                command_id=command_id,
                action_id=action_id,
                request_fingerprint=request_fingerprint,
                status=ExecutionStatus.CREATED,
                created_at=now,
                updated_at=now,
                metadata=safe_journal_metadata(metadata),
            )
            self._tokens[operation.operation_id] = event
            added = self.journal.add(operation)
            return OperationRegistration(
                operation=added,
                token=CancellationToken(added.operation_id, event),
            )

    def token_for(self, operation_id: str) -> CancellationToken:
        with self._lock:
            event = self._tokens.setdefault(operation_id, Event())
            return CancellationToken(operation_id, event)

    def cancel(self, operation_id: str, *, reason: str = "cancelled") -> ExecutionOperation | None:
        with self._lock:
            operation = self.journal.get(operation_id)
            if operation is None:
                return None
            event = self._tokens.setdefault(operation_id, Event())
            event.set()
            if operation.status in TERMINAL_EXECUTION_STATUSES:
                return operation
            return self.journal.update(
                operation_id,
                status=ExecutionStatus.CANCELLED,
                cancellable=False,
                safe_error_code=reason,
            )

    def mark_awaiting_clarification(self, operation_id: str) -> ExecutionOperation:
        return self.journal.update(
            operation_id,
            status=ExecutionStatus.AWAITING_CLARIFICATION,
            cancellable=True,
        )

    def mark_awaiting_confirmation(self, operation_id: str) -> ExecutionOperation:
        return self.journal.update(
            operation_id,
            status=ExecutionStatus.AWAITING_CONFIRMATION,
            cancellable=True,
        )

    def mark_running(self, operation_id: str) -> ExecutionOperation:
        return self.journal.update(
            operation_id,
            status=ExecutionStatus.RUNNING,
            cancellable=True,
        )

    def mark_succeeded(self, operation_id: str, *, summary: str | None = None) -> ExecutionOperation:
        return self.journal.update(
            operation_id,
            status=ExecutionStatus.SUCCEEDED,
            cancellable=False,
            safe_result_summary=summary,
        )

    def mark_failed(self, operation_id: str, *, error_code: str) -> ExecutionOperation:
        return self.journal.update(
            operation_id,
            status=ExecutionStatus.FAILED,
            cancellable=False,
            safe_error_code=error_code,
        )

    def mark_denied(
        self,
        operation_id: str,
        *,
        policy_decision: dict[str, object] | None = None,
        error_code: str | None = None,
    ) -> ExecutionOperation:
        return self.journal.update(
            operation_id,
            status=ExecutionStatus.DENIED,
            policy_decision=policy_decision,
            cancellable=False,
            safe_error_code=error_code,
        )

    def set_policy_decision(
        self,
        operation_id: str,
        policy_decision: dict[str, object],
    ) -> ExecutionOperation:
        return self.journal.update(operation_id, policy_decision=policy_decision)

    def recent_operations(self, limit: int | None = None) -> tuple[ExecutionOperation, ...]:
        return self.journal.recent(limit)

    @staticmethod
    def _new_operation_id() -> str:
        return "op-" + uuid4().hex
