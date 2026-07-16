import dataclasses
import json

import pytest

from app.startup_profiler import StartupProfiler
from core.lazy_component import LazyComponentSnapshot


class FakeClock:
    def __init__(self, values):
        self.values = list(values)

    def __call__(self):
        return self.values.pop(0)


def test_profiler_uses_injectable_monotonic_clock_and_preserves_phase_order():
    clock = FakeClock([10.0, 10.1, 10.4, 10.5, 10.45, 10.8])
    profiler = StartupProfiler(clock=clock)

    with profiler.phase("first", "First phase"):
        pass
    with profiler.phase("second", "Second phase"):
        pass
    profiler.complete()

    snapshot = profiler.snapshot(eager_components=("policy",))

    assert [phase.phase_id for phase in snapshot.phases] == ["first", "second"]
    assert snapshot.phases[0].duration_ms == pytest.approx(300.0)
    assert snapshot.phases[1].duration_ms == 0.0
    assert snapshot.total_duration_ms == pytest.approx(800.0)
    assert snapshot.startup_completed is True
    assert snapshot.eager_components == ("policy",)


def test_profile_snapshot_is_immutable_and_serializable_and_redacts_message():
    profiler = StartupProfiler(clock=FakeClock([1.0, 1.0]))
    profiler.complete()

    snapshot = profiler.snapshot(
        deferred_components=(
            LazyComponentSnapshot(
                component_id="provider",
                state="deferred",
                initialization_count=0,
                initialized=False,
            ),
        ),
        message="api_key sk-test-1234567890secret failed",
    )

    assert dataclasses.is_dataclass(snapshot)
    assert snapshot.message == "[REDACTED]"
    rendered = json.dumps(snapshot.to_dict(), sort_keys=True)
    assert "sk-test-1234567890secret" not in rendered
    assert "provider" in rendered
    try:
        snapshot.total_duration_ms = 1
    except dataclasses.FrozenInstanceError:
        pass
    else:
        raise AssertionError("snapshot must be immutable")
