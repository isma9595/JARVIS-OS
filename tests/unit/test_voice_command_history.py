from voice import VoiceCommandHistoryEntry, VoiceCommandSessionHistory


def test_history_starts_empty():
    history = VoiceCommandSessionHistory()

    assert history.count() == 0
    assert history.last_entry() is None
    assert history.list_recent() == []


def test_add_one_entry():
    history = VoiceCommandSessionHistory()

    entry = history.add_entry(
        recognized_text="статус системы",
        normalized_text="статус системы",
        canonical_command="статус системы",
        status="allowlisted_executed",
    )

    assert isinstance(entry, VoiceCommandHistoryEntry)
    assert entry.id == 1
    assert entry.recognized_text == "статус системы"
    assert entry.canonical_command == "статус системы"
    assert entry.source == "one_shot_vosk"
    assert entry.status == "allowlisted_executed"
    assert history.count() == 1


def test_last_entry_returns_latest():
    history = VoiceCommandSessionHistory()

    first = history.add_entry(recognized_text="первая", status="pending_confirmation")
    second = history.add_entry(recognized_text="вторая", status="canceled")

    assert history.last_entry() == second
    assert history.last_entry() != first


def test_list_recent_respects_order_and_limit():
    history = VoiceCommandSessionHistory()
    for index in range(5):
        history.add_entry(recognized_text=f"команда {index}", status="recognized")

    recent = history.list_recent(limit=3)

    assert [entry.recognized_text for entry in recent] == [
        "команда 2",
        "команда 3",
        "команда 4",
    ]


def test_max_entries_trims_older_entries():
    history = VoiceCommandSessionHistory(max_entries=3)

    for index in range(5):
        history.add_entry(recognized_text=f"команда {index}", status="recognized")

    assert history.count() == 3
    assert [entry.recognized_text for entry in history.list_recent(limit=10)] == [
        "команда 2",
        "команда 3",
        "команда 4",
    ]


def test_clear_removes_entries():
    history = VoiceCommandSessionHistory()
    history.add_entry(recognized_text="статус системы", status="recognized")

    history.clear()

    assert history.count() == 0
    assert history.last_entry() is None


def test_count_returns_expected_number():
    history = VoiceCommandSessionHistory()

    history.add_entry(status="empty")
    history.add_entry(status="blocked")

    assert history.count() == 2


def test_entries_are_in_memory_only_and_have_no_audio_field():
    history = VoiceCommandSessionHistory()

    entry = history.add_entry(recognized_text="статус системы", status="recognized")

    assert not hasattr(history, "path")
    assert not hasattr(history, "file_path")
    assert not hasattr(entry, "audio")
    assert not hasattr(entry, "audio_path")
    assert not hasattr(entry, "audio_bytes")
