from dialogue import AssistantResponseHistory


def test_starts_empty():
    history = AssistantResponseHistory()

    assert history.count() == 0
    assert history.last_response() is None
    assert history.last_speakable_response() is None
    assert history.list_recent() == []


def test_add_response():
    history = AssistantResponseHistory()

    entry = history.add_response("  Ответ JARVIS.  ", source_command="статус")

    assert entry is not None
    assert entry.id == 1
    assert entry.text == "Ответ JARVIS."
    assert entry.source_command == "статус"
    assert entry.source == "command_processor"
    assert entry.speakable is True
    assert history.count() == 1


def test_last_response_returns_latest():
    history = AssistantResponseHistory()

    history.add_response("первый")
    history.add_response("второй")

    assert history.last_response().text == "второй"


def test_last_speakable_response_ignores_non_speakable_entries():
    history = AssistantResponseHistory()

    history.add_response("можно озвучить")
    history.add_response("служебный ответ", speakable=False)

    assert history.last_response().text == "служебный ответ"
    assert history.last_speakable_response().text == "можно озвучить"


def test_list_recent_respects_order_and_limit():
    history = AssistantResponseHistory()
    for index in range(1, 5):
        history.add_response(f"ответ {index}")

    recent = history.list_recent(limit=2)

    assert [entry.text for entry in recent] == ["ответ 3", "ответ 4"]


def test_max_entries_trims_older_entries():
    history = AssistantResponseHistory(max_entries=2)

    history.add_response("первый")
    history.add_response("второй")
    history.add_response("третий")

    assert history.count() == 2
    assert [entry.text for entry in history.list_recent(limit=5)] == ["второй", "третий"]


def test_clear_removes_entries():
    history = AssistantResponseHistory()
    history.add_response("ответ")

    history.clear()

    assert history.count() == 0
    assert history.last_response() is None


def test_count_returns_expected_number():
    history = AssistantResponseHistory()
    history.add_response("один")
    history.add_response("два")

    assert history.count() == 2


def test_empty_response_is_ignored():
    history = AssistantResponseHistory()

    entry = history.add_response("   ")

    assert entry is None
    assert history.count() == 0


def test_long_response_is_capped():
    history = AssistantResponseHistory(max_text_length=10)

    entry = history.add_response("а" * 20)

    assert entry.text == "а" * 10


def test_history_is_in_memory_only():
    history = AssistantResponseHistory()

    history.add_response("ответ")
    history.clear()

    assert not hasattr(history, "storage_path")
    assert not hasattr(history, "file_path")
