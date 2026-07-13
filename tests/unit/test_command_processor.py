from core.command_processor import CommandProcessor
from ideas import IdeaManager
from memory import LocalMemoryManager
from pathlib import Path
from tempfile import TemporaryDirectory
from users.user_profile import UserProfileManager
from voice import (
    AudioDependencyReadinessResult,
    AudioDependencyStatus,
    MicrophoneListeningModeManager,
    OneShotVoskRecognitionBridgeResult,
    OneShotVoskRealRecognitionResult,
    VoiceInputManager,
    VoskSettingsManager,
)


class InMemoryVoskSettingsManager:
    def __init__(self):
        self._settings = {}

    def load_settings(self):
        return dict(self._settings)

    def set_model_path(self, model_path):
        self._settings["model_path"] = model_path
        self._settings.setdefault("language", "ru")
        return dict(self._settings)

    def clear_model_path(self):
        self._settings["model_path"] = None
        self._settings.setdefault("language", "ru")
        return dict(self._settings)

    def set_language(self, language):
        self._settings["language"] = language
        return dict(self._settings)


class FakeAudioDependencyReadinessChecker:
    def __init__(self, missing=()):
        self.missing = set(missing)
        self.calls = 0

    def check(self):
        self.calls += 1
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
        from voice.audio_dependency_readiness import AudioDependencyReadinessChecker

        return AudioDependencyReadinessResult(
            dependencies=tuple(dependencies),
            audio_capture_dependencies_ready=bool(
                available["numpy"] and available["sounddevice"]
            ),
            vosk_recognition_dependencies_ready=bool(available["vosk"]),
            russian_summary=AudioDependencyReadinessChecker.format_russian_dependencies(
                dependencies
            ),
        )


def test_speech_backend_commands():
    processor = CommandProcessor()

    assert processor.process("speech backend")["intent"] == "speech.backend.status"
    assert (
        processor.process("почему нет распознавания")["intent"]
        == "speech.backend.explain"
    )


def test_audio_dependency_readiness_commands_return_safe_success_response():
    checker = FakeAudioDependencyReadinessChecker()
    processor = CommandProcessor(audio_dependency_readiness_checker=checker)

    for command in (
        "проверка аудио зависимостей",
        "проверить зависимости микрофона",
        "диагностика микрофона",
        "почему не работает микрофон",
    ):
        result = processor.process(command)

        assert result["intent"] == "voice.audio_dependencies.status"
        assert "Зависимости аудиозахвата готовы." in result["response"]
        assert "- numpy" in result["response"]
        assert "- sounddevice" in result["response"]
        assert "- vosk" in result["response"]
        assert "JARVIS ничего не устанавливает автоматически" in result["response"]
        assert "постоянное прослушивание не включается" in result["response"]

    assert checker.calls == 4


def test_audio_dependency_package_commands_return_safe_responses():
    for command, missing, install_command in (
        ("проверить numpy", "numpy", "python -m pip install numpy"),
        ("проверить sounddevice", "sounddevice", "python -m pip install sounddevice"),
        ("проверить vosk пакет", "vosk", "python -m pip install vosk"),
    ):
        processor = CommandProcessor(
            audio_dependency_readiness_checker=FakeAudioDependencyReadinessChecker(
                missing={missing}
            )
        )

        result = processor.process(command)

        assert result["intent"] == "voice.audio_dependencies.status"
        assert install_command in result["response"]
        assert "JARVIS ничего не устанавливает автоматически" in result["response"]


def test_audio_dependency_status_alias_commands_return_safe_responses():
    checker = FakeAudioDependencyReadinessChecker()
    processor = CommandProcessor(audio_dependency_readiness_checker=checker)

    for command in (
        "проверить аудио зависимости",
        "статус numpy",
        "статус sounddevice",
        "статус vosk пакета",
    ):
        result = processor.process(command)

        assert result["intent"] == "voice.audio_dependencies.status"
        assert "Зависимости аудиозахвата готовы." in result["response"]
        assert "JARVIS ничего не устанавливает автоматически" in result["response"]


def test_vosk_real_commands_and_selection_flow():
    processor, manager = create_voice_enabled_processor()
    original_use_vosk_backend = manager.use_vosk_backend
    use_vosk_calls = []

    def tracked_use_vosk_backend():
        use_vosk_calls.append(True)
        return original_use_vosk_backend()

    manager.use_vosk_backend = tracked_use_vosk_backend

    status = processor.process("vosk")
    assert status["intent"] == "speech.backend.vosk.status"
    assert manager.get_speech_backend_name() == "none"

    result = processor.process("выбрать vosk")
    assert result["intent"] == "speech.backend.vosk.select"
    assert use_vosk_calls == [True]
    assert manager.get_speech_backend_name() == "vosk_local"
    assert manager.get_speech_backend_status()["available"] is False
    assert "микрофон не включается" in result["response"]

    backend_status = processor.process("речевой backend")
    assert backend_status["intent"] == "speech.backend.status"
    assert "vosk_local" in backend_status["response"]

    listen_once = processor.process("послушай один раз")
    assert listen_once["intent"] == "microphone.listen.once"
    assert "Vosk skeleton готов" in listen_once["response"]
    assert manager.get_microphone_status()["permission_granted"] is False

    plan = processor.process("план vosk")
    assert plan["intent"] == "speech.backend.vosk.plan"


def test_vosk_manual_status_commands_use_safe_recognition_gate():
    processor, manager = create_voice_enabled_processor()

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("status command must stay read-only")

    manager.microphone_adapter.start_listening = fail_if_called
    manager.microphone_adapter.read_text = fail_if_called
    manager.listen_once_from_microphone = fail_if_called
    manager.use_vosk_backend = fail_if_called
    manager.get_vosk_backend_status = lambda: {
        "model_path": None,
        "vosk_package_available": False,
    }

    for command in (
        "статус vosk",
        "проверить vosk",
        "готов ли vosk",
        "готово ли распознавание",
        "статус распознавания",
        "проверка распознавания",
        "локальное распознавание",
        "готово ли локальное распознавание",
    ):
        result = processor.process(command)

        assert result["intent"] == "speech.backend.vosk.recognition.status"
        assert "Локальное распознавание Vosk пока недоступно." in result["response"]
        assert (
            "Локальное распознавание Vosk сейчас разрешено: нет."
            in result["response"]
        )
        assert "Причины:" in result["response"]
        assert "Пакет vosk не установлен." in result["response"]
        assert "Путь к модели Vosk не указан." in result["response"]
        assert "Следующие шаги:" in result["response"]
        assert "Установите пакет vosk вручную" in result["response"]
        assert "Скачайте модель Vosk вручную" in result["response"]
        assert "Микрофон не запускается автоматически." in result["response"]
        assert (
            "Постоянное прослушивание пока не связано с реальным распознаванием."
            in result["response"]
        )

    assert manager.microphone_adapter.get_state() == "disabled"
    assert manager.get_speech_backend_name() == "none"


def test_vosk_dry_run_commands_return_safe_russian_response():
    processor, manager = create_voice_enabled_processor()

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("dry run command must not touch real microphone or runtime")

    manager.microphone_adapter.start_listening = fail_if_called
    manager.microphone_adapter.read_text = fail_if_called
    manager.listen_once_from_microphone = fail_if_called
    manager.use_vosk_backend = fail_if_called
    manager.get_vosk_backend_status = lambda: {
        "model_path": None,
        "vosk_package_available": False,
    }
    processor._get_vosk_runtime_loader = fail_if_called

    for command in (
        "пробный запуск vosk",
        "тест vosk",
        "тест распознавания",
        "пробное распознавание",
        "проверить локальное распознавание",
        "dry run vosk",
    ):
        processor.vosk_recognition_dry_run = None
        result = processor.process(command)

        assert result["intent"] == "speech.backend.vosk.recognition.dry_run"
        assert "Пробный запуск Vosk заблокирован." in result["response"]
        assert result["response"].count("Причины:") == 1
        assert result["response"].count("Безопасность:") == 1
        assert "микрофон не запускался" in result["response"]
        assert "настоящая модель Vosk не загружалась" in result["response"]
        assert "реальное распознавание не запускалось" in result["response"]
        assert "Пакет vosk не установлен." in result["response"]
        assert "Путь к модели Vosk не указан." in result["response"]
        assert result["response"].count("Пакет vosk не установлен.") == 1
        assert result["response"].count("Путь к модели Vosk не указан.") == 1

    assert manager.microphone_adapter.get_state() == "disabled"
    assert manager.get_speech_backend_name() == "none"


def test_vosk_dry_run_command_can_report_fake_success_without_real_capture():
    from voice import VoskLocalRecognitionDryRun

    processor = CommandProcessor(
        vosk_recognition_dry_run=VoskLocalRecognitionDryRun(
            gate_checker=lambda: {
                "allowed": True,
                "blockers": [],
                "warnings": [],
                "next_steps": [],
            },
            recognizer=lambda _fake_audio: "тестовая команда",
        )
    )

    result = processor.process("тест vosk")

    assert result["intent"] == "speech.backend.vosk.recognition.dry_run"
    assert "Пробный запуск Vosk выполнен." in result["response"]
    assert "Тестовый распознанный текст: тестовая команда" in result["response"]
    assert "микрофон не запускался" in result["response"]
    assert "настоящая модель Vosk не загружалась" in result["response"]


def test_one_shot_vosk_bridge_command_aliases_return_safe_response():
    processor = CommandProcessor()

    for command in ("голосовой мост", "мост vosk", "тест голосового моста"):
        result = processor.process(command)

        assert result["intent"] == "speech.backend.vosk.one_shot_bridge"
        assert "One-shot Vosk bridge" in result["response"]
        assert "Реальный микрофон не запускался автоматически." in result["response"]
        assert "Постоянное прослушивание не использовалось." in result["response"]
        assert "Аудио не отправлялось в облако." in result["response"]
        assert "выполнение команд будут подключаться отдельной задачей" in result["response"]


def test_one_shot_vosk_bridge_recognized_text_is_not_executed_as_command():
    class FakeBridge:
        def run_once(self, explicit_one_shot_requested=False):
            assert explicit_one_shot_requested is True
            return OneShotVoskRecognitionBridgeResult(
                allowed=True,
                completed=True,
                blocked=False,
                simulated=True,
                recognized_text="статус системы",
            )

    processor = CommandProcessor(one_shot_vosk_recognition_bridge=FakeBridge())

    result = processor.process("проверить мост распознавания")

    assert result["intent"] == "speech.backend.vosk.one_shot_bridge"
    assert "Распознанный текст: статус системы" in result["response"]
    assert "Активных сервисов" not in result["response"]
    assert "Распознанный текст не выполнялся как команда." in result["response"]


def test_one_shot_vosk_real_recognition_command_aliases_return_safe_response():
    class FakeRealRecognition:
        def __init__(self):
            self.calls = 0

        def run_once(self, explicit_one_shot_requested=False):
            assert explicit_one_shot_requested is True
            self.calls += 1
            return OneShotVoskRealRecognitionResult(
                allowed=True,
                completed=True,
                blocked=False,
                recognized_text="статус системы",
                capture_seconds=2,
            )

    recognizer = FakeRealRecognition()
    processor = CommandProcessor(one_shot_vosk_real_recognition=recognizer)

    for command in (
        "распознай голос один раз",
        "реальное распознавание vosk",
        "проверить голос через vosk",
    ):
        result = processor.process(command)

        assert result["intent"] == "system.status"
        assert "Распознавание завершено." in result["response"]
        assert "Я распознал безопасную голосовую команду: \"статус системы\"." in result["response"]
        assert "Выполняю: статус системы" in result["response"]
        assert "без дополнительного подтверждения" in result["response"]
        assert "read-only" in result["response"]
        assert processor.has_pending_voice_command() is False
        assert "Активных сервисов" in result["response"]

    assert recognizer.calls == 3


def test_one_shot_vosk_real_recognition_handles_unavailable_dependencies_safely():
    class FakeRealRecognition:
        def run_once(self, explicit_one_shot_requested=False):
            assert explicit_one_shot_requested is True
            return OneShotVoskRealRecognitionResult(
                allowed=False,
                completed=False,
                blocked=True,
                recognized_text=None,
                capture_seconds=0,
                reasons=[
                    "Пакет vosk не установлен или недоступен для текущего Python."
                ],
                next_steps=[
                    "Установите Vosk вручную в совместимое окружение.",
                ],
                safety_notes=[
                    "Микрофон не запускался.",
                    "Постоянное прослушивание не использовалось.",
                    "Аудио не отправлялось в облако.",
                    "Распознанный текст не выполнялся как команда.",
                ],
            )

    processor = CommandProcessor(one_shot_vosk_real_recognition=FakeRealRecognition())

    result = processor.process("тест реального распознавания")

    assert result["intent"] == "speech.backend.vosk.one_shot_real_recognition"
    assert "Реальное распознавание Vosk заблокировано." in result["response"]
    assert "Пакет vosk не установлен" in result["response"]
    assert "Установите Vosk вручную" in result["response"]
    assert "Безопасность:" in result["response"]
    assert "Микрофон не запускался." in result["response"]


def test_existing_bridge_commands_still_do_not_start_real_recognition():
    class FailRealRecognition:
        def run_once(self, explicit_one_shot_requested=False):
            raise AssertionError("bridge commands must not start real recognition")

    processor = CommandProcessor(
        one_shot_vosk_real_recognition=FailRealRecognition()
    )

    for command in (
        "голосовой мост",
        "мост vosk",
        "тест голосового моста",
        "проверить мост распознавания",
    ):
        result = processor.process(command)

        assert result["intent"] == "speech.backend.vosk.one_shot_bridge"
        assert "One-shot Vosk bridge" in result["response"]


def test_vosk_manual_setup_commands_return_safe_russian_instructions():
    processor = CommandProcessor()

    for command in ("как настроить vosk", "инструкция vosk", "настройка распознавания"):
        result = processor.process(command)

        assert result["intent"] == "speech.backend.vosk.installation.guide"
        assert "Vosk автоматически не устанавливается" in result["response"]
        assert "Команда для ручной установки" in result["response"]
        assert "модель не скачивается" in result["response"]
        assert "микрофон не включается" in result["response"]


def test_vosk_model_path_status_reports_missing_path_without_writes(tmp_path):
    processor, manager = create_voice_enabled_processor(tmp_path)

    result = processor.process("путь модели vosk")

    assert result["intent"] == "speech.backend.vosk.model.path.status"
    assert result["response"] == "Путь к модели Vosk пока не указан."
    assert manager.get_vosk_backend_status()["model_path"] is None


def test_vosk_model_path_status_reports_configured_path_read_only(tmp_path):
    processor, manager = create_voice_enabled_processor(tmp_path)
    model_dir = tmp_path / "vosk-model-small-ru"
    model_dir.mkdir()
    configured_path = str(model_dir)
    manager.configure_vosk_model_path(configured_path)

    result = processor.process("путь модели vosk")
    alias_result = processor.process("где модель vosk")
    check_result = processor.process("проверить путь модели vosk")
    which_result = processor.process("какой путь модели vosk")

    assert result["intent"] == "speech.backend.vosk.model.path.status"
    assert configured_path in result["response"]
    assert "модель не загружается" in result["response"]
    assert "микрофон не запускается" in result["response"]
    assert alias_result["intent"] == "speech.backend.vosk.model.path.status"
    assert configured_path in alias_result["response"]
    assert check_result["intent"] == "speech.backend.vosk.model.path.status"
    assert configured_path in check_result["response"]
    assert which_result["intent"] == "speech.backend.vosk.model.path.status"
    assert configured_path in which_result["response"]
    assert manager.get_vosk_backend_status()["model_path"] == configured_path


def test_vosk_model_path_status_reports_missing_and_not_directory_cases(tmp_path):
    processor, manager = create_voice_enabled_processor(tmp_path)
    missing_path = str(tmp_path / "missing-model")
    manager.configure_vosk_model_path(missing_path)

    missing = processor.process("проверить путь модели vosk")

    assert missing["intent"] == "speech.backend.vosk.model.path.status"
    assert missing["response"] == (
        f"Путь к модели Vosk указан, но папка не найдена: {missing_path}"
    )

    file_path = tmp_path / "vosk-model-file"
    file_path.write_text("not a directory", encoding="utf-8")
    manager.configure_vosk_model_path(str(file_path))

    not_directory = processor.process("проверить путь модели vosk")

    assert not_directory["intent"] == "speech.backend.vosk.model.path.status"
    assert not_directory["response"] == (
        f"Путь к модели Vosk указан, но это не папка: {file_path}"
    )


def test_vosk_model_path_set_commands_save_safely_and_report_path_state(tmp_path):
    processor, manager = create_voice_enabled_processor(tmp_path)
    model_dir = tmp_path / "vosk model small ru"
    model_dir.mkdir()

    for command_prefix in (
        "установи путь модели vosk",
        "задай путь модели vosk",
        "измени путь модели vosk",
        "сохрани путь модели vosk",
        "путь модели vosk",
    ):
        result = processor.process(f"{command_prefix} {model_dir}")

        assert result["intent"] == "speech.backend.vosk.model.path.set"
        assert manager.get_vosk_backend_status()["model_path"] == str(model_dir)
        assert result["response"] == (
            "Путь к модели Vosk сохранен. Папка найдена.\n"
            "Распознавание речи не запускается автоматически. "
            "Выполните команду 'статус vosk', чтобы проверить готовность."
        )


def test_vosk_model_path_set_quoted_and_missing_paths(tmp_path):
    processor, manager = create_voice_enabled_processor(tmp_path)
    quoted_path = tmp_path / "quoted vosk model"
    quoted_path.mkdir()

    quoted = processor.process(f'установи путь модели vosk "{quoted_path}"')

    assert quoted["intent"] == "speech.backend.vosk.model.path.set"
    assert manager.get_vosk_backend_status()["model_path"] == str(quoted_path)
    assert "Папка найдена" in quoted["response"]

    missing_path = tmp_path / "missing model with spaces"
    missing = processor.process(f"сохрани путь модели vosk {missing_path}")

    assert missing["intent"] == "speech.backend.vosk.model.path.set"
    assert manager.get_vosk_backend_status()["model_path"] == str(missing_path)
    assert "папка пока не найдена" in missing["response"]
    assert "Распознавание речи не запускается автоматически" in missing["response"]


def test_vosk_model_path_set_empty_command_is_rejected(tmp_path):
    processor, manager = create_voice_enabled_processor(tmp_path)

    for command in (
        "установи путь модели vosk",
        'установи путь модели vosk ""',
    ):
        result = processor.process(command)

        assert result["intent"] == "speech.backend.vosk.model_path.missing"
        assert result["response"] == (
            "Не удалось сохранить путь к модели Vosk: путь не указан."
        )
        assert manager.get_vosk_backend_status()["model_path"] is None


def test_vosk_model_path_set_reports_not_directory(tmp_path):
    processor, manager = create_voice_enabled_processor(tmp_path)
    file_path = tmp_path / "vosk-model-file"
    file_path.write_text("not a directory", encoding="utf-8")

    result = processor.process(f"установи путь модели vosk {file_path}")

    assert result["intent"] == "speech.backend.vosk.model.path.set"
    assert manager.get_vosk_backend_status()["model_path"] == str(file_path)
    assert "указанный путь не является папкой" in result["response"]


def test_vosk_model_path_clear_aliases_clear_configured_path(tmp_path):
    processor, manager = create_voice_enabled_processor(tmp_path)

    for command in (
        "очисти путь модели vosk",
        "сбрось путь модели vosk",
        "удали путь модели vosk",
        "удалить путь модели vosk",
    ):
        manager.configure_vosk_model_path(str(tmp_path))

        result = processor.process(command)

        assert result["intent"] == "speech.backend.vosk.model.path.cleared"
        assert manager.get_vosk_backend_status()["model_path"] is None
        assert result["response"] == (
            "Путь к модели Vosk очищен.\n"
            "Распознавание речи не запускается автоматически. "
            "Выполните команду 'статус vosk', чтобы проверить готовность."
        )


def test_vosk_model_path_commands_do_not_start_capture_or_load_runtime(tmp_path):
    processor, manager = create_voice_enabled_processor(tmp_path)

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("path commands must remain configuration-only")

    manager.microphone_adapter.start_listening = fail_if_called
    manager.microphone_adapter.read_text = fail_if_called
    manager.listen_once_from_microphone = fail_if_called
    manager.use_vosk_backend = fail_if_called
    processor._get_vosk_runtime_loader = fail_if_called

    for command in (
        "путь модели vosk",
        f"установи путь модели vosk {tmp_path}",
        "где модель vosk",
        "очисти путь модели vosk",
    ):
        result = processor.process(command)
        assert result["intent"].startswith("speech.backend.vosk.model.path")

    assert manager.microphone_adapter.get_state() == "disabled"


def test_vosk_preflight_and_in_memory_model_path_commands(tmp_path):
    processor, manager = create_voice_enabled_processor(tmp_path)

    for command in (
        "preflight vosk",
        "проверка vosk",
        "диагностика vosk",
        "проверить воск",
        "диагностика воск",
    ):
        preflight = processor.process(command)
        assert preflight["intent"] == "speech.backend.vosk.preflight"
        assert "микрофон не включается" in preflight["response"]

    for command in (
        "модель vosk",
        "статус модели vosk",
        "проверить модель vosk",
        "модель воск",
        "статус модели воск",
    ):
        model = processor.process(command)
        assert model["intent"] == "speech.backend.vosk.model.status"
        assert "путь к модели не задан" in model["response"]

    configured_path = r"C:\models\vosk-model-small-ru"
    configured = processor.process(
        f"сохранить путь модели vosk {configured_path}"
    )
    assert configured["intent"] == "speech.backend.vosk.model.path.set"
    assert manager.get_vosk_backend_status()["model_path"] == configured_path

    settings = processor.process("настройки vosk")
    assert settings["intent"] == "speech.backend.vosk.settings"
    assert configured_path in settings["response"]

    for command in (
        "требования vosk",
        "что не хватает vosk",
        "чего не хватает vosk",
        "требования воск",
    ):
        missing = processor.process(command)
        assert missing["intent"] == "speech.backend.vosk.requirements"

    configured = processor.process(f"установить путь модели vosk {tmp_path}")
    assert configured["intent"] == "speech.backend.vosk.model.path.set"
    assert manager.get_vosk_preflight()["model_path_exists"] is True
    assert "Путь к модели Vosk сохранен" in configured["response"]

    language_before = processor.process("язык vosk")
    assert language_before["intent"] == "speech.backend.vosk.language.status"
    assert "ru" in language_before["response"]

    language = processor.process("установить язык vosk ru")
    assert language["intent"] == "speech.backend.vosk.language.set"
    assert manager.get_vosk_backend_status()["language"] == "ru"

    cleared = processor.process("очистить путь модели vosk")
    assert cleared["intent"] == "speech.backend.vosk.model.path.cleared"
    assert manager.get_vosk_backend_status()["model_path"] is None
    assert tmp_path.is_dir()


def sample_profile():
    return {
        "user_name": "Исмаил",
        "preferred_name": "Исмаил",
        "assistant_name": "JARVIS",
        "language": "ru",
        "communication_style": "естественный, понятный, не робот",
        "main_use_cases": ["работа", "обучение"],
    }


def test_creation_without_profile():
    processor = CommandProcessor()

    assert processor.user_profile == {}


def test_creation_with_profile():
    processor = CommandProcessor(sample_profile())

    assert processor.user_profile["preferred_name"] == "Исмаил"


def test_user_identity_command():
    result = CommandProcessor(sample_profile()).process("кто я")

    assert result["intent"] == "user.identity"
    assert result["should_exit"] is False
    assert "Исмаил" in result["response"]


def test_assistant_identity_command():
    result = CommandProcessor(sample_profile()).process("как тебя зовут")

    assert result["intent"] == "assistant.identity"
    assert result["should_exit"] is False
    assert result["response"] == "Исмаил, меня зовут JARVIS."
    assert "JARVIS" in result["response"]


def test_assistant_name_view_aliases_return_current_name():
    for command in ("как тебя зовут", "имя ассистента"):
        result = CommandProcessor(sample_profile()).process(command)

        assert result["intent"] == "assistant.identity"
        assert result["response"] == "Исмаил, меня зовут JARVIS."


def test_profile_command():
    result = CommandProcessor(sample_profile()).process("покажи профиль")

    assert result["intent"] == "user.profile"
    assert result["should_exit"] is False
    assert "Имя пользователя: Исмаил" in result["response"]
    assert "Имя ассистента: JARVIS" in result["response"]
    assert "Язык: ru" in result["response"]
    assert "Стиль общения: естественный, понятный, не робот" in result["response"]
    assert "работа, обучение" in result["response"]


def test_help_command():
    result = CommandProcessor(sample_profile()).process("что ты умеешь")

    assert result["intent"] == "assistant.help"
    assert result["should_exit"] is False
    assert "работать с профилем" in result["response"]
    assert "имя ассистента можно посмотреть, изменить или сбросить" in result["response"]
    assert "режимы микрофона" in result["response"]
    assert "Vosk" in result["response"]
    assert "реальное one-shot распознавание Vosk по явной команде" in result["response"]
    assert "Неизвестные и рискованные голосовые команды всё ещё требуют подтверждения да / нет" in result["response"]
    assert "ожидающую голосовую команду можно проверить или отменить" in result["response"]
    assert "последнее голосовое распознавание" in result["response"]
    assert "историю голосовых команд за сессию" in result["response"]
    assert "очистить историю голоса" in result["response"]
    assert "Рискованные действия не обходят безопасность" in result["response"]
    assert "постоянное прослушивание не связано" in result["response"]
    assert "Реальный захват микрофона автоматически не включается" in result["response"]
    assert "будут добавлены позже" not in result["response"]


def test_help_alias_command():
    result = CommandProcessor(sample_profile()).process("помощь")

    assert result["intent"] == "assistant.help"
    assert result["should_exit"] is False
    assert "пробный запуск Vosk" in result["response"]
    assert "симуляция голосовой команды" in result["response"]
    assert "безопасные голосовые команды" in result["response"]
    assert "последнее голосовое распознавание" in result["response"]
    assert "Неизвестные и рискованные голосовые команды" in result["response"]
    assert "Для выхода напишите: выход" in result["response"]


def test_voice_recognition_correction_commands():
    processor = CommandProcessor()

    added = processor.process("я сказал не статуя система, а статус системы")
    listed = processor.process("голосовые исправления")
    count = processor.process("сколько голосовых исправлений")
    cleared = processor.process("очистить голосовые исправления")
    empty = processor.process("голосовые исправления")

    assert added["intent"] == "voice.recognition_correction.added"
    assert "Было: статуя система" in added["response"]
    assert "Должно быть: статус системы" in added["response"]
    assert "не обходит проверку команд" in added["response"]
    assert listed["intent"] == "voice.recognition_correction.list"
    assert "1. статуя система -> статус системы" in listed["response"]
    assert count["intent"] == "voice.recognition_correction.count"
    assert count["response"] == "Голосовых исправлений в текущей сессии: 1."
    assert cleared["intent"] == "voice.recognition_correction.cleared"
    assert cleared["response"] == "Голосовые исправления текущей сессии очищены."
    assert empty["response"] == "В текущей сессии нет голосовых исправлений."


def test_voice_recognition_correction_arrow_command():
    processor = CommandProcessor()

    result = processor.process(
        "исправь распознавание: статуя система -> статус системы"
    )

    assert result["intent"] == "voice.recognition_correction.added"
    assert processor.voice_recognition_correction_manager.count() == 1


def test_help_mentions_voice_corrections():
    response = CommandProcessor(sample_profile()).process("помощь")["response"]

    assert "исправление распознавания" in response
    assert "я сказал не X, а Y" in response
    assert "текущей сессии" in response


def test_voice_history_commands_return_empty_responses():
    processor = CommandProcessor()

    for command in (
        "последнее распознавание",
        "последняя голосовая команда",
        "что ты услышал",
        "что ты распознал",
    ):
        result = processor.process(command)

        assert result["intent"] == "voice.history.last"
        assert result["response"] == "В этой сессии ещё нет голосовых распознаваний."

    history = processor.process("история голосовых команд")
    assert history["intent"] == "voice.history.list"
    assert history["response"] == "В этой сессии ещё нет голосовых распознаваний."

    count = processor.process("сколько голосовых команд")
    assert count["intent"] == "voice.history.count"
    assert count["response"] == "В этой сессии записано голосовых событий: 0."


def test_voice_history_clear_command_returns_success():
    processor = CommandProcessor()
    processor.voice_command_history.add_entry(
        recognized_text="статус системы",
        canonical_command="статус системы",
        status="allowlisted_executed",
    )

    result = processor.process("очистить историю голосовых команд")

    assert result["intent"] == "voice.history.cleared"
    assert result["response"] == "История голосовых команд за текущую сессию очищена."
    assert processor.voice_command_history.count() == 0


def test_safe_voice_command_allowlist_status_commands():
    processor = CommandProcessor()

    for command in (
        "список безопасных голосовых команд",
        "безопасные голосовые команды",
        "какие голосовые команды без подтверждения",
    ):
        result = processor.process(command)

        assert result["intent"] == "voice.safe_allowlist.status"
        assert "Безопасные голосовые команды без подтверждения" in result["response"]
        assert "Read-only" in result["response"]
        assert "статус системы" in result["response"]
        assert "статуя система" in result["response"]
        assert "помощь" in result["response"]
        assert "Safe aliases" in result["response"]
        assert "только явные варианты для read-only команд" in result["response"]
        assert "Широкое угадывание и fuzzy matching" in result["response"]
        assert "Все остальные голосовые команды требуют подтверждения" in result["response"]
        assert "Все неизвестные и рискованные голосовые команды всё ещё требуют подтверждения" in result["response"]
        assert "Рискованные действия не обходят безопасность" in result["response"]
        assert "CommandProcessor" in result["response"]
        assert "ActionRouter" in result["response"]
        assert "- запомни" not in result["response"]
        assert "удали" not in result["response"]
        assert "установи" not in result["response"]


def test_greeting_command():
    result = CommandProcessor(sample_profile()).process("привет")

    assert result["intent"] == "assistant.greeting"
    assert result["should_exit"] is False
    assert result["response"] == "Исмаил, привет. JARVIS работает и готов помочь."


def test_greeting_salam_command():
    result = CommandProcessor(sample_profile()).process("салам")

    assert result["intent"] == "assistant.greeting"
    assert result["should_exit"] is False
    assert "JARVIS работает и готов помочь" in result["response"]


def test_change_assistant_name_to_jarvis_persists_in_profile():
    with TemporaryDirectory() as tmp_dir:
        manager = UserProfileManager(Path(tmp_dir) / "profile.json")
        profile = manager.save_profile(sample_profile())
        processor = CommandProcessor(profile, user_profile_manager=manager)

        result = processor.process("измени имя ассистента на JARVIS")

        assert result["intent"] == "assistant.name.changed"
        assert result["response"] == (
            "Исмаил, имя ассистента изменено. Теперь меня зовут JARVIS."
        )
        assert manager.get_assistant_name() == "JARVIS"


def test_change_assistant_name_aliases_update_greeting():
    processor = CommandProcessor(sample_profile())

    first = processor.process("назови себя ВанДам")
    identity = processor.process("как тебя зовут")
    greeting = processor.process("привет")

    assert first["intent"] == "assistant.name.changed"
    assert first["response"] == (
        "Исмаил, имя ассистента изменено. Теперь меня зовут ВанДам."
    )
    assert identity["response"] == "Исмаил, меня зовут ВанДам."
    assert greeting["response"] == "Исмаил, привет. ВанДам работает и готов помочь."


def test_now_your_name_is_alias_changes_assistant_name():
    processor = CommandProcessor(sample_profile())

    result = processor.process("теперь тебя зовут Али")

    assert result["intent"] == "assistant.name.changed"
    assert processor.process("имя ассистента")["response"] == "Исмаил, меня зовут Али."


def test_reset_assistant_name_command_returns_default():
    processor = CommandProcessor(sample_profile())
    processor.process("назови себя ВанДам")

    result = processor.process("сбрось имя ассистента")

    assert result["intent"] == "assistant.name.reset"
    assert result["response"] == (
        "Исмаил, имя ассистента сброшено. Теперь меня зовут JARVIS."
    )
    assert processor.process("как тебя зовут")["response"] == "Исмаил, меня зовут JARVIS."


def test_invalid_assistant_name_does_not_change_name():
    processor = CommandProcessor(sample_profile())

    for command in (
        "назови себя",
        "назови себя Али/Бот",
        "назови себя " + ("А" * 41),
        "назови себя Али\nБот",
    ):
        result = processor.process(command)

        assert result["intent"] == "assistant.name.invalid"
        assert result["should_exit"] is False
        assert "имя ассистента не изменено" in result["response"]
        assert processor.dialogue_manager.get_assistant_name() == "JARVIS"


def test_version_command():
    result = CommandProcessor(sample_profile()).process("версия")

    assert result["intent"] == "system.version"
    assert result["should_exit"] is False
    assert "v0.2" in result["response"]


def test_show_version_command():
    result = CommandProcessor(sample_profile()).process("покажи версию")

    assert result["intent"] == "system.version"
    assert result["should_exit"] is False
    assert "текущая версия JARVIS OS" in result["response"]


def test_system_status_command():
    result = CommandProcessor(sample_profile()).process("статус системы")

    assert result["intent"] == "system.status"
    assert result["should_exit"] is False
    assert "система работает" in result["response"]
    assert "Активных сервисов: 9" in result["response"]


def test_services_command():
    result = CommandProcessor(sample_profile()).process("покажи сервисы")

    assert result["intent"] == "system.services"
    assert result["should_exit"] is False
    assert "активные системные сервисы" in result["response"]
    assert "1. logger" in result["response"]
    assert "8. microphone_input_adapter" in result["response"]
    assert "9. voice_input_manager" in result["response"]


def test_voice_status_command():
    result = CommandProcessor(sample_profile()).process("голос")

    assert result["intent"] == "voice.status"
    assert result["should_exit"] is False
    assert "голосовой фундамент есть" in result["response"]
    assert "микрофон пока не включается" in result["response"]


def test_voice_status_alias_command():
    result = CommandProcessor(sample_profile()).process("статус голоса")

    assert result["intent"] == "voice.status"
    assert result["should_exit"] is False


def test_voice_enable_command():
    result = CommandProcessor(sample_profile()).process("включи голос")

    assert result["intent"] == "voice.enable"
    assert result["should_exit"] is False
    assert "голосовой ввод подготовлен" in result["response"]
    assert "реальный микрофон пока не включается" in result["response"]


def test_voice_disable_command():
    result = CommandProcessor(sample_profile()).process("отключи голос")

    assert result["intent"] == "voice.disable"
    assert result["should_exit"] is False
    assert "голосовой ввод отключён" in result["response"]
    assert "не слушаю микрофон" in result["response"]


def test_show_commands_command():
    result = CommandProcessor(sample_profile()).process("покажи команды")

    assert result["intent"] == "assistant.commands"
    assert result["should_exit"] is False
    assert "Профиль:" in result["response"]
    assert "Память:" in result["response"]
    assert "Система:" in result["response"]


def test_commands_list_command():
    result = CommandProcessor(sample_profile()).process("список команд")

    assert result["intent"] == "assistant.commands"
    assert result["should_exit"] is False
    assert "- покажи сервисы" in result["response"]


def test_exit_command():
    result = CommandProcessor(sample_profile()).process("выход")

    assert result["intent"] == "system.exit"
    assert result["should_exit"] is True
    assert result["response"] == "Хорошо, Исмаил. Завершаю работу."


def test_unknown_command():
    result = CommandProcessor(sample_profile()).process("запусти космический режим")

    assert result["intent"] == "unknown"
    assert result["should_exit"] is False
    assert result["category"] == "idea"
    assert result["risk_level"] == "unknown"
    assert "идею для будущего" in result["response"]


def test_confirmation_words_without_pending_do_not_become_ideas():
    processor = CommandProcessor(sample_profile())

    for command in ("да", "нет"):
        result = processor.process(command)

        assert result["intent"] == "voice.pending_command.none"
        assert result["response"] == "Нет голосовой команды, ожидающей подтверждения."
        assert "идею для будущего" not in result["response"]
        assert processor.voice_command_history.count() == 0


def test_empty_command():
    result = CommandProcessor(sample_profile()).process("   ")

    assert result["intent"] == "empty"
    assert result["should_exit"] is False
    assert result["response"] == (
        "Исмаил, я не услышал команду. Повторите, пожалуйста."
    )


def test_stop_command_is_voice_cancel_without_exit():
    result = CommandProcessor(sample_profile()).process("стоп")

    assert result["intent"] == "voice.confirmation.none"
    assert result["should_exit"] is False
    assert "нет голосового действия" in result["response"]


def test_normalizes_command():
    result = CommandProcessor(sample_profile()).process("  Кто Я  ")

    assert result["intent"] == "user.identity"


def test_send_email_requires_confirmation():
    result = CommandProcessor(sample_profile()).process("отправь письмо")

    assert result["intent"] == "action.confirmation_required"
    assert result["category"] == "confirmation_required"
    assert result["requires_confirmation"] is True
    assert result["risk_level"] == "medium"
    assert "требует подтверждения" in result["response"]


def test_delete_file_requires_confirmation():
    result = CommandProcessor(sample_profile()).process("удали файл")

    assert result["intent"] == "action.confirmation_required"
    assert result["category"] == "confirmation_required"
    assert result["requires_confirmation"] is True
    assert result["risk_level"] == "medium"


def test_delete_system32_is_forbidden():
    result = CommandProcessor(sample_profile()).process("удали system32")

    assert result["intent"] == "action.forbidden"
    assert result["category"] == "forbidden"
    assert result["allowed"] is False
    assert result["risk_level"] == "high"
    assert "не могу выполнить" in result["response"]


def test_unknown_action_is_future_idea_without_execution():
    result = CommandProcessor(sample_profile()).process("настрой утренний сценарий")

    assert result["intent"] == "unknown"
    assert result["category"] == "idea"
    assert result["allowed"] is False
    assert result["requires_confirmation"] is False
    assert result["risk_level"] == "unknown"


def test_add_idea_command():
    with TemporaryDirectory() as tmp_dir:
        idea_manager = IdeaManager(Path(tmp_dir) / "ideas.json")
        processor = CommandProcessor(sample_profile(), idea_manager=idea_manager)

        result = processor.process("добавь идею научиться видеть экран")

        assert result["intent"] == "idea.add"
        assert result["should_exit"] is False
        assert idea_manager.count_ideas() == 1
        assert idea_manager.list_ideas()[0]["title"] == "научиться видеть экран"
        assert "я сохранил идею: научиться видеть экран" in result["response"]


def test_remember_idea_command():
    with TemporaryDirectory() as tmp_dir:
        idea_manager = IdeaManager(Path(tmp_dir) / "ideas.json")
        processor = CommandProcessor(sample_profile(), idea_manager=idea_manager)

        result = processor.process("запомни идею сделать голосовое управление")

        assert result["intent"] == "idea.add"
        assert result["should_exit"] is False
        assert idea_manager.list_ideas()[0]["title"] == "сделать голосовое управление"


def test_list_ideas_command():
    with TemporaryDirectory() as tmp_dir:
        idea_manager = IdeaManager(Path(tmp_dir) / "ideas.json")
        idea_manager.add_idea("научиться видеть экран")
        processor = CommandProcessor(sample_profile(), idea_manager=idea_manager)

        result = processor.process("покажи идеи")

        assert result["intent"] == "idea.list"
        assert result["should_exit"] is False
        assert "1. научиться видеть экран" in result["response"]


def test_add_memory_command_remember_that():
    with TemporaryDirectory() as tmp_dir:
        memory_manager = LocalMemoryManager(Path(tmp_dir) / "memory.json")
        processor = CommandProcessor(sample_profile(), memory_manager=memory_manager)

        result = processor.process("запомни что я работаю с документами")

        assert result["intent"] == "memory.add"
        assert result["should_exit"] is False
        assert memory_manager.count_memories() == 1
        assert memory_manager.list_memories()[0]["content"] == "я работаю с документами"


def test_add_memory_command_save_to_memory():
    with TemporaryDirectory() as tmp_dir:
        memory_manager = LocalMemoryManager(Path(tmp_dir) / "memory.json")
        processor = CommandProcessor(sample_profile(), memory_manager=memory_manager)

        result = processor.process("сохрани в память что JARVIS должен быть расширяемым")

        assert result["intent"] == "memory.add"
        assert result["should_exit"] is False
        assert memory_manager.list_memories()[0]["content"] == "JARVIS должен быть расширяемым".lower()


def test_list_memory_command_show_memory():
    with TemporaryDirectory() as tmp_dir:
        memory_manager = LocalMemoryManager(Path(tmp_dir) / "memory.json")
        memory_manager.add_memory("любишь зелёный цвет")
        processor = CommandProcessor(sample_profile(), memory_manager=memory_manager)

        result = processor.process("покажи память")

        assert result["intent"] == "memory.list"
        assert result["should_exit"] is False
        assert "1. любишь зелёный цвет" in result["response"]


def test_memory_recall_what_was_remembered_command():
    with TemporaryDirectory() as tmp_dir:
        memory_manager = LocalMemoryManager(Path(tmp_dir) / "memory.json")
        memory_manager.add_memory("любишь зелёный цвет")
        memory_manager.add_memory("JARVIS должен быть расширяемым")
        processor = CommandProcessor(sample_profile(), memory_manager=memory_manager)

        result = processor.process("что ты запомнил")

        assert result["intent"] == "memory.list"
        assert result["should_exit"] is False
        assert "1. любишь зелёный цвет" in result["response"]
        assert "2. JARVIS должен быть расширяемым" in result["response"]


def test_memory_recall_empty_memory_is_safe():
    with TemporaryDirectory() as tmp_dir:
        memory_manager = LocalMemoryManager(Path(tmp_dir) / "memory.json")
        processor = CommandProcessor(sample_profile(), memory_manager=memory_manager)

        result = processor.process("локальная память")

        assert result["intent"] == "memory.list"
        assert result["should_exit"] is False
        assert result["response"] == "В локальной памяти пока нет сохранённых записей."


def test_list_memory_command_what_do_you_remember():
    with TemporaryDirectory() as tmp_dir:
        memory_manager = LocalMemoryManager(Path(tmp_dir) / "memory.json")
        processor = CommandProcessor(sample_profile(), memory_manager=memory_manager)

        result = processor.process("что ты помнишь")

        assert result["intent"] == "memory.list"
        assert result["should_exit"] is False


def test_show_memory_alias_still_works():
    with TemporaryDirectory() as tmp_dir:
        memory_manager = LocalMemoryManager(Path(tmp_dir) / "memory.json")
        memory_manager.add_memory("локальный факт")
        processor = CommandProcessor(sample_profile(), memory_manager=memory_manager)

        result = processor.process("покажи память")

        assert result["intent"] == "memory.list"
        assert "1. локальный факт" in result["response"]


def test_search_memory_command():
    with TemporaryDirectory() as tmp_dir:
        memory_manager = LocalMemoryManager(Path(tmp_dir) / "memory.json")
        memory_manager.add_memory("я работаю с документами")
        processor = CommandProcessor(sample_profile(), memory_manager=memory_manager)

        result = processor.process("найди в памяти документы")

        assert result["intent"] == "memory.search"
        assert result["should_exit"] is False
        assert "1. я работаю с документами" in result["response"]


def test_memory_count_command():
    with TemporaryDirectory() as tmp_dir:
        memory_manager = LocalMemoryManager(Path(tmp_dir) / "memory.json")
        memory_manager.add_memory("локальный факт")
        processor = CommandProcessor(sample_profile(), memory_manager=memory_manager)

        result = processor.process("сколько ты помнишь")

        assert result["intent"] == "memory.count"
        assert result["should_exit"] is False
        assert "сохранено записей: 1" in result["response"]


def test_idea_count_commands():
    with TemporaryDirectory() as tmp_dir:
        idea_manager = IdeaManager(Path(tmp_dir) / "ideas.json")
        idea_manager.add_idea("первая идея")
        idea_manager.add_idea("вторая идея")
        processor = CommandProcessor(sample_profile(), idea_manager=idea_manager)

        for command in ("сколько идей", "количество идей", "сколько сохранено идей"):
            result = processor.process(command)

            assert result["intent"] == "idea.count"
            assert result["should_exit"] is False
            assert result["response"] == "Исмаил, сохранено идей: 2."


def test_recent_memory_command():
    with TemporaryDirectory() as tmp_dir:
        memory_manager = LocalMemoryManager(Path(tmp_dir) / "memory.json")
        memory_manager.add_memory("первая запись")
        memory_manager.add_memory("вторая запись")
        processor = CommandProcessor(sample_profile(), memory_manager=memory_manager)

        result = processor.process("покажи последние записи памяти")

        assert result["intent"] == "memory.recent"
        assert result["should_exit"] is False
        assert "1. вторая запись" in result["response"]
        assert "2. первая запись" in result["response"]


def test_about_user_memory_command():
    with TemporaryDirectory() as tmp_dir:
        memory_manager = LocalMemoryManager(Path(tmp_dir) / "memory.json")
        memory_manager.add_memory("вы работаете с муниципальными письмами")
        processor = CommandProcessor(sample_profile(), memory_manager=memory_manager)

        result = processor.process("что ты знаешь обо мне")

        assert result["intent"] == "memory.about_user"
        assert result["should_exit"] is False
        assert "вот что я знаю из локальной памяти" in result["response"]
        assert "1. вы работаете с муниципальными письмами" in result["response"]


def test_recall_memory_command_remember_about():
    with TemporaryDirectory() as tmp_dir:
        memory_manager = LocalMemoryManager(Path(tmp_dir) / "memory.json")
        memory_manager.add_memory("JARVIS должен быть расширяемым")
        processor = CommandProcessor(sample_profile(), memory_manager=memory_manager)

        result = processor.process("что ты помнишь про JARVIS")

        assert result["intent"] == "memory.search"
        assert result["should_exit"] is False
        assert "1. JARVIS должен быть расширяемым" in result["response"]


def test_recall_memory_command_not_found():
    with TemporaryDirectory() as tmp_dir:
        memory_manager = LocalMemoryManager(Path(tmp_dir) / "memory.json")
        memory_manager.add_memory("локальный факт")
        processor = CommandProcessor(sample_profile(), memory_manager=memory_manager)

        result = processor.process("вспомни про документы")

        assert result["intent"] == "memory.search"
        assert result["should_exit"] is False
        assert "записей по запросу: документы" in result["response"]


def test_memory_delete_command_does_not_delete():
    with TemporaryDirectory() as tmp_dir:
        memory_manager = LocalMemoryManager(Path(tmp_dir) / "memory.json")
        memory_manager.add_memory("локальный факт")
        processor = CommandProcessor(sample_profile(), memory_manager=memory_manager)

        result = processor.process("очисти память")

        assert result["intent"] == "memory.delete.requested"
        assert result["should_exit"] is False
        assert memory_manager.count_memories() == 1


def test_memory_delete_command_delete_memory_does_not_delete():
    with TemporaryDirectory() as tmp_dir:
        memory_manager = LocalMemoryManager(Path(tmp_dir) / "memory.json")
        memory_manager.add_memory("локальный факт")
        processor = CommandProcessor(sample_profile(), memory_manager=memory_manager)

        result = processor.process("удали память")

        assert result["intent"] == "memory.delete.requested"
        assert result["should_exit"] is False
        assert memory_manager.count_memories() == 1


def test_memory_delete_command_forget_all_does_not_delete():
    with TemporaryDirectory() as tmp_dir:
        memory_manager = LocalMemoryManager(Path(tmp_dir) / "memory.json")
        memory_manager.add_memory("локальный факт")
        processor = CommandProcessor(sample_profile(), memory_manager=memory_manager)

        result = processor.process("забудь всё")

        assert result["intent"] == "memory.delete.requested"
        assert result["should_exit"] is False
        assert memory_manager.count_memories() == 1


def create_voice_enabled_processor(tmp_path=None):
    processor = CommandProcessor(sample_profile())
    if tmp_path is not None:
        settings_manager = VoskSettingsManager(tmp_path / "vosk_settings.json")
    else:
        settings_manager = InMemoryVoskSettingsManager()
    manager = VoiceInputManager(
        command_processor=processor,
        dialogue_manager=processor.dialogue_manager,
        user_profile=sample_profile(),
        vosk_settings_manager=settings_manager,
    )
    processor.set_voice_input_manager(manager)
    return processor, manager


def test_microphone_mode_status_is_off_by_default():
    processor = CommandProcessor(sample_profile())

    result = processor.process("статус микрофона")

    assert result["intent"] == "microphone.mode.status"
    assert result["should_exit"] is False
    assert result["response"] == "Микрофон выключен."
    assert processor.microphone_listening_mode_manager.get_mode() == "off"


def test_microphone_mode_status_commands():
    for command in (
        "статус микрофона",
        "режим микрофона",
        "какой режим микрофона",
        "микрофон статус",
    ):
        processor = CommandProcessor(sample_profile())

        result = processor.process(command)

        assert result["intent"] == "microphone.mode.status"
        assert result["should_exit"] is False
        assert result["response"] == "Микрофон выключен."


def test_microphone_legacy_status_command_still_reports_adapter_status():
    processor, _manager = create_voice_enabled_processor()

    result = processor.process("микрофон")

    assert result["intent"] == "microphone.status"
    assert result["should_exit"] is False
    assert "статус микрофона" in result["response"]


def test_microphone_mode_off_commands_switch_to_off():
    for command in (
        "выключи микрофон",
        "отключи микрофон",
        "отключи прослушивание",
        "выключи прослушивание",
        "стоп микрофон",
        "отключи постоянное прослушивание",
        "выключи постоянное прослушивание",
        "перестань слушать постоянно",
    ):
        mode_manager = MicrophoneListeningModeManager("continuous")
        processor = CommandProcessor(
            sample_profile(),
            microphone_listening_mode_manager=mode_manager,
        )

        result = processor.process(command)

        assert result["intent"] == "microphone.mode.off"
        assert result["response"] == "Микрофон выключен."
        assert mode_manager.get_mode() == "off"


def test_microphone_mode_partial_commands_switch_to_partial():
    for command in (
        "слушай одну команду",
        "прими голосовую команду",
        "включи частичное прослушивание",
        "режим одной команды",
        "частичное прослушивание",
    ):
        processor = CommandProcessor(sample_profile())

        result = processor.process(command)

        assert result["intent"] == "microphone.mode.partial"
        assert result["response"] == (
            "Включено частичное прослушивание. "
            "Реальный захват микрофона пока не запускается автоматически."
        )
        assert processor.microphone_listening_mode_manager.get_mode() == "partial"

        status = processor.process("режим микрофона")
        assert status["response"] == (
            "Включено частичное прослушивание. JARVIS готов принять одну "
            "голосовую команду после явного запуска."
        )


def test_microphone_mode_continuous_commands_switch_to_continuous():
    for command in (
        "включи постоянное прослушивание",
        "слушай постоянно",
        "режим постоянного прослушивания",
        "включи постоянный микрофон",
    ):
        processor = CommandProcessor(sample_profile())

        result = processor.process(command)

        assert result["intent"] == "microphone.mode.continuous"
        assert result["response"] == (
            "Режим постоянного прослушивания включен как безопасное состояние. "
            "Реальный микрофон пока не запускается автоматически."
        )
        assert processor.microphone_listening_mode_manager.get_mode() == "continuous"

        status = processor.process("режим микрофона")
        assert status["response"] == (
            "Включен режим постоянного прослушивания. Реальный захват "
            "микрофона пока не активирован в целях безопасности."
        )


def test_microphone_mode_unknown_command_stays_safe():
    processor = CommandProcessor(sample_profile())

    result = processor.process("включи неизвестный режим микрофона")

    assert result["intent"] == "unknown"
    assert processor.microphone_listening_mode_manager.get_mode() == "off"


def test_microphone_mode_commands_do_not_touch_real_capture_or_vosk():
    processor, manager = create_voice_enabled_processor()

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("real microphone or Vosk path must not be used")

    manager.microphone_adapter.start_listening = fail_if_called
    manager.microphone_adapter.read_text = fail_if_called
    manager.use_vosk_backend = fail_if_called

    processor.process("слушай одну команду")
    processor.process("включи постоянное прослушивание")
    result = processor.process("выключи микрофон")

    assert result["intent"] == "microphone.mode.off"
    assert manager.microphone_adapter.get_state() == "disabled"
    assert manager.get_speech_backend_name() == "none"


def test_microphone_permission_request_commands():
    for command in (
        "разрешение микрофона",
        "запросить микрофон",
        "подготовить микрофон",
    ):
        processor, manager = create_voice_enabled_processor()

        result = processor.process(command)

        assert result["intent"] == "microphone.permission.requested"
        assert manager.microphone_adapter.get_state() == "permission_required"
        assert "явное разрешение" in result["response"]


def test_microphone_permission_grant_commands():
    for command in (
        "разрешаю микрофон",
        "дать доступ к микрофону",
        "включить доступ к микрофону",
    ):
        processor, manager = create_voice_enabled_processor()

        result = processor.process(command)

        assert result["intent"] == "microphone.permission.granted"
        assert manager.microphone_adapter.permission_granted is True
        assert manager.microphone_adapter.get_state() == "ready"


def test_microphone_permission_revoke_commands():
    for command in (
        "запретить микрофон",
        "отключить доступ к микрофону",
        "отозвать микрофон",
    ):
        processor, manager = create_voice_enabled_processor()
        manager.grant_microphone_permission()

        result = processor.process(command)

        assert result["intent"] == "microphone.permission.revoked"
        assert manager.microphone_adapter.permission_granted is False
        assert manager.microphone_adapter.get_state() == "disabled"


def test_microphone_listen_start_commands():
    for command in ("слушай меня", "начать слушать", "включи микрофон"):
        processor, manager = create_voice_enabled_processor()
        manager.grant_microphone_permission()

        result = processor.process(command)

        assert result["intent"] == "microphone.listen.start"
        assert manager.microphone_adapter.get_state() == "unavailable"
        assert manager.get_state() == "ready"
        assert "backend распознавания речи ещё не подключён" in result["response"]
        assert "Я не включаю микрофон" in result["response"]


def test_microphone_listen_stop_commands():
    for command in (
        "перестань слушать",
        "остановить микрофон",
    ):
        processor, manager = create_voice_enabled_processor()
        manager.grant_microphone_permission()
        manager.start_microphone_input()

        result = processor.process(command)

        assert result["intent"] == "microphone.listen.stop"
        assert manager.microphone_adapter.get_state() == "ready"
        assert "микрофон остановлен" in result["response"]


def test_microphone_listen_once_commands():
    for command in (
        "послушай один раз",
        "слушай команду",
        "принять голосовую команду",
    ):
        processor, manager = create_voice_enabled_processor()
        manager.grant_microphone_permission()

        result = processor.process(command)

        assert result["intent"] == "microphone.listen.once"
        assert manager.microphone_adapter.get_state() == "unavailable"
        assert "backend распознавания речи ещё не подключён" in result["response"]
        assert "Я не включаю микрофон" in result["response"]


def test_voice_simulation_identity_command():
    processor, manager = create_voice_enabled_processor()

    result = processor.process("РіРѕР»РѕСЃРѕРІР°СЏ РєРѕРјР°РЅРґР° РєС‚Рѕ СЏ")

    assert result["intent"] == "voice.command.simulated"
    assert result["should_exit"] is False
    assert result["channel"] == "voice"
    assert result["source"] == "recognized_text"
    assert manager.has_pending_confirmation() is False


def test_voice_simulation_profile_alias_command():
    processor, manager = create_voice_enabled_processor()

    result = processor.process("РіРѕР»РѕСЃРѕРј РїРѕРєР°Р¶Рё РїСЂРѕС„РёР»СЊ")

    assert result["intent"] == "voice.command.simulated"
    assert result["channel"] == "voice"
    assert manager.has_pending_confirmation() is False


def test_voice_simulation_system_status_alias_command():
    processor, _manager = create_voice_enabled_processor()

    result = processor.process("РєР°Рє РіРѕР»РѕСЃ СЃС‚Р°С‚СѓСЃ СЃРёСЃС‚РµРјС‹")

    assert result["intent"] == "voice.command.simulated"
    assert result["should_exit"] is False
    assert "РђРєС‚РёРІРЅС‹С… СЃРµСЂРІРёСЃРѕРІ" in result["response"]


def test_voice_simulation_recognized_text_alias_command():
    processor, _manager = create_voice_enabled_processor()

    result = processor.process(
        "СЂР°СЃРїРѕР·РЅР°РЅРЅС‹Р№ С‚РµРєСЃС‚ РІСЃРїРѕРјРЅРё РїСЂРѕ РјСѓРЅРёС†РёРїР°Р»СЊРЅС‹Рµ РїРёСЃСЊРјР°"
    )

    assert result["intent"] == "voice.command.simulated"
    assert result["channel"] == "voice"


def test_voice_simulation_empty_text():
    processor, _manager = create_voice_enabled_processor()

    result = processor.process("РіРѕР»РѕСЃРѕРІР°СЏ РєРѕРјР°РЅРґР°")

    assert result["intent"] == "voice.empty"
    assert result["should_exit"] is False


def test_voice_simulation_requires_confirmation():
    processor, manager = create_voice_enabled_processor()

    result = processor.process("РіРѕР»РѕСЃРѕРІР°СЏ РєРѕРјР°РЅРґР° РѕС‚РїСЂР°РІСЊ РїРёСЃСЊРјРѕ")

    assert result["intent"] == "voice.confirmation_required"
    assert manager.has_pending_confirmation() is True
    assert manager.get_pending_confirmation()["text"] == "РѕС‚РїСЂР°РІСЊ РїРёСЃСЊРјРѕ"


def test_voice_confirmation_command_confirms_pending_action():
    processor, manager = create_voice_enabled_processor()
    processor.process("РіРѕР»РѕСЃРѕРІР°СЏ РєРѕРјР°РЅРґР° РѕС‚РїСЂР°РІСЊ РїРёСЃСЊРјРѕ")

    result = processor.process("РїРѕРґС‚РІРµСЂРґРёС‚СЊ РіРѕР»РѕСЃРѕРІСѓСЋ РєРѕРјР°РЅРґСѓ")

    assert result["intent"] == "voice.confirmation.confirmed"
    assert manager.has_pending_confirmation() is False


def test_voice_cancellation_command_cancels_pending_action():
    processor, manager = create_voice_enabled_processor()
    processor.process("РіРѕР»РѕСЃРѕРІР°СЏ РєРѕРјР°РЅРґР° РѕС‚РїСЂР°РІСЊ РїРёСЃСЊРјРѕ")

    result = processor.process("РѕС‚РјРµРЅРёС‚СЊ РіРѕР»РѕСЃРѕРІСѓСЋ РєРѕРјР°РЅРґСѓ")

    assert result["intent"] == "voice.confirmation.cancelled"
    assert manager.has_pending_confirmation() is False


def test_voice_confirmation_command_without_pending():
    processor, _manager = create_voice_enabled_processor()

    result = processor.process("РїРѕРґС‚РІРµСЂРґРёС‚СЊ РіРѕР»РѕСЃРѕРІСѓСЋ РєРѕРјР°РЅРґСѓ")

    assert result["intent"] == "voice.confirmation.none"


def test_voice_simulation_identity_command():
    processor, manager = create_voice_enabled_processor()

    result = processor.process("голосовая команда кто я")

    assert result["intent"] == "voice.command.simulated"
    assert result["should_exit"] is False
    assert result["channel"] == "voice"
    assert result["source"] == "recognized_text"
    assert manager.has_pending_confirmation() is False


def test_voice_simulation_jarvis_identity_command():
    processor, manager = create_voice_enabled_processor()

    result = processor.process("джарвис кто я")

    assert result["intent"] == "voice.command.simulated"
    assert result["should_exit"] is False
    assert result["channel"] == "voice"
    assert manager.has_pending_confirmation() is False


def test_voice_simulation_jarvis_status_command():
    processor, _manager = create_voice_enabled_processor()

    result = processor.process("jarvis статус системы")

    assert result["intent"] == "voice.command.simulated"
    assert result["should_exit"] is False
    assert "Активных сервисов" in result["response"]


def test_voice_simulation_say_identity_command():
    processor, _manager = create_voice_enabled_processor()

    result = processor.process("скажи кто я")

    assert result["intent"] == "voice.command.simulated"
    assert result["should_exit"] is False


def test_voice_simulation_ask_status_command():
    processor, _manager = create_voice_enabled_processor()

    result = processor.process("спроси статус системы")

    assert result["intent"] == "voice.command.simulated"
    assert result["should_exit"] is False


def test_voice_simulation_voice_ask_status_command():
    processor, _manager = create_voice_enabled_processor()

    result = processor.process("голосом спроси статус системы")

    assert result["intent"] == "voice.command.simulated"
    assert result["should_exit"] is False


def test_voice_simulation_nested_jarvis_say_memory_command():
    processor, _manager = create_voice_enabled_processor()

    result = processor.process("джарвис скажи покажи память")

    assert result["intent"] == "voice.command.simulated"
    assert result["should_exit"] is False
    assert "принял голосовую команду: покажи память" in result["response"]


def test_voice_simulation_profile_alias_command():
    processor, manager = create_voice_enabled_processor()

    result = processor.process("голосом покажи профиль")

    assert result["intent"] == "voice.command.simulated"
    assert result["channel"] == "voice"
    assert manager.has_pending_confirmation() is False


def test_voice_simulation_system_status_alias_command():
    processor, _manager = create_voice_enabled_processor()

    result = processor.process("как голос статус системы")

    assert result["intent"] == "voice.command.simulated"
    assert result["should_exit"] is False
    assert "Активных сервисов" in result["response"]


def test_voice_simulation_recognized_text_alias_command():
    processor, _manager = create_voice_enabled_processor()

    result = processor.process(
        "распознанный текст вспомни про муниципальные письма"
    )

    assert result["intent"] == "voice.command.simulated"
    assert result["channel"] == "voice"


def test_voice_simulation_empty_text():
    processor, _manager = create_voice_enabled_processor()

    result = processor.process("голосовая команда")

    assert result["intent"] == "voice.empty"
    assert result["should_exit"] is False


def test_voice_simulation_requires_confirmation():
    processor, manager = create_voice_enabled_processor()

    result = processor.process("голосовая команда отправь письмо")

    assert result["intent"] == "voice.confirmation_required"
    assert manager.has_pending_confirmation() is True
    assert manager.get_pending_confirmation()["text"] == "отправь письмо"


def test_typed_recognition_simulation_command_parsing_safe_status():
    processor = CommandProcessor()

    result = processor.process("симулируй распознавание: статус системы")

    assert result["intent"] == "system.status"
    assert result["recognized_voice_command"] == "статус системы"
    assert result["voice_recognition_source"] == "typed_simulation"


def test_typed_recognition_simulation_test_alias_parsing():
    processor = CommandProcessor()

    result = processor.process("тестовое распознавание: статус системы")

    assert result["intent"] == "system.status"
    assert result["recognized_voice_command"] == "статус системы"
    assert result["voice_recognition_source"] == "typed_simulation"


def test_typed_recognition_simulation_check_voice_command_alias_parsing():
    processor = CommandProcessor()

    result = processor.process("проверить голосовую команду: статус системы")

    assert result["intent"] == "system.status"
    assert result["recognized_voice_command"] == "статус системы"
    assert result["voice_recognition_source"] == "typed_simulation"


def test_typed_recognition_simulation_empty_command_parsing():
    processor = CommandProcessor()

    result = processor.process("проверить голосовую команду:")

    assert result["intent"] == "voice.recognition.typed_simulation.empty"
    assert result["response"] == "Укажите текст для симуляции распознавания."


def test_voice_alias_requires_confirmation():
    processor, manager = create_voice_enabled_processor()

    result = processor.process("джарвис отправь письмо")

    assert result["intent"] == "voice.confirmation_required"
    assert manager.has_pending_confirmation() is True
    assert manager.get_pending_confirmation()["text"] == "отправь письмо"


def test_voice_confirmation_command_confirms_pending_action():
    processor, manager = create_voice_enabled_processor()
    processor.process("голосовая команда отправь письмо")

    result = processor.process("подтвердить голосовую команду")

    assert result["intent"] == "voice.confirmation.confirmed"
    assert manager.has_pending_confirmation() is False


def test_short_voice_confirmation_command_confirms_pending_action():
    processor, manager = create_voice_enabled_processor()
    processor.process("джарвис отправь письмо")

    result = processor.process("подтверждаю")

    assert result["intent"] == "voice.confirmation.confirmed"
    assert manager.has_pending_confirmation() is False


def test_short_voice_confirmation_command_without_pending():
    processor, _manager = create_voice_enabled_processor()

    result = processor.process("можно")

    assert result["intent"] == "voice.confirmation.none"
    assert result["should_exit"] is False


def test_voice_cancellation_command_cancels_pending_action():
    processor, manager = create_voice_enabled_processor()
    processor.process("голосовая команда отправь письмо")

    result = processor.process("отменить голосовую команду")

    assert result["intent"] == "voice.confirmation.cancelled"
    assert manager.has_pending_confirmation() is False


def test_short_voice_cancellation_command_cancels_pending_action():
    processor, manager = create_voice_enabled_processor()
    processor.process("джарвис отправь письмо")

    result = processor.process("отмена")

    assert result["intent"] == "voice.confirmation.cancelled"
    assert manager.has_pending_confirmation() is False


def test_short_voice_cancellation_command_without_pending():
    processor, _manager = create_voice_enabled_processor()

    result = processor.process("отбой")

    assert result["intent"] == "voice.confirmation.none"
    assert result["should_exit"] is False


def test_voice_confirmation_command_without_pending():
    processor, _manager = create_voice_enabled_processor()

    result = processor.process("подтвердить голосовую команду")

    assert result["intent"] == "voice.confirmation.none"


def run_tests():
    test_speech_backend_commands()
    test_vosk_real_commands_and_selection_flow()
    test_creation_without_profile()
    test_creation_with_profile()
    test_user_identity_command()
    test_assistant_identity_command()
    test_assistant_name_view_aliases_return_current_name()
    test_profile_command()
    test_help_command()
    test_help_alias_command()
    test_greeting_command()
    test_greeting_salam_command()
    test_change_assistant_name_to_jarvis_persists_in_profile()
    test_change_assistant_name_aliases_update_greeting()
    test_now_your_name_is_alias_changes_assistant_name()
    test_reset_assistant_name_command_returns_default()
    test_invalid_assistant_name_does_not_change_name()
    test_version_command()
    test_show_version_command()
    test_system_status_command()
    test_services_command()
    test_voice_status_command()
    test_voice_status_alias_command()
    test_voice_enable_command()
    test_voice_disable_command()
    test_show_commands_command()
    test_commands_list_command()
    test_exit_command()
    test_unknown_command()
    test_empty_command()
    test_stop_command_is_voice_cancel_without_exit()
    test_normalizes_command()
    test_send_email_requires_confirmation()
    test_delete_file_requires_confirmation()
    test_delete_system32_is_forbidden()
    test_unknown_action_is_future_idea_without_execution()
    test_add_idea_command()
    test_remember_idea_command()
    test_list_ideas_command()
    test_add_memory_command_remember_that()
    test_add_memory_command_save_to_memory()
    test_list_memory_command_show_memory()
    test_list_memory_command_what_do_you_remember()
    test_search_memory_command()
    test_memory_count_command()
    test_recent_memory_command()
    test_about_user_memory_command()
    test_recall_memory_command_remember_about()
    test_recall_memory_command_not_found()
    test_memory_delete_command_does_not_delete()
    test_memory_delete_command_delete_memory_does_not_delete()
    test_memory_delete_command_forget_all_does_not_delete()
    test_microphone_mode_status_is_off_by_default()
    test_microphone_mode_status_commands()
    test_microphone_legacy_status_command_still_reports_adapter_status()
    test_microphone_mode_off_commands_switch_to_off()
    test_microphone_mode_partial_commands_switch_to_partial()
    test_microphone_mode_continuous_commands_switch_to_continuous()
    test_microphone_mode_unknown_command_stays_safe()
    test_microphone_mode_commands_do_not_touch_real_capture_or_vosk()
    test_microphone_permission_request_commands()
    test_microphone_permission_grant_commands()
    test_microphone_permission_revoke_commands()
    test_microphone_listen_start_commands()
    test_microphone_listen_stop_commands()
    test_microphone_listen_once_commands()
    test_voice_simulation_identity_command()
    test_voice_simulation_jarvis_identity_command()
    test_voice_simulation_jarvis_status_command()
    test_voice_simulation_say_identity_command()
    test_voice_simulation_ask_status_command()
    test_voice_simulation_voice_ask_status_command()
    test_voice_simulation_nested_jarvis_say_memory_command()
    test_voice_simulation_profile_alias_command()
    test_voice_simulation_system_status_alias_command()
    test_voice_simulation_recognized_text_alias_command()
    test_voice_simulation_empty_text()
    test_voice_simulation_requires_confirmation()
    test_voice_alias_requires_confirmation()
    test_voice_confirmation_command_confirms_pending_action()
    test_short_voice_confirmation_command_confirms_pending_action()
    test_short_voice_confirmation_command_without_pending()
    test_voice_cancellation_command_cancels_pending_action()
    test_short_voice_cancellation_command_cancels_pending_action()
    test_short_voice_cancellation_command_without_pending()
    test_voice_confirmation_command_without_pending()


if __name__ == "__main__":
    run_tests()
def test_vosk_installation_information_commands():
    processor = CommandProcessor()

    install = processor.process("как установить vosk")
    assert install["intent"] == "speech.backend.vosk.installation.guide"
    assert "python -m pip install vosk" in install["response"]
    assert "автоматически не устанавливается" in install["response"]

    compatibility = processor.process("python для vosk")
    assert compatibility["intent"] == "speech.backend.vosk.compatibility"
    assert "3.5-3.9" in compatibility["response"]

    model = processor.process("русская модель vosk")
    assert model["intent"] == "speech.backend.vosk.model.guide"
    assert "vosk-model-small-ru-0.22" in model["response"]

    plan = processor.process("безопасно подключить vosk")
    assert plan["intent"] == "speech.backend.vosk.enablement.plan"
    assert "только план" in plan["response"]


def test_vosk_model_readiness_commands_return_safe_diagnostics():
    processor, _manager = create_voice_enabled_processor()

    for command in (
        "проверить модель vosk",
        "готовность модели vosk",
        "диагностика модели vosk",
        "модель vosk статус",
        "проверка модели vosk",
        "проверить установленную модель vosk",
    ):
        result = processor.process(command)

        assert result["intent"] == "speech.backend.vosk.model.status"
        assert "Путь к модели Vosk пока не указан." in result["response"]
        assert "модель не загружалась" in result["response"]
        assert "микрофон не запускался" in result["response"]
        assert "распознавание не выполнялось" in result["response"]


def test_vosk_model_installation_guidance_commands_are_manual_only():
    processor = CommandProcessor()

    for command in (
        "как установить модель vosk",
        "инструкция установки модели vosk",
        "куда положить модель vosk",
    ):
        result = processor.process(command)

        assert result["intent"] == "speech.backend.vosk.model.installation.guide"
        assert "Модель Vosk нужно скачать и распаковать вручную." in result["response"]
        assert r"C:\JARVIS-OS\models\<model-folder>" in result["response"]
        assert "установи путь модели vosk" in result["response"]
        assert "проверить модель vosk" in result["response"]
        assert "ничего не скачивает автоматически" in result["response"]
        assert "ничего не устанавливает автоматически" in result["response"]
        assert "модель не загружает" in result["response"]
        assert "микрофон не запускает" in result["response"]
