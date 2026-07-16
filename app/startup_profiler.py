"""Typed monotonic startup profiling for app composition."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, fields
import time
from typing import Callable, Iterable

from core.lazy_component import LazyComponentSnapshot


Clock = Callable[[], float]


@dataclass(frozen=True)
class StartupPhaseSnapshot:
    phase_id: str
    display_name: str
    duration_ms: float
    succeeded: bool
    error_code: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {field.name: getattr(self, field.name) for field in fields(self)}


@dataclass(frozen=True)
class StartupProfileSnapshot:
    total_duration_ms: float
    phases: tuple[StartupPhaseSnapshot, ...]
    eager_components: tuple[str, ...]
    deferred_components: tuple[LazyComponentSnapshot, ...]
    startup_completed: bool
    message: str

    def to_dict(self) -> dict[str, object]:
        return {
            "total_duration_ms": self.total_duration_ms,
            "phases": [phase.to_dict() for phase in self.phases],
            "eager_components": list(self.eager_components),
            "deferred_components": [
                component.to_dict() for component in self.deferred_components
            ],
            "startup_completed": self.startup_completed,
            "message": self.message,
        }


class StartupProfiler:
    def __init__(self, clock: Clock | None = None):
        self._clock = clock or time.perf_counter
        self._started_at = self._now()
        self._completed_at: float | None = None
        self._phases: list[StartupPhaseSnapshot] = []

    @contextmanager
    def phase(self, phase_id: str, display_name: str):
        started = self._now()
        succeeded = False
        error_code = None
        try:
            yield
            succeeded = True
        except Exception:
            error_code = "phase_failed"
            raise
        finally:
            ended = self._now()
            self._phases.append(
                StartupPhaseSnapshot(
                    phase_id=self._safe_id(phase_id),
                    display_name=self._safe_display_name(display_name),
                    duration_ms=self._duration_ms(started, ended),
                    succeeded=succeeded,
                    error_code=error_code,
                )
            )

    def complete(self) -> None:
        if self._completed_at is None:
            self._completed_at = self._now()

    def snapshot(
        self,
        *,
        eager_components: Iterable[str] = (),
        deferred_components: Iterable[LazyComponentSnapshot] = (),
        message: str = "startup profile available",
    ) -> StartupProfileSnapshot:
        ended = self._completed_at if self._completed_at is not None else self._now()
        return StartupProfileSnapshot(
            total_duration_ms=self._duration_ms(self._started_at, ended),
            phases=tuple(self._phases),
            eager_components=tuple(self._safe_id(component) for component in eager_components),
            deferred_components=tuple(deferred_components),
            startup_completed=self._completed_at is not None,
            message=self._safe_message(message),
        )

    def _now(self) -> float:
        try:
            return float(self._clock())
        except Exception:
            return time.perf_counter()

    @staticmethod
    def _duration_ms(started: float, ended: float) -> float:
        return max(0.0, (ended - started) * 1000.0)

    @staticmethod
    def _safe_id(value: str) -> str:
        safe = str(value or "phase").strip().lower().replace(" ", "_")
        return "".join(ch for ch in safe if ch.isalnum() or ch in {"_", "-", "."})[:80]

    @staticmethod
    def _safe_display_name(value: str) -> str:
        safe = " ".join(str(value or "Startup phase").split())
        return safe[:80]

    @staticmethod
    def _safe_message(value: str) -> str:
        safe = " ".join(str(value or "startup profile available").split())
        for marker in ("sk-", "api_key", "token=", "secret="):
            if marker in safe.lower():
                return "[REDACTED]"
        return safe[:160]
