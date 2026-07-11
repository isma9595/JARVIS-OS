from unittest.mock import Mock, patch

from voice import VoskLocalRecognitionDryRun


def blocked_gate():
    return {
        "allowed": False,
        "blockers": [
            "Пакет vosk не установлен.",
            "Путь к модели Vosk не указан.",
        ],
        "warnings": ["Автоматический запуск микрофона не выполняется."],
        "next_steps": ["Установите пакет vosk вручную."],
    }


def allowed_gate():
    return {
        "allowed": True,
        "blockers": [],
        "warnings": ["Постоянное прослушивание пока не связано с распознаванием."],
        "next_steps": ["Следующий шаг требует отдельного разрешения."],
    }


def test_dry_run_returns_blocked_result_when_gate_is_blocked():
    recognizer = Mock(return_value="тестовая команда")

    result = VoskLocalRecognitionDryRun(
        gate_checker=blocked_gate,
        recognizer=recognizer,
    ).run()

    assert result.success is False
    assert result.allowed is False
    assert result.dry_run is True
    assert result.used_fake_audio is True
    assert result.microphone_used is False
    assert result.real_model_loaded is False
    assert result.recognized_text is None
    assert "Пакет vosk не установлен." in result.blockers
    assert "Путь к модели Vosk не указан." in result.message
    assert "Реальный микрофон не запускался." in result.message
    recognizer.assert_not_called()


def test_dry_run_succeeds_with_fake_allowed_gate_and_fake_recognizer():
    seen_payloads = []

    def fake_recognizer(fake_audio):
        seen_payloads.append(fake_audio)
        return "тестовая команда"

    result = VoskLocalRecognitionDryRun(
        gate_checker=allowed_gate,
        recognizer=fake_recognizer,
    ).run()

    assert result.success is True
    assert result.allowed is True
    assert result.used_fake_audio is True
    assert result.microphone_used is False
    assert result.real_model_loaded is False
    assert result.recognized_text == "тестовая команда"
    assert "Пробный запуск локального распознавания Vosk выполнен" in result.message
    assert "Реальный микрофон не запускался." in result.message
    assert seen_payloads == [
        {
            "source": "vosk_dry_run_stub",
            "audio": b"",
            "stored_on_disk": False,
            "microphone_used": False,
        }
    ]


def test_dry_run_handles_fake_recognizer_failure_safely():
    def failing_recognizer(_fake_audio):
        raise RuntimeError("stub failure")

    result = VoskLocalRecognitionDryRun(
        gate_checker=allowed_gate,
        recognizer=failing_recognizer,
    ).run()

    assert result.success is False
    assert result.allowed is True
    assert result.used_fake_audio is True
    assert result.microphone_used is False
    assert result.real_model_loaded is False
    assert result.recognized_text is None
    assert "Пробный распознаватель вернул ошибку: stub failure" in result.blockers
    assert "Использовались только тестовые данные." in result.message


def test_dry_run_propagates_gate_warnings_and_next_steps():
    result = VoskLocalRecognitionDryRun(
        gate_checker=allowed_gate,
        recognizer=lambda _fake_audio: {"text": "тестовая команда"},
    ).run()

    assert result.warnings == [
        "Постоянное прослушивание пока не связано с распознаванием."
    ]
    assert result.next_steps == ["Следующий шаг требует отдельного разрешения."]
    assert result.to_dict()["recognized_text"] == "тестовая команда"


def test_dry_run_does_not_access_microphone_listeners_or_real_vosk_model():
    fake_vosk = Mock()
    with patch.dict("sys.modules", {"vosk": fake_vosk}):
        with patch(
            "voice.one_shot_microphone_capture.OneShotMicrophoneCapture.capture_once"
        ) as capture_once:
            with patch(
                "voice.microphone_listening_modes."
                "MicrophoneListeningModeManager.switch_to_continuous"
            ) as switch_to_continuous:
                with patch("threading.Thread.start") as thread_start:
                    result = VoskLocalRecognitionDryRun(
                        gate_checker=allowed_gate,
                        recognizer=lambda _fake_audio: "тестовая команда",
                    ).run()

    assert result.success is True
    fake_vosk.Model.assert_not_called()
    capture_once.assert_not_called()
    switch_to_continuous.assert_not_called()
    thread_start.assert_not_called()
