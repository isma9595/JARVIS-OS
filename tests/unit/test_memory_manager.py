from pathlib import Path
from tempfile import TemporaryDirectory

from memory import LocalMemoryManager


def create_manager(tmp_dir):
    return LocalMemoryManager(Path(tmp_dir) / "memory.json")


def assert_raises(expected_exception, callback):
    try:
        callback()
    except expected_exception:
        return

    raise AssertionError(f"Expected {expected_exception.__name__}")


def test_creation():
    with TemporaryDirectory() as tmp_dir:
        manager = create_manager(tmp_dir)

        assert isinstance(manager, LocalMemoryManager)


def test_memory_file_created():
    with TemporaryDirectory() as tmp_dir:
        storage_path = Path(tmp_dir) / "memory.json"
        manager = LocalMemoryManager(storage_path)

        assert manager.memory_file_exists() is True
        assert storage_path.exists()


def test_list_memories_empty():
    with TemporaryDirectory() as tmp_dir:
        manager = create_manager(tmp_dir)

        assert manager.list_memories() == []


def test_count_memories_empty():
    with TemporaryDirectory() as tmp_dir:
        manager = create_manager(tmp_dir)

        assert manager.count_memories() == 0


def test_add_memory():
    with TemporaryDirectory() as tmp_dir:
        manager = create_manager(tmp_dir)

        memory = manager.add_memory("любишь зелёный цвет")

        assert memory["type"] == "note"
        assert memory["content"] == "любишь зелёный цвет"
        assert memory["source"] == "user_command"
        assert memory["tags"] == []
        assert manager.count_memories() == 1


def test_add_memory_rejects_empty_content():
    with TemporaryDirectory() as tmp_dir:
        manager = create_manager(tmp_dir)

        assert_raises(ValueError, lambda: manager.add_memory("   "))


def test_memory_persists_and_reloads():
    with TemporaryDirectory() as tmp_dir:
        storage_path = Path(tmp_dir) / "memory.json"
        manager = LocalMemoryManager(storage_path)
        manager.add_memory("работаю с документами")

        reloaded_manager = LocalMemoryManager(storage_path)

        assert reloaded_manager.count_memories() == 1
        assert reloaded_manager.list_memories()[0]["content"] == "работаю с документами"


def test_search_memories():
    with TemporaryDirectory() as tmp_dir:
        manager = create_manager(tmp_dir)
        manager.add_memory("работаю с документами")
        manager.add_memory("люблю зелёный цвет")

        results = manager.search_memories("документы")

        assert len(results) == 1
        assert results[0]["content"] == "работаю с документами"


def run_tests():
    test_creation()
    test_memory_file_created()
    test_list_memories_empty()
    test_count_memories_empty()
    test_add_memory()
    test_add_memory_rejects_empty_content()
    test_memory_persists_and_reloads()
    test_search_memories()


if __name__ == "__main__":
    run_tests()
