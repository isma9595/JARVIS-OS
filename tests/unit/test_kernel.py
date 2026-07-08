from core.event_bus import EventBus
from core.exceptions import KernelError
from core.kernel import JARVISKernel
from core.logger import Logger
from core.module_manager import ModuleManager


def assert_raises(expected_exception, callback):
    try:
        callback()
    except expected_exception:
        return

    raise AssertionError(f"Expected {expected_exception.__name__}")


def test_kernel_creation():
    kernel = JARVISKernel()

    assert kernel.version == "0.2"
    assert kernel.state == "created"
    assert kernel.running is False
    assert kernel.get_user_display_name() == "Пользователь"


def test_kernel_user_profile():
    kernel = JARVISKernel(user_profile={"preferred_name": "Исмаил"})

    assert kernel.get_user_display_name() == "Исмаил"


def test_kernel_services_exist():
    kernel = JARVISKernel()

    assert isinstance(kernel.logger, Logger)
    assert isinstance(kernel.event_bus, EventBus)
    assert isinstance(kernel.module_manager, ModuleManager)


def test_get_service_logger():
    kernel = JARVISKernel()

    assert kernel.get_service("logger") is kernel.logger


def test_get_service_event_bus():
    kernel = JARVISKernel()

    assert kernel.get_service("event_bus") is kernel.event_bus


def test_get_service_module_manager():
    kernel = JARVISKernel()

    assert kernel.get_service("module_manager") is kernel.module_manager


def test_get_unknown_service_error():
    kernel = JARVISKernel()

    assert_raises(KernelError, lambda: kernel.get_service("unknown"))


def test_start():
    kernel = JARVISKernel()

    kernel.start()

    assert kernel.state == "running"
    assert kernel.running is True


def test_repeated_start_error():
    kernel = JARVISKernel()

    kernel.start()

    assert_raises(KernelError, kernel.start)
    assert kernel.state == "running"
    assert kernel.running is True


def test_shutdown():
    kernel = JARVISKernel()

    kernel.start()
    kernel.shutdown()

    assert kernel.state == "stopped"
    assert kernel.running is False


def test_repeated_shutdown():
    kernel = JARVISKernel()

    kernel.start()
    kernel.shutdown()
    kernel.shutdown()

    assert kernel.state == "stopped"
    assert kernel.running is False


def test_kernel_started_event():
    kernel = JARVISKernel()
    received = []

    kernel.event_bus.subscribe("kernel.started", lambda data: received.append(data))
    kernel.start()

    assert received == [{"version": "0.2"}]


def test_kernel_stopped_event():
    kernel = JARVISKernel()
    received = []

    kernel.event_bus.subscribe("kernel.stopped", lambda data: received.append(data))
    kernel.start()
    kernel.shutdown()

    assert received == [{"version": "0.2"}]


def run_tests():
    test_kernel_creation()
    test_kernel_user_profile()
    test_kernel_services_exist()
    test_get_service_logger()
    test_get_service_event_bus()
    test_get_service_module_manager()
    test_get_unknown_service_error()
    test_start()
    test_repeated_start_error()
    test_shutdown()
    test_repeated_shutdown()
    test_kernel_started_event()
    test_kernel_stopped_event()


if __name__ == "__main__":
    run_tests()
