"""Small thread-safe lazy initialization boundary."""

from __future__ import annotations

from dataclasses import dataclass, fields
from enum import Enum
from threading import Lock
from typing import Callable, Generic, TypeVar


T = TypeVar("T")


class LazyComponentState(str, Enum):
    DEFERRED = "deferred"
    INITIALIZING = "initializing"
    READY = "ready"
    FAILED = "failed"


@dataclass(frozen=True)
class LazyComponentSnapshot:
    component_id: str
    state: str
    initialization_count: int
    initialized: bool
    error_code: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {field.name: getattr(self, field.name) for field in fields(self)}


class LazyInitializationError(RuntimeError):
    """Safe typed failure raised when a lazy factory cannot initialize."""

    def __init__(self, component_id: str, error_code: str):
        self.component_id = component_id
        self.error_code = error_code
        super().__init__(f"Lazy component {component_id} failed: {error_code}")


class LazyComponent(Generic[T]):
    """Initialize one optional component on first explicit access."""

    def __init__(
        self,
        component_id: str,
        factory: Callable[[], T],
        *,
        failure_error_code: str = "initialization_failed",
    ):
        self.component_id = self._safe_component_id(component_id)
        self._factory = factory
        self._failure_error_code = self._safe_error_code(failure_error_code)
        self._state = LazyComponentState.DEFERRED
        self._instance: T | None = None
        self._initialization_count = 0
        self._error_code: str | None = None
        self._lock = Lock()

    def get(self) -> T:
        if self._state == LazyComponentState.READY:
            return self._instance  # type: ignore[return-value]

        with self._lock:
            if self._state == LazyComponentState.READY:
                return self._instance  # type: ignore[return-value]
            if self._state == LazyComponentState.FAILED:
                raise LazyInitializationError(
                    self.component_id,
                    self._error_code or self._failure_error_code,
                )

            self._state = LazyComponentState.INITIALIZING
            self._initialization_count += 1
            try:
                instance = self._factory()
            except Exception:
                self._instance = None
                self._state = LazyComponentState.FAILED
                self._error_code = self._failure_error_code
                raise LazyInitializationError(
                    self.component_id,
                    self._failure_error_code,
                ) from None

            self._instance = instance
            self._state = LazyComponentState.READY
            self._error_code = None
            return instance

    def snapshot(self) -> LazyComponentSnapshot:
        return LazyComponentSnapshot(
            component_id=self.component_id,
            state=self._state.value,
            initialization_count=self._initialization_count,
            initialized=self._state == LazyComponentState.READY,
            error_code=self._error_code,
        )

    def __getattr__(self, name: str):
        return getattr(self.get(), name)

    @staticmethod
    def _safe_component_id(component_id: str) -> str:
        safe = str(component_id or "component").strip().lower().replace(" ", "_")
        return "".join(ch for ch in safe if ch.isalnum() or ch in {"_", "-", "."})[:80]

    @staticmethod
    def _safe_error_code(error_code: str) -> str:
        safe = str(error_code or "initialization_failed").strip().lower().replace(" ", "_")
        return "".join(ch for ch in safe if ch.isalnum() or ch in {"_", "-"})[:80]
