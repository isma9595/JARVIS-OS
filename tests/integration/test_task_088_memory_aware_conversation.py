from pathlib import Path

from app import AppCommandSource, JarvisAppService
from memory import LocalMemoryManager


class TrackingProcessor:
    def __init__(self):
        self.calls = []

    def process(self, text):
        self.calls.append(text)
        return {"response": "processed"}


def make_service(tmp_path, processor=None):
    return JarvisAppService(
        command_processor=processor or TrackingProcessor(),
        memory_manager=LocalMemoryManager(Path(tmp_path) / "memory.json"),
    )


def test_vertical_remember_recall_persist_update_forget_and_delete_all(tmp_path):
    processor = TrackingProcessor()
    service = make_service(tmp_path, processor)

    remember = service.execute_contract("запомни, что тестовое слово — север", AppCommandSource.TEST)
    recall = service.execute_contract("какое моё тестовое слово", AppCommandSource.TEST)

    assert remember.ok is True
    assert remember.executed is True
    assert "север" in recall.output_text
    assert processor.calls == []

    new_service = make_service(tmp_path, TrackingProcessor())
    persisted = new_service.execute_contract("что ты помнишь о тестовом слове", AppCommandSource.TEST)
    unknown = new_service.execute_contract("какой мой любимый автомобиль", AppCommandSource.TEST)
    update = new_service.execute_contract("запомни, что тестовое слово — юг", AppCommandSource.TEST)
    removed = new_service.execute_contract("забудь тестовое слово", AppCommandSource.TEST)
    missing = new_service.execute_contract("что ты помнишь о тестовом слове", AppCommandSource.TEST)

    assert "север" in persisted.output_text
    assert "не помню" in unknown.output_text
    assert "Обновил" in update.output_text
    assert "Забыл" in removed.output_text
    assert "не помню" in missing.output_text

    new_service.remember_user_fact("первое", "1")
    new_service.remember_user_fact("второе", "2")
    request = new_service.execute_contract("забудь всё, что ты помнишь обо мне", AppCommandSource.TEST)
    cancel = new_service.execute_contract("отмена", AppCommandSource.TEST)

    assert request.awaiting_confirmation is True
    assert cancel.operation_id == request.operation_id
    assert len(new_service.list_user_memories().entries) == 2

    request_again = new_service.execute_contract("забудь всё, что ты помнишь обо мне", AppCommandSource.TEST)
    confirmed = new_service.execute_contract("да", AppCommandSource.TEST)

    assert confirmed.operation_id == request_again.operation_id
    assert new_service.list_user_memories().entries == ()


def test_vertical_safe_follow_up_and_english(tmp_path):
    service = make_service(tmp_path)
    service.execute_contract("запомни, что тестовое слово — север", AppCommandSource.TEST)

    recall = service.execute_contract("что ты помнишь о тестовом слове", AppCommandSource.TEST)
    repeat = service.execute_contract("покажи ещё раз", AppCommandSource.TEST)
    risky = service.execute_contract("сделай это ещё раз", AppCommandSource.TEST)

    assert repeat.output_text == recall.output_text
    assert risky.command_id != "memory.repeat"
    assert risky.executed is False

    english_service = make_service(tmp_path / "en")
    english_service.execute_contract("language English", AppCommandSource.TEST)
    remember = english_service.execute_contract("remember that test word is north", AppCommandSource.TEST)
    recall_en = english_service.execute_contract("what is my test word", AppCommandSource.TEST)

    assert "Remembered" in remember.output_text
    assert "I remember" in recall_en.output_text
    assert "north" in recall_en.output_text
