from voice import VoiceRecognitionCorrection, VoiceRecognitionCorrectionManager


def test_corrections_start_empty():
    manager = VoiceRecognitionCorrectionManager()

    assert manager.count() == 0
    assert manager.list_corrections() == []
    assert manager.find_correction("статуя система") is None


def test_add_correction():
    manager = VoiceRecognitionCorrectionManager()

    correction = manager.add_correction("статуя система", "статус системы")

    assert isinstance(correction, VoiceRecognitionCorrection)
    assert correction.wrong_text == "статуя система"
    assert correction.corrected_text == "статус системы"
    assert correction.normalized_wrong_text == "статуя система"
    assert correction.normalized_corrected_text == "статус системы"
    assert correction.source == "user_session_correction"
    assert manager.count() == 1


def test_find_correction_by_exact_normalized_wrong_text():
    manager = VoiceRecognitionCorrectionManager()
    correction = manager.add_correction("статуя система", "статус системы")

    assert manager.find_correction("статуя система") == correction


def test_normalize_spaces_case_and_yo():
    manager = VoiceRecognitionCorrectionManager()
    correction = manager.add_correction("  СТАТУЁ   СИСТЕМА! ", "статус системы")

    assert correction.normalized_wrong_text == "статуе система"
    assert manager.find_correction("статуё система") == correction
    assert manager.find_correction("  СТАТУЕ   СИСТЕМА  ") == correction


def test_list_corrections():
    manager = VoiceRecognitionCorrectionManager()
    first = manager.add_correction("статуя система", "статус системы")
    second = manager.add_correction("статую системы", "статус системы")

    assert manager.list_corrections() == [first, second]


def test_clear_corrections():
    manager = VoiceRecognitionCorrectionManager()
    manager.add_correction("статуя система", "статус системы")

    manager.clear()

    assert manager.count() == 0
    assert manager.list_corrections() == []


def test_max_corrections_trims_older_entries():
    manager = VoiceRecognitionCorrectionManager(max_corrections=2)

    manager.add_correction("первая", "один")
    second = manager.add_correction("вторая", "два")
    third = manager.add_correction("третья", "три")

    assert manager.list_corrections() == [second, third]
    assert manager.find_correction("первая") is None


def test_no_disk_persistence_or_audio_fields():
    manager = VoiceRecognitionCorrectionManager()
    correction = manager.add_correction("статуя система", "статус системы")

    assert not hasattr(manager, "path")
    assert not hasattr(manager, "file_path")
    assert not hasattr(correction, "audio")
    assert not hasattr(correction, "audio_path")
    assert not hasattr(correction, "audio_bytes")
