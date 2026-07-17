from pathlib import Path

from app import AppCommandSource, JarvisAppService
from language.language_manager import ApplicationLanguageManager
from memory import LocalMemoryManager
from users.user_profile import UserProfileManager


SAVE_RU_MARKER = "\u043c\u0430\u0440\u043a\u0435\u0440 \u0430\u0443\u0434\u0438\u0442\u0430 9073"
QUERY_RU_EXACT = (
    "\u0447\u0442\u043e \u0442\u044b \u043f\u043e\u043c\u043d\u0438\u0448\u044c "
    "\u043e \u043c\u0430\u0440\u043a\u0435\u0440 \u0430\u0443\u0434\u0438\u0442\u0430 9073"
)
QUERY_RU_INFLECTED = (
    "\u0447\u0442\u043e \u0442\u044b \u043f\u043e\u043c\u043d\u0438\u0448\u044c "
    "\u043e \u043c\u0430\u0440\u043a\u0435\u0440\u0435 \u0430\u0443\u0434\u0438\u0442\u0430 9073"
)


class FailingProcessor:
    user_profile = None
    memory_manager = None
    language_manager = None

    def process(self, text):
        raise AssertionError(f"memory contract test must not call CommandProcessor: {text}")


def make_service(tmp_path: Path):
    memory = LocalMemoryManager(tmp_path / "task091_memory.json")
    profile = UserProfileManager(tmp_path / "task091_profile.json")
    language = ApplicationLanguageManager.from_profile_manager(profile)
    return (
        JarvisAppService(
            command_processor=FailingProcessor(),
            memory_manager=memory,
            language_manager=language,
        ),
        memory,
    )


def test_characterizes_current_russian_inflected_memory_key_lookup(tmp_path):
    service, memory = make_service(tmp_path)

    stored = service.remember_user_fact(SAVE_RU_MARKER, "value-9073")
    exact = service.execute_command(QUERY_RU_EXACT, AppCommandSource.TEST)
    inflected = service.execute_command(QUERY_RU_INFLECTED, AppCommandSource.TEST)

    # CHARACTERIZATION OF CURRENT BEHAVIOR: exact Russian key lookup succeeds,
    # but the natural inflected form "о маркере ..." is treated as a different key.
    assert stored.ok is True
    assert memory.recall_user_fact(SAVE_RU_MARKER).found is True

    assert exact.registry_match_id == "memory.recall"
    assert exact.category == "memory"
    assert exact.risk_level == "read_only"
    assert exact.executed is False
    assert "value-9073" in exact.output_text

    assert inflected.registry_match_id == "memory.recall"
    assert inflected.category == "memory"
    assert inflected.risk_level == "read_only"
    assert inflected.executed is False
    assert "value-9073" not in inflected.output_text
    assert memory.recall_user_fact("\u043c\u0430\u0440\u043a\u0435\u0440\u0435 \u0430\u0443\u0434\u0438\u0442\u0430 9073").found is False
