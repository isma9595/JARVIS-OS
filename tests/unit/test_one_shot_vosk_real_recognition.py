import sys

from voice import (
    AudioDependencyReadinessResult,
    AudioDependencyStatus,
    OneShotVoskRealRecognition,
    OneShotVoskRealRecognitionResult,
)


class FakeSettings:
    def __init__(self, model_path=None):
        self.model_path = model_path

    def get_model_path(self):
        return self.model_path


class FakeReadiness:
    def __init__(self, ready=True):
        self.ready = ready

    def verify(self, configured_path=None):
        return {
            "ready_for_future_recognition": self.ready,
            "reasons": [] if self.ready else ["Папка модели Vosk не готова."],
            "warnings": [],
            "next_steps": ["Проверьте модель Vosk вручную."],
        }


class FakeCapture:
    def __init__(self, result=None, error=None):
        self.calls = 0
        self.result = result or {
            "audio_captured": True,
            "audio": b"fake-audio",
            "duration_seconds": 2.0,
            "stored_on_disk": False,
        }
        self.error = error

    def capture_once(self):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.result


class FakeRuntime:
    class Model:
        def __init__(self, model_path):
            self.model_path = model_path

    class KaldiRecognizer:
        recognized_text = "статус системы"

        def __init__(self, model, sample_rate):
            self.model = model
            self.sample_rate = sample_rate
            self.audio = None

        def AcceptWaveform(self, audio):
            self.audio = audio
            return True

        def FinalResult(self):
            return '{"text": "' + self.recognized_text + '"}'


class FakeDependencyChecker:
    def __init__(self, missing=()):
        self.missing = set(missing)

    def check(self):
        dependencies = []
        for name in ("numpy", "sounddevice", "vosk"):
            available = name not in self.missing
            dependencies.append(
                AudioDependencyStatus(
                    name=name,
                    available=available,
                    import_error=None if available else f"missing {name}",
                    manual_install_command=f"python -m pip install {name}",
                )
            )
        available = {dependency.name: dependency.available for dependency in dependencies}
        return AudioDependencyReadinessResult(
            dependencies=tuple(dependencies),
            audio_capture_dependencies_ready=bool(
                available["numpy"] and available["sounddevice"]
            ),
            vosk_recognition_dependencies_ready=bool(available["vosk"]),
            russian_summary="fake",
        )


def allowed_gate(_model_path):
    return {
        "allowed": True,
        "blockers": [],
        "warnings": [],
        "next_steps": [],
    }


def blocked_gate(_model_path):
    return {
        "allowed": False,
        "blockers": ["Пакет vosk не установлен."],
        "warnings": ["Автоматический запуск микрофона не выполняется."],
        "next_steps": ["Установите пакет vosk вручную."],
    }


def fake_runtime_factory():
    return FakeRuntime


class BoolRaisingAudio:
    def __bool__(self):
        raise ValueError("ambiguous truth value")

    def __bytes__(self):
        return b"fake-array-audio"


def create_service(**overrides):
    defaults = {
        "settings_manager": FakeSettings("C:/fake/vosk-model"),
        "gate_checker": allowed_gate,
        "readiness_verifier": FakeReadiness(),
        "capture_provider": FakeCapture(),
        "vosk_runtime_factory": fake_runtime_factory,
        "capture_seconds": 2,
    }
    defaults.update(overrides)
    return OneShotVoskRealRecognition(**defaults)


def test_blocks_when_model_path_is_missing():
    capture = FakeCapture()
    service = create_service(
        settings_manager=FakeSettings(None),
        capture_provider=capture,
    )

    result = service.run_once(explicit_one_shot_requested=True)

    assert result.blocked is True
    assert result.allowed is False
    assert result.completed is False
    assert "Путь к модели Vosk не указан." in result.reasons
    assert capture.calls == 0


def test_blocks_when_readiness_gate_denies():
    capture = FakeCapture()
    service = create_service(gate_checker=blocked_gate, capture_provider=capture)

    result = service.run_once(explicit_one_shot_requested=True)

    assert result.blocked is True
    assert "Пакет vosk не установлен." in result.reasons
    assert capture.calls == 0


def test_blocks_safely_when_vosk_package_is_unavailable():
    capture = FakeCapture()

    def missing_runtime():
        raise ImportError("no vosk")

    service = create_service(
        capture_provider=capture,
        vosk_runtime_factory=missing_runtime,
    )

    result = service.run_once(explicit_one_shot_requested=True)

    assert result.blocked is True
    assert "Пакет vosk не установлен или недоступен для текущего Python." in result.reasons
    assert result.next_steps == ["python -m pip install vosk"]
    assert capture.calls == 0


def test_blocks_with_precise_numpy_install_step_when_numpy_is_missing():
    capture = FakeCapture()
    service = create_service(
        capture_provider=capture,
        dependency_checker=FakeDependencyChecker(missing={"numpy"}),
    )

    result = service.run_once(explicit_one_shot_requested=True)

    assert result.blocked is True
    assert "Зависимость NumPy не найдена" in result.reasons[0]
    assert result.next_steps == ["python -m pip install numpy"]
    assert capture.calls == 0


def test_blocks_with_precise_sounddevice_install_step_when_sounddevice_is_missing():
    capture = FakeCapture()
    service = create_service(
        capture_provider=capture,
        dependency_checker=FakeDependencyChecker(missing={"sounddevice"}),
    )

    result = service.run_once(explicit_one_shot_requested=True)

    assert result.blocked is True
    assert "Зависимость sounddevice не найдена" in result.reasons[0]
    assert result.next_steps == ["python -m pip install sounddevice"]
    assert capture.calls == 0


def test_blocks_with_precise_vosk_install_step_when_vosk_is_missing():
    capture = FakeCapture()
    service = create_service(
        capture_provider=capture,
        dependency_checker=FakeDependencyChecker(missing={"vosk"}),
    )

    result = service.run_once(explicit_one_shot_requested=True)

    assert result.blocked is True
    assert "Пакет vosk не найден" in result.reasons[0]
    assert result.next_steps == ["python -m pip install vosk"]
    assert capture.calls == 0


def test_blocks_safely_when_capture_provider_is_missing():
    service = create_service()
    service.capture_provider = None
    service._default_capture_provider = lambda: None

    result = service.run_once(explicit_one_shot_requested=True)

    assert result.blocked is True
    assert "Провайдер одноразового захвата микрофона недоступен." in result.reasons


def test_handles_capture_failure_safely():
    capture = FakeCapture(error=RuntimeError("mic failed"))
    service = create_service(capture_provider=capture)

    result = service.run_once(explicit_one_shot_requested=True)

    assert result.blocked is True
    assert result.completed is False
    assert "Одноразовый захват микрофона завершился ошибкой: mic failed" in result.reasons


def test_handles_recognizer_empty_result_safely():
    FakeRuntime.KaldiRecognizer.recognized_text = ""
    service = create_service()

    result = service.run_once(explicit_one_shot_requested=True)

    assert result.completed is True
    assert result.blocked is False
    assert result.recognized_text is None
    FakeRuntime.KaldiRecognizer.recognized_text = "статус системы"


def test_completes_with_fake_capture_provider_and_fake_recognizer():
    capture = FakeCapture()
    service = create_service(capture_provider=capture)

    result = service.run_once(explicit_one_shot_requested=True)

    assert result.allowed is True
    assert result.completed is True
    assert result.blocked is False
    assert capture.calls == 1


def test_extract_audio_payload_prefers_audio_without_truthiness_check():
    audio = BoolRaisingAudio()
    fallback = b"fallback-audio"

    payload = OneShotVoskRealRecognition._extract_audio_payload(
        {
            "audio_captured": True,
            "audio": audio,
            "audio_payload": fallback,
        }
    )

    assert payload is audio


def test_extract_audio_payload_uses_audio_payload_when_audio_is_none():
    fallback = BoolRaisingAudio()

    payload = OneShotVoskRealRecognition._extract_audio_payload(
        {
            "audio_captured": True,
            "audio": None,
            "audio_payload": fallback,
        }
    )

    assert payload is fallback


def test_extract_audio_payload_returns_none_when_payload_is_missing():
    payload = OneShotVoskRealRecognition._extract_audio_payload(
        {
            "audio_captured": True,
            "duration_seconds": 2.0,
        }
    )

    assert payload is None


def test_run_once_handles_array_like_audio_without_truthiness_check():
    audio = BoolRaisingAudio()
    capture = FakeCapture(
        result={
            "audio_captured": True,
            "audio": audio,
            "duration_seconds": 2.0,
            "stored_on_disk": False,
        }
    )
    service = create_service(capture_provider=capture)

    result = service.run_once(explicit_one_shot_requested=True)

    assert result.completed is True
    assert result.blocked is False
    assert capture.calls == 1


def test_returns_recognized_text_from_fake_recognizer():
    service = create_service()

    result = service.run_once(explicit_one_shot_requested=True)

    assert result.recognized_text == "статус системы"


def test_safety_notes_say_mic_was_one_shot_only():
    result = create_service().run_once(explicit_one_shot_requested=True)

    assert "Микрофон был включён только для одного короткого захвата." in result.safety_notes


def test_safety_notes_say_continuous_listening_was_not_used():
    result = create_service().run_once(explicit_one_shot_requested=True)

    assert "Постоянное прослушивание не использовалось." in result.safety_notes


def test_safety_notes_say_audio_was_not_sent_to_cloud():
    result = create_service().run_once(explicit_one_shot_requested=True)

    assert "Аудио не отправлялось в облако." in result.safety_notes


def test_result_says_recognized_text_was_not_executed_as_command():
    result = create_service().run_once(explicit_one_shot_requested=True)

    assert "Распознанный текст не выполнялся как команда." in result.safety_notes
    assert "Выполнение распознанного текста" in result.next_steps[0]


def test_formatter_returns_russian_blocked_message():
    result = create_service(
        vosk_runtime_factory=lambda: (_ for _ in ()).throw(ImportError("no vosk"))
    ).run_once(explicit_one_shot_requested=True)

    formatted = OneShotVoskRealRecognition.format_result(result)

    assert formatted.startswith("Реальное распознавание Vosk заблокировано.")
    assert "Причины:" in formatted
    assert "Пакет vosk не установлен" in formatted
    assert "Следующий шаг: python -m pip install vosk" in formatted
    assert "Безопасность:" in formatted
    assert "Микрофон не запускался." in formatted


def test_formatter_returns_russian_success_message():
    result = OneShotVoskRealRecognitionResult(
        allowed=True,
        completed=True,
        blocked=False,
        recognized_text="статус системы",
        capture_seconds=2,
    )

    formatted = OneShotVoskRealRecognition.format_result(result)

    assert "Распознавание завершено." in formatted
    assert "Я распознал: \"статус системы\"." in formatted
    assert "Выполнить эту команду? Подтвердите: да / нет." in formatted
    assert "Безопасность: команда не выполнена автоматически." in formatted


def test_no_real_vosk_import_is_required_in_tests(monkeypatch):
    monkeypatch.delitem(sys.modules, "vosk", raising=False)

    result = create_service().run_once(explicit_one_shot_requested=True)

    assert result.completed is True
    assert "vosk" not in sys.modules


def test_no_real_microphone_is_required_in_tests():
    capture = FakeCapture()
    service = create_service(capture_provider=capture)

    result = service.run_once(explicit_one_shot_requested=True)

    assert result.completed is True
    assert capture.calls == 1
