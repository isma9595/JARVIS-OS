from core.event_bus import EventBus


def assert_raises(expected_exception, callback):
    try:
        callback()
    except expected_exception:
        return

    raise AssertionError(f"Expected {expected_exception.__name__}")


def test_event_publish():
    bus = EventBus()
    received = []

    bus.subscribe("system.started", lambda data: received.append(data))
    bus.publish("system.started", {"version": "0.2"})

    assert received == [{"version": "0.2"}]


def test_multiple_subscribers():
    bus = EventBus()
    received = []

    bus.subscribe("system.started", lambda data: received.append(("first", data)))
    bus.subscribe("system.started", lambda data: received.append(("second", data)))
    bus.publish("system.started", {"status": "running"})

    assert received == [
        ("first", {"status": "running"}),
        ("second", {"status": "running"}),
    ]


def test_callback_error_does_not_stop_publish():
    bus = EventBus()
    received = []

    def failing_callback(data):
        raise RuntimeError("callback failed")

    bus.subscribe("system.started", failing_callback)
    bus.subscribe("system.started", lambda data: received.append(data))
    bus.publish("system.started", {"status": "running"})

    assert received == [{"status": "running"}]


def test_list_events():
    bus = EventBus()

    bus.subscribe("system.started", lambda data: data)
    bus.subscribe("module.loaded", lambda data: data)

    assert bus.list_events() == ["system.started", "module.loaded"]


def test_callback_validation():
    bus = EventBus()

    assert_raises(TypeError, lambda: bus.subscribe("system.started", None))


def run_tests():
    test_event_publish()
    test_multiple_subscribers()
    test_callback_error_does_not_stop_publish()
    test_list_events()
    test_callback_validation()


if __name__ == "__main__":
    run_tests()
