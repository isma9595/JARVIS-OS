import json
from pathlib import Path
from tempfile import TemporaryDirectory

from ideas import IdeaManager


def storage_path(tmp_dir):
    return Path(tmp_dir) / "ideas.json"


def test_creation():
    with TemporaryDirectory() as tmp_dir:
        manager = IdeaManager(storage_path(tmp_dir))

        assert manager.count_ideas() == 0


def test_creates_ideas_file():
    with TemporaryDirectory() as tmp_dir:
        path = storage_path(tmp_dir)

        IdeaManager(path)

        assert path.exists()
        assert json.loads(path.read_text(encoding="utf-8")) == {"ideas": []}


def test_list_ideas_empty():
    with TemporaryDirectory() as tmp_dir:
        manager = IdeaManager(storage_path(tmp_dir))

        assert manager.list_ideas() == []


def test_count_ideas():
    with TemporaryDirectory() as tmp_dir:
        manager = IdeaManager(storage_path(tmp_dir))

        assert manager.count_ideas() == 0
        manager.add_idea("научиться видеть экран")
        assert manager.count_ideas() == 1


def test_add_idea():
    with TemporaryDirectory() as tmp_dir:
        manager = IdeaManager(storage_path(tmp_dir))

        idea = manager.add_idea("сделать голосовое управление")

        assert idea["title"] == "сделать голосовое управление"
        assert idea["description"] == ""
        assert idea["source"] == "user_command"
        assert idea["status"] == "new"
        assert idea["priority"] == "normal"
        assert idea["id"]
        assert idea["created_at"]
        assert idea["updated_at"]


def test_empty_title_error():
    with TemporaryDirectory() as tmp_dir:
        manager = IdeaManager(storage_path(tmp_dir))

        try:
            manager.add_idea("   ")
        except ValueError as exc:
            assert "Idea title must not be empty" in str(exc)
            return

        raise AssertionError("Expected ValueError")


def test_save_and_reload_ideas():
    with TemporaryDirectory() as tmp_dir:
        path = storage_path(tmp_dir)
        manager = IdeaManager(path)
        manager.add_idea("чтобы JARVIS видел монитор")

        reloaded_manager = IdeaManager(path)

        ideas = reloaded_manager.list_ideas()
        assert len(ideas) == 1
        assert ideas[0]["title"] == "чтобы JARVIS видел монитор"


def run_tests():
    test_creation()
    test_creates_ideas_file()
    test_list_ideas_empty()
    test_count_ideas()
    test_add_idea()
    test_empty_title_error()
    test_save_and_reload_ideas()


if __name__ == "__main__":
    run_tests()
