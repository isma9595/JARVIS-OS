import json
from pathlib import Path

from app import AppCommandSource, JarvisAppService
from memory import LocalMemoryManager, SessionConversationContext


class FailingProcessor:
    def __init__(self):
        self.calls = []

    def process(self, text):
        self.calls.append(text)
        raise AssertionError("memory commands must not call CommandProcessor")


def service_for(tmp_path, *, processor=None, context=None):
    manager = LocalMemoryManager(Path(tmp_path) / "memory.json")
    return JarvisAppService(
        command_processor=processor or FailingProcessor(),
        memory_manager=manager,
        conversation_context=context,
    )


def test_session_context_starts_empty_and_is_serializable():
    context = SessionConversationContext(max_turns=2)
    snapshot = context.snapshot()

    assert snapshot.bounded_turn_count == 0
    assert snapshot.turns == ()
    json.dumps(snapshot.to_dict(), ensure_ascii=False)


def test_session_context_is_bounded_and_evicts_oldest():
    context = SessionConversationContext(max_turns=2)
    context.add_turn(user_text="one", assistant_text="1", intent_id="memory.recall")
    context.add_turn(user_text="two", assistant_text="2", intent_id="memory.recall")
    context.add_turn(user_text="three", assistant_text="3", intent_id="memory.recall")

    snapshot = context.snapshot()

    assert snapshot.bounded_turn_count == 2
    assert [turn.user_summary for turn in snapshot.turns] == ["two", "three"]


def test_session_context_is_not_persisted(tmp_path):
    context = SessionConversationContext(max_turns=2)
    context.add_turn(user_text="what is my color", assistant_text="green", intent_id="memory.recall")
    service = service_for(tmp_path, context=context)
    new_service = service_for(tmp_path)

    assert service.get_conversation_context_snapshot().bounded_turn_count == 1
    assert new_service.get_conversation_context_snapshot().bounded_turn_count == 0


def test_preview_does_not_mutate_session_context(tmp_path):
    service = service_for(tmp_path)

    service.preview_command("запомни, что тестовое слово — север")

    assert service.get_conversation_context_snapshot().bounded_turn_count == 0
    assert not (Path(tmp_path) / "memory.json").exists()


def test_explicit_remember_stores_and_recalls_fact(tmp_path):
    service = service_for(tmp_path)

    remember = service.execute_contract("запомни, что мой любимый цвет — зелёный", AppCommandSource.TEST)
    recall = service.execute_contract("какой мой любимый цвет", AppCommandSource.TEST)

    assert remember.ok is True
    assert remember.command_id == "memory.remember"
    assert "зелёный" in remember.output_text
    assert recall.command_id == "memory.recall"
    assert "Я помню" in recall.output_text
    assert "зелёный" in recall.output_text


def test_ordinary_conversation_does_not_store_fact(tmp_path):
    class ConversationProcessor:
        def __init__(self):
            self.calls = []

        def process(self, text):
            self.calls.append(text)
            return {"response": "processed"}

    service = service_for(tmp_path, processor=ConversationProcessor())

    result = service.execute_contract("мой любимый цвет зелёный", AppCommandSource.TEST)

    assert result.command_id is None
    assert service.list_user_memories().entries == ()
    assert not (Path(tmp_path) / "memory.json").exists()


def test_memory_key_normalization_is_deterministic():
    normalize = LocalMemoryManager.normalize_user_fact_key

    assert normalize("мой любимый цвет") == "любимый цвет"
    assert normalize("любимый цвет") == "любимый цвет"
    assert normalize("Favorite Color") == "любимый цвет"
    assert normalize("favorite color") == "любимый цвет"


def test_appservice_inflected_russian_memory_recall_is_read_only(tmp_path):
    processor = FailingProcessor()
    service = service_for(tmp_path, processor=processor)
    service.remember_user_fact("маркер аудита 9073", "value-9073")
    before_entries = service.list_user_memories().entries
    before_storage = (Path(tmp_path) / "memory.json").read_text(encoding="utf-8")

    result = service.execute_command(
        "что ты помнишь о маркере аудита 9073",
        AppCommandSource.TEST,
    )
    after_storage = (Path(tmp_path) / "memory.json").read_text(encoding="utf-8")

    assert result.registry_match_id == "memory.recall"
    assert result.category == "memory"
    assert result.risk_level == "read_only"
    assert result.executed is False
    assert result.requires_confirmation is False
    assert result.operation_id is None
    assert result.operation_status == "succeeded"
    assert "value-9073" in result.output_text
    assert service.list_user_memories().entries == before_entries
    assert after_storage == before_storage
    assert processor.calls == []


def test_preview_inflected_russian_memory_recall_only_classifies(tmp_path):
    processor = FailingProcessor()
    service = service_for(tmp_path, processor=processor)
    service.remember_user_fact("маркер аудита 9073", "value-9073")
    before_entries = service.list_user_memories().entries
    before_storage = (Path(tmp_path) / "memory.json").read_text(encoding="utf-8")

    preview = service.preview_command("что ты помнишь о маркере аудита 9073")
    after_storage = (Path(tmp_path) / "memory.json").read_text(encoding="utf-8")

    assert preview.known_command is True
    assert preview.registry_match_id == "memory.recall"
    assert preview.category == "memory"
    assert preview.risk_level == "read_only"
    assert preview.read_only is True
    assert preview.requires_confirmation is False
    assert preview.operation_id is None
    assert service.list_user_memories().entries == before_entries
    assert after_storage == before_storage
    assert service.recent_execution_operations(None) == ()
    assert service._pending_memory_forget_all is None
    assert processor.calls == []


def test_validation_rejects_empty_oversized_control_and_credentials(tmp_path):
    manager = LocalMemoryManager(Path(tmp_path) / "memory.json")

    cases = [
        ("", "x", "empty_memory_key"),
        ("key", "", "empty_memory_value"),
        ("x" * 81, "value", "memory_key_too_long"),
        ("key", "x" * 301, "memory_value_too_long"),
        ("bad\x01key", "value", "memory_control_characters"),
        ("key", "api key sk-test-1234567890secret", "credential_like_memory_rejected"),
    ]

    for key, value, code in cases:
        result = manager.remember_user_fact(key, value)
        assert result.ok is False
        assert result.safe_error_code == code
        assert result.value is None
    assert not (Path(tmp_path) / "memory.json").exists()


def test_duplicate_remember_is_idempotent_and_update_reports_previous_value(tmp_path):
    service = service_for(tmp_path)

    first = service.remember_user_fact("тестовое слово", "север")
    duplicate = service.remember_user_fact("тестовое слово", "север")
    update = service.remember_user_fact("тестовое слово", "юг")

    assert first.changed is True
    assert duplicate.changed is False
    assert update.changed is True
    assert update.previous_value == "север"
    assert service.recall_user_fact("тестовое слово").value == "юг"


def test_unknown_memory_is_not_fabricated(tmp_path):
    service = service_for(tmp_path)

    result = service.execute_contract("какой мой любимый автомобиль", AppCommandSource.TEST)

    assert "не помню" in result.output_text
    assert "автомобиль" in result.output_text


def test_missing_and_corrupt_storage_fail_safely(tmp_path):
    storage = Path(tmp_path) / "memory.json"
    manager = LocalMemoryManager(storage)

    assert manager.list_user_facts().entries == ()
    assert not storage.exists()

    storage.write_text("{bad json", encoding="utf-8")
    result = manager.recall_user_fact("тестовое слово")

    assert result.ok is True
    assert result.found is False
    assert manager.last_error_code == "memory_storage_unreadable"


def test_list_memory_is_bounded_deterministic_and_safe(tmp_path):
    service = service_for(tmp_path)
    for index in range(30):
        service.remember_user_fact(f"ключ {index:02d}", f"значение {index:02d}")

    result = service.execute_contract("покажи, что ты помнишь обо мне", AppCommandSource.TEST)

    assert result.command_id == "memory.list"
    assert result.output_text.count("- ключ") == 25
    assert "- ключ 00: значение 00" in result.output_text
    assert "memory.json" not in result.output_text
    assert "normalized_key" not in result.output_text


def test_forgetting_one_and_missing_key_are_safe(tmp_path):
    service = service_for(tmp_path)
    service.remember_user_fact("тестовое слово", "север")

    removed = service.execute_contract("забудь тестовое слово", AppCommandSource.TEST)
    missing = service.execute_contract("забудь тестовое слово", AppCommandSource.TEST)

    assert "Забыл" in removed.output_text
    assert removed.executed is True
    assert "не было" in missing.output_text
    assert missing.executed is False


def test_vague_forget_requests_clarification(tmp_path):
    service = service_for(tmp_path)

    result = service.execute_contract("забудь это", AppCommandSource.TEST)

    assert result.command_id == "memory.clarify"
    assert result.executed is False
    assert "уточните" in result.output_text.lower()


def test_delete_all_requires_confirmation_and_cancel_preserves_memory(tmp_path):
    service = service_for(tmp_path)
    service.remember_user_fact("первое", "1")
    service.remember_user_fact("второе", "2")

    request = service.execute_contract("забудь всё, что ты помнишь обо мне", AppCommandSource.TEST)
    cancel = service.execute_contract("отмена", AppCommandSource.TEST)

    assert request.awaiting_confirmation is True
    assert request.operation_id
    assert cancel.operation_id == request.operation_id
    assert len(service.list_user_memories().entries) == 2


def test_delete_all_confirmation_deletes_once(tmp_path):
    service = service_for(tmp_path)
    service.remember_user_fact("первое", "1")
    service.remember_user_fact("второе", "2")

    request = service.execute_contract("забудь всё, что ты помнишь обо мне", AppCommandSource.TEST)
    confirmed = service.execute_contract("да", AppCommandSource.TEST)
    duplicate = service.execute_contract("да", AppCommandSource.TEST)

    assert confirmed.operation_id == request.operation_id
    assert confirmed.executed is True
    assert service.list_user_memories().entries == ()
    assert duplicate.command_id != "memory.forget_all"


def test_memory_commands_do_not_call_processor_action_router_provider_or_network(tmp_path):
    processor = FailingProcessor()
    service = service_for(tmp_path, processor=processor)

    service.execute_contract("запомни: тестовое слово = север", AppCommandSource.TEST)
    service.execute_contract("какое моё тестовое слово", AppCommandSource.TEST)
    service.execute_contract("забудь тестовое слово", AppCommandSource.TEST)

    assert processor.calls == []


def test_safe_follow_up_repeats_only_read_only_memory_answer(tmp_path):
    service = service_for(tmp_path)
    service.remember_user_fact("тестовое слово", "север")

    first = service.execute_contract("что ты помнишь о тестовом слове", AppCommandSource.TEST)
    repeat = service.execute_contract("покажи ещё раз", AppCommandSource.TEST)
    risky = service.execute_contract("сделай это ещё раз", AppCommandSource.TEST)

    assert repeat.output_text == first.output_text
    assert risky.command_id != "memory.repeat"
    assert risky.executed is False


def test_english_memory_responses_after_language_switch(tmp_path):
    service = service_for(tmp_path)

    service.execute_contract("language English", AppCommandSource.TEST)
    remember = service.execute_contract("remember that test word is north", AppCommandSource.TEST)
    recall = service.execute_contract("what is my test word", AppCommandSource.TEST)
    service.execute_contract("language Russian", AppCommandSource.TEST)
    russian_recall = service.execute_contract("что ты помнишь о тестовом слове", AppCommandSource.TEST)

    assert "Remembered" in remember.output_text
    assert "I remember" in recall.output_text
    assert "north" in recall.output_text
    assert "north" in russian_recall.output_text
