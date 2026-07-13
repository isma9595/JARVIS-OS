from voice import DryRunSpeechSynthesisBackend, SpeechSynthesisBackend


def test_dry_run_backend_returns_success():
    backend = DryRunSpeechSynthesisBackend()

    result = backend.synthesize("Исмаил, система работает.")

    assert result.success is True


def test_dry_run_backend_does_not_require_external_dependencies():
    backend = DryRunSpeechSynthesisBackend()

    result = backend.synthesize("тест")

    assert "Внешние зависимости не требуются." in result.safety_notes


def test_dry_run_backend_includes_backend_name():
    backend = DryRunSpeechSynthesisBackend()

    result = backend.synthesize("тест")

    assert result.backend_name == "dry_run"


def test_dry_run_backend_includes_spoken_text():
    backend = DryRunSpeechSynthesisBackend()

    result = backend.synthesize("  тестовая фраза  ")

    assert result.spoken_text == "тестовая фраза"


def test_dry_run_backend_includes_safety_notes():
    backend = DryRunSpeechSynthesisBackend()

    result = backend.synthesize("тест")

    assert "Реальный звук не воспроизводился." in result.safety_notes
    assert "Облачный TTS не использовался." in result.safety_notes
    assert "Аудиофайл не сохранялся." in result.safety_notes


def test_base_backend_is_safe_not_implemented_result():
    backend = SpeechSynthesisBackend()

    result = backend.synthesize("тест")

    assert result.success is False
    assert result.backend_name == "base"
    assert result.error == "speech synthesis is not implemented"
