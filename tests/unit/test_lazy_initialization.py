import json
from threading import Thread
import time

import pytest

from core.lazy_component import LazyComponent, LazyComponentState, LazyInitializationError


def test_lazy_factory_is_not_called_during_registration_and_starts_deferred():
    calls = []
    component = LazyComponent("provider", lambda: calls.append("called") or object())

    snapshot = component.snapshot()

    assert calls == []
    assert snapshot.state == LazyComponentState.DEFERRED.value
    assert snapshot.initialized is False
    json.dumps(snapshot.to_dict(), sort_keys=True)


def test_first_access_initializes_once_and_repeated_access_reuses_instance():
    calls = []

    def factory():
        calls.append("called")
        return {"ok": True}

    component = LazyComponent("provider", factory)

    first = component.get()
    second = component.get()
    snapshot = component.snapshot()

    assert first is second
    assert calls == ["called"]
    assert snapshot.state == "ready"
    assert snapshot.initialization_count == 1


def test_concurrent_first_access_does_not_create_duplicate_instances():
    calls = []

    def factory():
        time.sleep(0.02)
        instance = object()
        calls.append(instance)
        return instance

    component = LazyComponent("provider", factory)
    results = []
    threads = [Thread(target=lambda: results.append(component.get())) for _ in range(8)]

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(calls) == 1
    assert len({id(result) for result in results}) == 1
    assert component.snapshot().initialization_count == 1


def test_failed_factory_does_not_publish_partial_instance_and_redacts_error():
    partial = object()

    def factory():
        _ = partial
        raise RuntimeError("api key sk-test-1234567890secret exploded")

    component = LazyComponent(
        "provider",
        factory,
        failure_error_code="provider_initialization_failed",
    )

    with pytest.raises(LazyInitializationError) as exc_info:
        component.get()

    snapshot = component.snapshot()
    assert snapshot.state == "failed"
    assert snapshot.initialized is False
    assert snapshot.initialization_count == 1
    assert snapshot.error_code == "provider_initialization_failed"
    assert exc_info.value.error_code == "provider_initialization_failed"
    assert "sk-test-1234567890secret" not in str(exc_info.value)


def test_inspection_does_not_initialize_component():
    calls = []
    component = LazyComponent("voice", lambda: calls.append("called") or object())

    first = component.snapshot()
    second = component.snapshot()

    assert calls == []
    assert first == second
