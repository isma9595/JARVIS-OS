from core.base_module import BaseModule
from core.module_manager import ModuleManager


def assert_raises(expected_exception, callback):
    try:
        callback()
    except expected_exception:
        return

    raise AssertionError(f"Expected {expected_exception.__name__}")


def create_module(module_id="memory.core.v1", name="Memory Module"):
    return BaseModule(
        module_id=module_id,
        name=name,
        version="0.1",
        description="Memory module for JARVIS OS",
        permissions=["memory.read", "memory.write"],
        dependencies=[],
        supported_languages=["ru", "en"],
    )


def test_base_module_creation():
    module = create_module()

    assert module.module_id == "memory.core.v1"
    assert module.name == "Memory Module"
    assert module.get_status() == "created"
    assert module.get_info()["permissions"] == ["memory.read", "memory.write"]
    assert module.get_info()["dependencies"] == []
    assert module.get_info()["supported_languages"] == ["ru", "en"]


def test_base_module_validation():
    assert_raises(ValueError, lambda: create_module(module_id=""))
    assert_raises(ValueError, lambda: create_module(name=" "))


def test_base_module_lifecycle():
    module = create_module()

    module.initialize()
    assert module.get_status() == "initialized"

    module.start()
    assert module.get_status() == "running"

    module.stop()
    assert module.get_status() == "stopped"

    module.unload()
    assert module.get_status() == "unloaded"


def test_base_module_invalid_status_transition():
    module = create_module()

    assert_raises(ValueError, module.start)
    assert module.get_status() == "created"


def test_module_registration():
    manager = ModuleManager()
    module = create_module()

    manager.register(module)

    assert manager.get_module("memory.core.v1") is module
    assert manager.list_modules()[0]["module_id"] == "memory.core.v1"


def test_module_duplicate_registration():
    manager = ModuleManager()
    module = create_module()

    manager.register(module)

    assert_raises(ValueError, lambda: manager.register(module))


def test_module_type_validation():
    manager = ModuleManager()

    assert_raises(TypeError, lambda: manager.register(object()))


def test_module_start_through_manager():
    manager = ModuleManager()
    module = create_module()

    manager.register(module)
    manager.initialize_all()
    manager.start_all()

    assert module.get_status() == "running"


def test_unknown_module_error():
    manager = ModuleManager()

    assert_raises(KeyError, lambda: manager.get_module("unknown.module"))


def run_tests():
    test_base_module_creation()
    test_base_module_validation()
    test_base_module_lifecycle()
    test_base_module_invalid_status_transition()
    test_module_registration()
    test_module_duplicate_registration()
    test_module_type_validation()
    test_module_start_through_manager()
    test_unknown_module_error()


if __name__ == "__main__":
    run_tests()
