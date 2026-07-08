from core.action_router import SafeActionRouter
from core.command_processor import CommandProcessor
from core.event_bus import EventBus
from core.exceptions import KernelError
from core.kernel import JARVISKernel
from core.logger import Logger
from core.module_manager import ModuleManager
from dialogue import DialogueManager
from ideas import IdeaManager
from memory import LocalMemoryManager
from voice import MicrophoneInputAdapter, VoiceInputManager


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
    assert isinstance(kernel.command_processor, CommandProcessor)
    assert isinstance(kernel.action_router, SafeActionRouter)
    assert isinstance(kernel.idea_manager, IdeaManager)
    assert isinstance(kernel.memory_manager, LocalMemoryManager)
    assert isinstance(kernel.microphone_input_adapter, MicrophoneInputAdapter)
    assert isinstance(kernel.voice_input_manager, VoiceInputManager)
    assert isinstance(kernel.dialogue, DialogueManager)


def test_get_service_logger():
    kernel = JARVISKernel()

    assert kernel.get_service("logger") is kernel.logger


def test_get_service_event_bus():
    kernel = JARVISKernel()

    assert kernel.get_service("event_bus") is kernel.event_bus


def test_get_service_module_manager():
    kernel = JARVISKernel()

    assert kernel.get_service("module_manager") is kernel.module_manager


def test_get_service_command_processor():
    kernel = JARVISKernel()

    assert kernel.get_service("command_processor") is kernel.command_processor


def test_get_service_action_router():
    kernel = JARVISKernel()

    assert kernel.get_service("action_router") is kernel.action_router


def test_get_service_idea_manager():
    kernel = JARVISKernel()

    assert kernel.get_service("idea_manager") is kernel.idea_manager


def test_get_service_memory_manager():
    kernel = JARVISKernel()

    assert kernel.get_service("memory_manager") is kernel.memory_manager


def test_get_service_voice_input_manager():
    kernel = JARVISKernel()

    assert kernel.get_service("voice_input_manager") is kernel.voice_input_manager


def test_get_service_microphone_input_adapter():
    kernel = JARVISKernel()

    assert (
        kernel.get_service("microphone_input_adapter")
        is kernel.microphone_input_adapter
    )


def test_get_version():
    kernel = JARVISKernel()

    assert kernel.get_version() == "0.2"


def test_get_state():
    kernel = JARVISKernel()

    assert kernel.get_state() == "created"


def test_list_services():
    kernel = JARVISKernel()

    assert kernel.list_services() == [
        "logger",
        "event_bus",
        "module_manager",
        "command_processor",
        "action_router",
        "idea_manager",
        "memory_manager",
        "microphone_input_adapter",
        "voice_input_manager",
    ]


def test_get_system_status():
    kernel = JARVISKernel()

    assert kernel.get_system_status() == {
        "version": "0.2",
        "state": "created",
        "services": [
            "logger",
            "event_bus",
            "module_manager",
            "command_processor",
            "action_router",
            "idea_manager",
            "memory_manager",
            "microphone_input_adapter",
            "voice_input_manager",
        ],
    }


def test_existing_services_are_available_through_get_service():
    kernel = JARVISKernel()

    for service_name in kernel.list_services():
        assert kernel.get_service(service_name) is kernel.services[service_name]


def test_command_processor_uses_kernel_memory_manager():
    kernel = JARVISKernel()

    assert kernel.command_processor.memory_manager is kernel.memory_manager


def test_command_processor_uses_kernel_system_status():
    kernel = JARVISKernel()

    result = kernel.command_processor.process("статус системы")

    assert result["intent"] == "system.status"
    assert "Активных сервисов: 9" in result["response"]


def test_voice_input_manager_uses_kernel_services():
    kernel = JARVISKernel()

    assert kernel.voice_input_manager.command_processor is kernel.command_processor
    assert kernel.voice_input_manager.dialogue_manager is kernel.dialogue
    assert (
        kernel.voice_input_manager.microphone_adapter
        is kernel.microphone_input_adapter
    )


def test_command_processor_is_linked_to_voice_input_manager():
    kernel = JARVISKernel()

    assert kernel.command_processor.voice_input_manager is kernel.voice_input_manager


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
    test_get_service_command_processor()
    test_get_service_action_router()
    test_get_service_idea_manager()
    test_get_service_memory_manager()
    test_get_service_microphone_input_adapter()
    test_get_service_voice_input_manager()
    test_get_version()
    test_get_state()
    test_list_services()
    test_get_system_status()
    test_existing_services_are_available_through_get_service()
    test_command_processor_uses_kernel_memory_manager()
    test_command_processor_uses_kernel_system_status()
    test_voice_input_manager_uses_kernel_services()
    test_command_processor_is_linked_to_voice_input_manager()
    test_get_unknown_service_error()
    test_start()
    test_repeated_start_error()
    test_shutdown()
    test_repeated_shutdown()
    test_kernel_started_event()
    test_kernel_stopped_event()


if __name__ == "__main__":
    run_tests()
