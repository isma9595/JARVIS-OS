from voice import (
    OneShotVoskRecognitionBridge,
    OneShotVoskRecognitionBridgeResult,
)


def allowed_gate():
    return {
        "allowed": True,
        "blockers": [],
        "warnings": [],
        "next_steps": [],
    }


def blocked_gate():
    return {
        "allowed": False,
        "blockers": ["Путь к модели Vosk не указан."],
        "warnings": ["Автоматический запуск микрофона не выполняется."],
        "next_steps": [],
    }


def fake_capture():
    return {
        "audio_captured": True,
        "audio": b"fake-audio",
        "source": "injected_test",
        "stored_on_disk": False,
    }


def fake_recognizer(audio_payload):
    assert audio_payload == b"fake-audio"
    return {"text": "статус системы"}


def test_bridge_blocks_when_vosk_gate_is_not_ready():
    bridge = OneShotVoskRecognitionBridge(
        gate_checker=blocked_gate,
        capture_provider=fake_capture,
        recognizer=fake_recognizer,
    )

    result = bridge.run_once(explicit_one_shot_requested=True)

    assert result.allowed is False
    assert result.blocked is True
    assert result.completed is False
    assert result.recognized_text is None
    assert "Путь к модели Vosk не указан." in result.reasons


def test_bridge_does_not_call_capture_provider_when_gate_blocks():
    calls = []

    def capture_provider():
        calls.append("capture")
        return fake_capture()

    bridge = OneShotVoskRecognitionBridge(
        gate_checker=blocked_gate,
        capture_provider=capture_provider,
        recognizer=fake_recognizer,
    )

    bridge.run_once(explicit_one_shot_requested=True)

    assert calls == []


def test_bridge_requires_explicit_one_shot_intent():
    bridge = OneShotVoskRecognitionBridge(
        gate_checker=allowed_gate,
        capture_provider=fake_capture,
        recognizer=fake_recognizer,
    )

    result = bridge.run_once(explicit_one_shot_requested=False)

    assert result.blocked is True
    assert "Нужен явный one-shot запрос пользователя." in result.reasons


def test_bridge_handles_missing_capture_provider_safely():
    bridge = OneShotVoskRecognitionBridge(
        gate_checker=allowed_gate,
        recognizer=fake_recognizer,
    )

    result = bridge.run_once(explicit_one_shot_requested=True)

    assert result.blocked is True
    assert "Провайдер one-shot аудио не передан." in result.reasons


def test_bridge_handles_missing_recognizer_safely():
    bridge = OneShotVoskRecognitionBridge(
        gate_checker=allowed_gate,
        capture_provider=fake_capture,
    )

    result = bridge.run_once(explicit_one_shot_requested=True)

    assert result.blocked is True
    assert "Распознаватель Vosk не передан." in result.reasons


def test_bridge_can_complete_with_fake_capture_provider_and_fake_recognizer():
    bridge = OneShotVoskRecognitionBridge(
        gate_checker=allowed_gate,
        capture_provider=fake_capture,
        recognizer=fake_recognizer,
    )

    result = bridge.run_once(explicit_one_shot_requested=True)

    assert result.allowed is True
    assert result.completed is True
    assert result.blocked is False
    assert result.simulated is True


def test_bridge_returns_recognized_text_from_fake_recognizer():
    bridge = OneShotVoskRecognitionBridge(
        gate_checker=allowed_gate,
        capture_provider=fake_capture,
        recognizer=fake_recognizer,
    )

    result = bridge.run_once(explicit_one_shot_requested=True)

    assert result.recognized_text == "статус системы"


def test_bridge_safety_notes_cover_mic_cloud_and_continuous_listening():
    bridge = OneShotVoskRecognitionBridge(
        gate_checker=allowed_gate,
        capture_provider=fake_capture,
        recognizer=fake_recognizer,
    )

    result = bridge.run_once(explicit_one_shot_requested=True)
    notes = " ".join(result.safety_notes)

    assert "Реальный микрофон не запускался автоматически." in notes
    assert "Аудио не отправлялось в облако." in notes
    assert "Постоянное прослушивание не использовалось." in notes


def test_bridge_formatter_returns_russian_blocked_message():
    result = OneShotVoskRecognitionBridgeResult(
        allowed=False,
        completed=False,
        blocked=True,
        simulated=False,
        reasons=["Путь к модели Vosk не указан."],
    )

    formatted = OneShotVoskRecognitionBridge.format_result(result)

    assert formatted.startswith("One-shot Vosk bridge заблокирован.")
    assert "Причины:" in formatted
    assert "- Путь к модели Vosk не указан." in formatted
    assert "Безопасность:" in formatted


def test_bridge_formatter_returns_russian_simulated_completed_message():
    result = OneShotVoskRecognitionBridgeResult(
        allowed=True,
        completed=True,
        blocked=False,
        simulated=True,
        recognized_text="статус системы",
    )

    formatted = OneShotVoskRecognitionBridge.format_result(result)

    assert "One-shot Vosk bridge выполнен в безопасном тестовом режиме." in formatted
    assert "Распознанный текст: статус системы" in formatted
    assert "Реальный микрофон не запускался" in formatted


def test_bridge_uses_only_injected_dependencies_without_real_vosk_or_microphone():
    capture_calls = []
    recognizer_calls = []

    def capture_provider():
        capture_calls.append(True)
        return fake_capture()

    def recognizer(audio_payload):
        recognizer_calls.append(audio_payload)
        return "статус системы"

    bridge = OneShotVoskRecognitionBridge(
        gate_checker=allowed_gate,
        capture_provider=capture_provider,
        recognizer=recognizer,
    )

    result = bridge.run_once(explicit_one_shot_requested=True)

    assert result.completed is True
    assert capture_calls == [True]
    assert recognizer_calls == [b"fake-audio"]
