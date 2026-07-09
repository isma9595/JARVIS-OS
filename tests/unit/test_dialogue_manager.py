from dialogue import DialogueManager


def test_speech_backend_responses():
    dialogue = DialogueManager()
    status_response = dialogue.speech_backend_status_response(
        {"name": "none", "available": False, "supports_offline": False}
    )

    assert "none" in status_response
    assert "не включает микрофон" in status_response
    assert "звук не записывается" in dialogue.speech_backend_explain_response()
    assert "Vosk" in dialogue.speech_backend_options_response()


def test_vosk_backend_selected_response_is_explicitly_safe():
    response = DialogueManager().speech_backend_selected_response(
        {"name": "vosk_local", "available": False}
    )

    assert "vosk_local" in response
    assert "skeleton" in response
    assert "звук не записывается" in response


def sample_profile():
    return {
        "user_name": "Исмаил",
        "preferred_name": "Исмаил",
        "assistant_name": "JARVIS",
        "language": "ru",
        "communication_style": "естественный, понятный, не робот",
    }


def test_creation_without_profile():
    dialogue = DialogueManager()

    assert dialogue.get_user_name() == "Пользователь"
    assert dialogue.get_preferred_name() == "Пользователь"


def test_creation_with_profile():
    dialogue = DialogueManager(sample_profile())

    assert dialogue.get_preferred_name() == "Исмаил"


def test_get_user_name():
    dialogue = DialogueManager(sample_profile())

    assert dialogue.get_user_name() == "Исмаил"


def test_get_assistant_name():
    dialogue = DialogueManager(sample_profile())

    assert dialogue.get_assistant_name() == "JARVIS"


def test_get_language():
    dialogue = DialogueManager(sample_profile())

    assert dialogue.get_language() == "ru"


def test_get_communication_style():
    dialogue = DialogueManager(sample_profile())

    assert dialogue.get_communication_style() == "естественный, понятный, не робот"


def test_greeting():
    dialogue = DialogueManager(sample_profile())

    assert dialogue.greeting() == "Добро пожаловать, Исмаил."


def test_startup_complete():
    dialogue = DialogueManager()

    assert dialogue.startup_complete() == "Система успешно запущена."


def test_shutdown_message():
    dialogue = DialogueManager()

    assert dialogue.shutdown_message() == "Система остановлена."


def test_already_stopped_message():
    dialogue = DialogueManager()

    assert dialogue.already_stopped_message() == "Ядро уже остановлено."


def test_confirmation_request():
    dialogue = DialogueManager(sample_profile())

    assert dialogue.confirmation_request("отправить письмо") == (
        "Исмаил, я могу выполнить действие: отправить письмо. Подтвердить?"
    )


def test_action_requires_confirmation_response():
    dialogue = DialogueManager(sample_profile())

    assert dialogue.action_requires_confirmation_response("отправить письмо") == (
        "Исмаил, это действие требует подтверждения: отправить письмо. "
        "Я не буду выполнять его без вашего разрешения."
    )


def test_forbidden_action_response():
    dialogue = DialogueManager(sample_profile())

    assert dialogue.forbidden_action_response("удали system32") == (
        "Исмаил, я не могу выполнить это действие, потому что оно может быть опасным."
    )


def test_future_idea_response():
    dialogue = DialogueManager(sample_profile())

    assert dialogue.future_idea_response("новая команда") == (
        "Исмаил, я пока не умею выполнять эту команду, "
        "но могу сохранить её как идею для будущего."
    )


def test_safe_action_response():
    dialogue = DialogueManager(sample_profile())

    assert dialogue.safe_action_response("подготовь черновик") == (
        "Исмаил, это безопасная команда: подготовь черновик. "
        "На этом этапе я только определяю действие и не выполняю его."
    )


def test_acknowledgement():
    dialogue = DialogueManager(sample_profile())

    assert dialogue.acknowledgement("подготовить письмо") == (
        "Понял, Исмаил. Подготовлю: подготовить письмо."
    )


def test_error_message():
    dialogue = DialogueManager(sample_profile())

    assert dialogue.error_message("файл не найден") == (
        "Исмаил, возникла ошибка: файл не найден."
    )


def test_memory_saved_response():
    dialogue = DialogueManager(sample_profile())

    assert dialogue.memory_saved_response("любишь зелёный цвет") == (
        "Исмаил, я запомнил: любишь зелёный цвет."
    )


def test_no_memory_response():
    dialogue = DialogueManager(sample_profile())

    assert dialogue.no_memory_response() == "Исмаил, пока в локальной памяти ничего нет."


def test_memory_list_response():
    dialogue = DialogueManager(sample_profile())

    response = dialogue.memory_list_response(
        [{"content": "любишь зелёный цвет"}, {"content": "работаешь с документами"}]
    )

    assert "Исмаил, вот что я помню:" in response
    assert "1. любишь зелёный цвет" in response
    assert "2. работаешь с документами" in response


def test_memory_search_response():
    dialogue = DialogueManager(sample_profile())

    response = dialogue.memory_search_response(
        [{"content": "работаешь с документами"}], "документы"
    )

    assert "Исмаил, я нашёл в памяти:" in response
    assert "1. работаешь с документами" in response


def test_memory_count_response():
    dialogue = DialogueManager(sample_profile())

    assert dialogue.memory_count_response(3) == (
        "Исмаил, в локальной памяти сохранено записей: 3."
    )


def test_recent_memory_response():
    dialogue = DialogueManager(sample_profile())

    response = dialogue.recent_memory_response(
        [{"content": "вторая запись"}, {"content": "первая запись"}]
    )

    assert "Исмаил, вот последние записи памяти:" in response
    assert "1. вторая запись" in response
    assert "2. первая запись" in response


def test_about_user_response():
    dialogue = DialogueManager(sample_profile())

    response = dialogue.about_user_response(
        [{"content": "вы работаете с муниципальными письмами"}]
    )

    assert "Исмаил, вот что я знаю из локальной памяти:" in response
    assert "1. вы работаете с муниципальными письмами" in response


def test_memory_recall_response():
    dialogue = DialogueManager(sample_profile())

    response = dialogue.memory_recall_response(
        [{"content": "JARVIS должен быть расширяемым"}], "JARVIS"
    )

    assert "Исмаил, я нашёл в памяти:" in response
    assert "1. JARVIS должен быть расширяемым" in response


def test_memory_not_found_response():
    dialogue = DialogueManager(sample_profile())

    assert dialogue.memory_not_found_response("проект") == (
        "Исмаил, я не нашёл в памяти записей по запросу: проект."
    )


def test_version_response():
    dialogue = DialogueManager(sample_profile())

    assert dialogue.version_response("0.2") == (
        "Исмаил, текущая версия JARVIS OS: v0.2."
    )


def test_system_status_response():
    dialogue = DialogueManager(sample_profile())

    response = dialogue.system_status_response(
        {
            "version": "0.2",
            "state": "running",
            "services": ["logger", "event_bus"],
        }
    )

    assert response == (
        "Исмаил, система работает. Версия: v0.2. Активных сервисов: 2."
    )


def test_services_response():
    dialogue = DialogueManager(sample_profile())

    response = dialogue.services_response(["logger", "event_bus"])

    assert "Исмаил, активные системные сервисы:" in response
    assert "1. logger" in response
    assert "2. event_bus" in response


def test_commands_response():
    dialogue = DialogueManager(sample_profile())

    response = dialogue.commands_response()

    assert "Исмаил, сейчас доступны такие команды:" in response
    assert "Профиль:" in response
    assert "Память:" in response
    assert "Идеи:" in response
    assert "Система:" in response
    assert "Выход:" in response


def test_help_response():
    dialogue = DialogueManager(sample_profile())

    response = dialogue.help_response()

    assert "работать с профилем" in response
    assert "Голос, зрение экрана и автоматизация" in response
    assert "Для выхода напишите: выход" in response


def test_voice_disabled_response():
    dialogue = DialogueManager(sample_profile())

    response = dialogue.voice_disabled_response()

    assert "голосовой ввод отключён" in response
    assert "не слушаю микрофон" in response


def test_voice_enabled_response():
    dialogue = DialogueManager(sample_profile())

    response = dialogue.voice_enabled_response()

    assert "голосовой ввод подготовлен" in response
    assert "реальный микрофон пока не включается" in response


def test_voice_listening_started_response():
    dialogue = DialogueManager(sample_profile())

    response = dialogue.voice_listening_started_response()

    assert "режим ожидания" in response
    assert "Микрофон в этой версии не включается" in response


def test_voice_listening_stopped_response():
    dialogue = DialogueManager(sample_profile())

    response = dialogue.voice_listening_stopped_response()

    assert "остановлен" in response
    assert "Микрофон не использовался" in response


def test_voice_empty_input_response():
    dialogue = DialogueManager(sample_profile())

    response = dialogue.voice_empty_input_response()

    assert "не получил распознанный текст" in response


def test_voice_not_real_microphone_response():
    dialogue = DialogueManager(sample_profile())

    response = dialogue.voice_not_real_microphone_response()

    assert "голосовой фундамент есть" in response
    assert "микрофон пока не включается" in response


def test_voice_command_received_response():
    dialogue = DialogueManager(sample_profile())

    response = dialogue.voice_command_received_response("РєС‚Рѕ СЏ")

    assert "РїСЂРёРЅСЏР» РіРѕР»РѕСЃРѕРІСѓСЋ РєРѕРјР°РЅРґСѓ" in response
    assert "РєС‚Рѕ СЏ" in response


def test_voice_confirmation_required_response():
    dialogue = DialogueManager(sample_profile())

    response = dialogue.voice_confirmation_required_response("РѕС‚РїСЂР°РІСЊ РїРёСЃСЊРјРѕ")

    assert "С‚СЂРµР±СѓРµС‚ РїРѕРґС‚РІРµСЂР¶РґРµРЅРёСЏ" in response
    assert "РѕС‚РїСЂР°РІСЊ РїРёСЃСЊРјРѕ" in response


def test_voice_confirmation_confirmed_response():
    dialogue = DialogueManager(sample_profile())

    response = dialogue.voice_confirmation_confirmed_response("РѕС‚РїСЂР°РІСЊ РїРёСЃСЊРјРѕ")

    assert "РїРѕРґС‚РІРµСЂР¶РґРµРЅРёРµ РїСЂРёРЅСЏС‚Рѕ" in response
    assert "Р РµР°Р»СЊРЅРѕРµ РІС‹РїРѕР»РЅРµРЅРёРµ РґРµР№СЃС‚РІРёР№" in response


def test_voice_confirmation_cancelled_response():
    dialogue = DialogueManager(sample_profile())

    response = dialogue.voice_confirmation_cancelled_response("РѕС‚РїСЂР°РІСЊ РїРёСЃСЊРјРѕ")

    assert "РіРѕР»РѕСЃРѕРІРѕРµ РґРµР№СЃС‚РІРёРµ РѕС‚РјРµРЅРµРЅРѕ" in response


def test_voice_confirmation_none_response():
    dialogue = DialogueManager(sample_profile())

    response = dialogue.voice_confirmation_none_response()

    assert "РЅРµС‚ РіРѕР»РѕСЃРѕРІРѕРіРѕ РґРµР№СЃС‚РІРёСЏ" in response
    assert "РґР»СЏ РїРѕРґС‚РІРµСЂР¶РґРµРЅРёСЏ" in response


def test_voice_cancellation_none_response():
    dialogue = DialogueManager(sample_profile())

    response = dialogue.voice_cancellation_none_response()

    assert "РЅРµС‚ РіРѕР»РѕСЃРѕРІРѕРіРѕ РґРµР№СЃС‚РІРёСЏ" in response
    assert "РґР»СЏ РѕС‚РјРµРЅС‹" in response


def test_voice_forbidden_response():
    dialogue = DialogueManager(sample_profile())

    response = dialogue.voice_forbidden_response("СѓРґР°Р»Рё system32")

    assert "РЅРµ РјРѕРіСѓ РІС‹РїРѕР»РЅРёС‚СЊ СЌС‚Сѓ РіРѕР»РѕСЃРѕРІСѓСЋ РєРѕРјР°РЅРґСѓ" in response
    assert "РѕРїР°СЃРЅРѕР№" in response


def test_voice_command_received_response():
    dialogue = DialogueManager(sample_profile())

    response = dialogue.voice_command_received_response("кто я")

    assert "принял голосовую команду" in response
    assert "кто я" in response


def test_voice_confirmation_required_response():
    dialogue = DialogueManager(sample_profile())

    response = dialogue.voice_confirmation_required_response("отправь письмо")

    assert "требует подтверждения" in response
    assert "отправь письмо" in response


def test_voice_confirmation_confirmed_response():
    dialogue = DialogueManager(sample_profile())

    response = dialogue.voice_confirmation_confirmed_response("отправь письмо")

    assert "подтверждение принято" in response
    assert "Реальное выполнение действий" in response


def test_voice_confirmation_cancelled_response():
    dialogue = DialogueManager(sample_profile())

    response = dialogue.voice_confirmation_cancelled_response("отправь письмо")

    assert "голосовое действие отменено" in response


def test_voice_confirmation_none_response():
    dialogue = DialogueManager(sample_profile())

    response = dialogue.voice_confirmation_none_response()

    assert "нет голосового действия" in response
    assert "для подтверждения" in response


def test_voice_cancellation_none_response():
    dialogue = DialogueManager(sample_profile())

    response = dialogue.voice_cancellation_none_response()

    assert "нет голосового действия" in response
    assert "для отмены" in response


def test_voice_forbidden_response():
    dialogue = DialogueManager(sample_profile())

    response = dialogue.voice_forbidden_response("удали system32")

    assert "не могу выполнить эту голосовую команду" in response
    assert "опасной" in response


def test_microphone_responses():
    dialogue = DialogueManager(sample_profile())

    assert "статус микрофона" in dialogue.microphone_status_response(
        {
            "state": "disabled",
            "permission_granted": False,
            "backend_name": "none",
        }
    )
    assert "явное разрешение" in dialogue.microphone_permission_required_response()
    assert "доступ к микрофону разрешён" in dialogue.microphone_permission_granted_response()
    assert "доступ к микрофону отозван" in dialogue.microphone_permission_revoked_response()
    assert "backend распознавания речи ещё не подключён" in dialogue.microphone_unavailable_response()
    assert "Я не включаю микрофон" in dialogue.microphone_unavailable_response()
    assert "Реальное прослушивание не запускается" in dialogue.microphone_listening_started_response()
    assert "микрофон остановлен" in dialogue.microphone_listening_stopped_response()
    assert "микрофон сейчас не слушает" in dialogue.microphone_not_listening_response()


def run_tests():
    test_creation_without_profile()
    test_creation_with_profile()
    test_get_user_name()
    test_get_assistant_name()
    test_get_language()
    test_get_communication_style()
    test_greeting()
    test_startup_complete()
    test_shutdown_message()
    test_already_stopped_message()
    test_confirmation_request()
    test_action_requires_confirmation_response()
    test_forbidden_action_response()
    test_future_idea_response()
    test_safe_action_response()
    test_acknowledgement()
    test_error_message()
    test_memory_saved_response()
    test_no_memory_response()
    test_memory_list_response()
    test_memory_search_response()
    test_memory_count_response()
    test_recent_memory_response()
    test_about_user_response()
    test_memory_recall_response()
    test_memory_not_found_response()
    test_version_response()
    test_system_status_response()
    test_services_response()
    test_commands_response()
    test_help_response()
    test_voice_disabled_response()
    test_voice_enabled_response()
    test_voice_listening_started_response()
    test_voice_listening_stopped_response()
    test_voice_empty_input_response()
    test_voice_not_real_microphone_response()
    test_voice_command_received_response()
    test_voice_confirmation_required_response()
    test_voice_confirmation_confirmed_response()
    test_voice_confirmation_cancelled_response()
    test_voice_confirmation_none_response()
    test_voice_cancellation_none_response()
    test_voice_forbidden_response()
    test_microphone_responses()


if __name__ == "__main__":
    run_tests()
