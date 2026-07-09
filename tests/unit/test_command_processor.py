from core.command_processor import CommandProcessor
from ideas import IdeaManager
from memory import LocalMemoryManager
from pathlib import Path
from tempfile import TemporaryDirectory
from voice import VoiceInputManager, VoskSettingsManager


def test_speech_backend_commands():
    processor = CommandProcessor()

    assert processor.process("speech backend")["intent"] == "speech.backend.status"
    assert (
        processor.process("почему нет распознавания")["intent"]
        == "speech.backend.explain"
    )


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


def test_vosk_preflight_and_in_memory_model_path_commands(tmp_path):
    processor, manager = create_voice_enabled_processor(tmp_path)

    for command in (
        "проверить vosk",
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
    assert "локальный путь к модели сохранён" in configured["response"]

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
    assert "JARVIS" in result["response"]


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
    assert "Голос, зрение экрана и автоматизация" in result["response"]


def test_help_alias_command():
    result = CommandProcessor(sample_profile()).process("помощь")

    assert result["intent"] == "assistant.help"
    assert result["should_exit"] is False
    assert "Для выхода напишите: выход" in result["response"]


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


def test_list_memory_command_what_do_you_remember():
    with TemporaryDirectory() as tmp_dir:
        memory_manager = LocalMemoryManager(Path(tmp_dir) / "memory.json")
        processor = CommandProcessor(sample_profile(), memory_manager=memory_manager)

        result = processor.process("что ты помнишь")

        assert result["intent"] == "memory.list"
        assert result["should_exit"] is False


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
    settings_manager = None
    if tmp_path is not None:
        settings_manager = VoskSettingsManager(tmp_path / "vosk_settings.json")
    manager = VoiceInputManager(
        command_processor=processor,
        dialogue_manager=processor.dialogue_manager,
        user_profile=sample_profile(),
        vosk_settings_manager=settings_manager,
    )
    processor.set_voice_input_manager(manager)
    return processor, manager


def test_microphone_status_commands():
    for command in ("микрофон", "статус микрофона"):
        processor, _manager = create_voice_enabled_processor()

        result = processor.process(command)

        assert result["intent"] == "microphone.status"
        assert result["should_exit"] is False
        assert "статус микрофона" in result["response"]


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
        "выключи микрофон",
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
    test_profile_command()
    test_help_command()
    test_help_alias_command()
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
    test_microphone_status_commands()
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
