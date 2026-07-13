from pathlib import Path

from core.action_router import SafeActionRouter
from dialogue import (
    AssistantResponseHistory,
    DialogueManager,
    VoiceDialogueModeManager,
    VoiceInteractionControls,
)
from ideas import IdeaManager
from memory import LocalMemoryManager
from users.user_profile import UserProfileManager


class CommandProcessor:
    GREETING_COMMANDS = {
        "привет",
        "здравствуй",
        "здравствуйте",
        "салам",
        "ассаламу алейкум",
    }
    USER_IDENTITY_COMMANDS = {
        "кто я",
        "как меня зовут",
        "мое имя",
        "моё имя",
    }
    ASSISTANT_IDENTITY_COMMANDS = {
        "как тебя зовут",
        "как зовут ассистента",
        "имя ассистента",
        "покажи имя ассистента",
        "кто ты",
        "твое имя",
        "твоё имя",
    }
    ASSISTANT_NAME_CHANGE_PREFIXES = (
        "измени имя ассистента на",
        "поменяй имя ассистента на",
        "назови себя",
        "теперь тебя зовут",
        "зови себя",
    )
    ASSISTANT_NAME_RESET_COMMANDS = {
        "сбрось имя ассистента",
        "верни имя ассистента по умолчанию",
        "сбросить имя ассистента",
        "удали имя ассистента",
    }
    PROFILE_COMMANDS = {
        "покажи профиль",
        "мой профиль",
        "профиль",
    }
    CAPABILITIES_COMMANDS = {
        "что ты умеешь",
        "помощь",
        "команды",
        "help",
        "покажи возможности",
    }
    VERSION_COMMANDS = {
        "версия",
        "покажи версию",
        "какая версия",
        "версия системы",
    }
    SYSTEM_STATUS_COMMANDS = {
        "статус",
        "статус системы",
        "как система",
        "состояние системы",
    }
    SYSTEM_SERVICES_COMMANDS = {
        "покажи сервисы",
        "список сервисов",
        "какие сервисы работают",
        "системные сервисы",
    }
    VOICE_STATUS_COMMANDS = {
        "голос",
        "статус голоса",
        "голосовой ввод",
        "голосовой режим",
    }
    VOICE_ENABLE_COMMANDS = {
        "включи голос",
        "включить голосовой ввод",
        "активируй голос",
    }
    VOICE_DISABLE_COMMANDS = {
        "отключи голос",
        "отключить голосовой ввод",
    }
    VOICE_OUTPUT_STATUS_COMMANDS = {
        "статус голосового ответа",
        "статус голоса",
        "голосовой ответ статус",
    }
    VOICE_OUTPUT_DRY_RUN_ENABLE_COMMANDS = {
        "включить тестовый голос",
        "включи тестовый голос",
        "режим голоса dry run",
        "режим голоса тест",
    }
    VOICE_OUTPUT_LOCAL_STATUS_COMMANDS = {
        "диагностика локального голоса",
        "проверить локальный голос",
        "проверить голос windows",
        "статус локального голоса windows",
        "доступен ли голос windows",
    }
    VOICE_OUTPUT_LOCAL_ENABLE_COMMANDS = {
        "включить локальный голос",
        "включить голос windows",
        "включи локальный голос",
        "режим голоса windows",
        "режим голоса локальный",
    }
    VOICE_OUTPUT_DISABLE_COMMANDS = {
        "выключить голос",
        "выключи голос",
        "отключить голосовой ответ",
    }
    VOICE_OUTPUT_MUTE_COMMANDS = {
        "замолчи",
        "тихо",
        "стоп голос",
        "останови голос",
        "остановить голос",
        "перестань говорить",
        "не говори",
        "отключи речь",
        "выключи речь",
    }
    VOICE_OUTPUT_UNMUTE_COMMANDS = {
        "снова говори",
        "можешь говорить",
        "включи речь",
        "разреши голос",
        "выключи тихий режим",
        "отключи тихий режим",
        "размутить голос",
    }
    VOICE_OUTPUT_SKIP_NEXT_COMMANDS = {
        "не озвучивай следующий ответ",
        "пропусти следующую озвучку",
        "следующий ответ не озвучивай",
        "один ответ без голоса",
    }
    VOICE_OUTPUT_SAFETY_STATUS_COMMANDS = {
        "статус голосовой безопасности",
        "статус тихого режима",
        "статус mute",
        "голос заблокирован?",
        "можно ли говорить голосом",
    }
    VOICE_OUTPUT_SAY_PREFIXES = (
        "скажи:",
        "произнеси:",
        "озвучь:",
    )
    VOICE_OUTPUT_TEST_COMMANDS = {
        "тест голоса",
        "проверка голоса",
    }
    VOICE_OUTPUT_LOCAL_TEST_COMMANDS = {
        "тест локального голоса",
        "проверка локального голоса",
    }
    VOICE_OUTPUT_CAPABILITIES_COMMANDS = {
        "что ты можешь сказать голосом",
    }
    ASSISTANT_LAST_RESPONSE_COMMANDS = {
        "последний ответ",
        "покажи последний ответ",
        "что ты сказал",
        "что ты ответил",
        "что ты сказал последний раз",
        "повтори текстом",
        "повтори последний ответ текстом",
        "последний ответ jarvis",
        "последний ответ джарвис",
    }
    ASSISTANT_SPEAK_LAST_RESPONSE_COMMANDS = {
        "повтори",
        "повтори ещё раз",
        "повтори еще раз",
        "озвучь последний ответ",
        "скажи последний ответ",
        "произнеси последний ответ",
        "повтори голосом",
        "повтори последний ответ голосом",
        "скажи ещё раз",
        "скажи еще раз",
        "озвучь ещё раз",
        "озвучь еще раз",
        "скажи это голосом",
        "озвучь это",
    }
    ASSISTANT_CLARIFY_SHORT_COMMANDS = {
        "объясни короче",
        "скажи короче",
        "коротко",
        "короче",
    }
    ASSISTANT_CLARIFY_SIMPLE_COMMANDS = {
        "скажи проще",
        "объясни проще",
        "проще",
    }
    ASSISTANT_RESPONSE_HISTORY_COMMANDS = {
        "история ответов",
        "история ответов jarvis",
    }
    ASSISTANT_RESPONSE_HISTORY_COUNT_COMMANDS = {
        "сколько ответов",
    }
    ASSISTANT_RESPONSE_HISTORY_CLEAR_COMMANDS = {
        "очистить историю ответов",
        "очисти историю ответов",
    }
    VOICE_DIALOGUE_STATUS_COMMANDS = {
        "статус голосового диалога",
        "режим голосового диалога",
    }
    VOICE_DIALOGUE_ENABLE_COMMANDS = {
        "включить голосовой диалог",
        "включи голосовой диалог",
        "включить ручной голосовой диалог",
        "включи ручной голосовой диалог",
        "говори ответы голосом",
        "озвучивай ответы",
        "озвучивай текущие ответы",
    }
    VOICE_DIALOGUE_DISABLE_COMMANDS = {
        "выключить голосовой диалог",
        "выключи голосовой диалог",
        "отключить голосовой диалог",
        "не озвучивай ответы",
        "перестань озвучивать ответы",
    }
    MICROPHONE_STATUS_COMMANDS = {
        "статус микрофона",
        "режим микрофона",
        "какой режим микрофона",
        "микрофон статус",
    }
    MICROPHONE_ADAPTER_STATUS_COMMANDS = {
        "микрофон",
    }
    MICROPHONE_MODE_OFF_COMMANDS = {
        "выключи микрофон",
        "отключи микрофон",
        "отключи прослушивание",
        "выключи прослушивание",
        "стоп микрофон",
    }
    MICROPHONE_MODE_PARTIAL_COMMANDS = {
        "слушай одну команду",
        "прими голосовую команду",
        "включи частичное прослушивание",
        "режим одной команды",
        "частичное прослушивание",
    }
    MICROPHONE_MODE_CONTINUOUS_COMMANDS = {
        "включи постоянное прослушивание",
        "слушай постоянно",
        "режим постоянного прослушивания",
        "включи постоянный микрофон",
    }
    MICROPHONE_MODE_DISABLE_CONTINUOUS_COMMANDS = {
        "отключи постоянное прослушивание",
        "выключи постоянное прослушивание",
        "перестань слушать постоянно",
    }
    MICROPHONE_PERMISSION_REQUEST_COMMANDS = {
        "разрешение микрофона",
        "запросить микрофон",
        "подготовить микрофон",
    }
    MICROPHONE_PERMISSION_GRANT_COMMANDS = {
        "разрешаю микрофон",
        "дать доступ к микрофону",
        "включить доступ к микрофону",
    }
    MICROPHONE_PERMISSION_REVOKE_COMMANDS = {
        "запретить микрофон",
        "отключить доступ к микрофону",
        "отозвать микрофон",
    }
    MICROPHONE_LISTEN_START_COMMANDS = {
        "слушай меня",
        "начать слушать",
        "включи микрофон",
    }
    MICROPHONE_LISTEN_STOP_COMMANDS = {
        "перестань слушать",
        "остановить микрофон",
        "выключи микрофон",
    }
    MICROPHONE_LISTEN_ONCE_COMMANDS = {
        "послушай один раз",
        "слушай команду",
        "принять голосовую команду",
    }
    SPEECH_BACKEND_STATUS_COMMANDS = {
        "речевой backend",
        "speech backend",
        "backend речи",
        "backend распознавания",
        "статус распознавания речи",
    }
    SPEECH_BACKEND_EXPLAIN_COMMANDS = {
        "почему ты меня не слышишь",
        "почему микрофон не работает",
        "почему нет распознавания",
        "почему ты не распознаешь голос",
    }
    SPEECH_BACKEND_OPTIONS_COMMANDS = {
        "варианты распознавания речи",
        "какие есть backend голоса",
        "какой backend выбрать",
        "локальное распознавание речи",
    }
    VOSK_BACKEND_STATUS_COMMANDS = {
        "vosk",
        "vosk backend",
        "локальный vosk",
        "восок",
        "воск",
    }
    VOSK_RECOGNITION_STATUS_COMMANDS = {
        "статус vosk",
        "проверить vosk",
        "готов ли vosk",
        "готово ли распознавание",
        "статус распознавания",
        "проверка распознавания",
        "локальное распознавание",
        "готово ли локальное распознавание",
    }
    VOSK_RECOGNITION_DRY_RUN_COMMANDS = {
        "пробный запуск vosk",
        "тест vosk",
        "тест распознавания",
        "пробное распознавание",
        "проверить локальное распознавание",
        "dry run vosk",
    }
    ONE_SHOT_VOSK_BRIDGE_COMMANDS = {
        "мост vosk",
        "голосовой мост",
        "one shot vosk",
        "one-shot vosk",
        "проверка голосового моста",
        "тест голосового моста",
        "проверить мост распознавания",
        "мост распознавания",
    }
    ONE_SHOT_VOSK_REAL_RECOGNITION_COMMANDS = {
        "распознай голос один раз",
        "распознай одну голосовую команду",
        "реальное распознавание vosk",
        "запусти распознавание vosk один раз",
        "запусти голосовое распознавание один раз",
        "проверить голос через vosk",
        "тест реального vosk",
        "тест реального распознавания",
    }
    TYPED_VOICE_RECOGNITION_SIMULATION_PREFIXES = (
        "симулируй распознавание",
        "симуляция распознавания",
        "тест распознавания",
        "тестовое распознавание",
        "проверить голосовую команду",
        "проверь голосовую команду",
    )
    PENDING_VOICE_COMMAND_STATUS_COMMANDS = {
        "ожидающая голосовая команда",
        "pending voice command",
        "какая голосовая команда ожидает подтверждения",
    }
    SAFE_VOICE_COMMAND_ALLOWLIST_COMMANDS = {
        "список безопасных голосовых команд",
        "безопасные голосовые команды",
        "voice allowlist",
        "какие голосовые команды без подтверждения",
    }
    LAST_VOICE_RECOGNITION_COMMANDS = {
        "последнее распознавание",
        "последнее распознование",
        "последняя голосовая команда",
        "покажи последнюю голосовую команду",
        "что я сказал",
        "что ты услышал",
        "что ты распознал",
    }
    REPEAT_LAST_VOICE_COMMAND_COMMANDS = {
        "повтори последнюю голосовую команду",
        "повтори что я сказал голосом",
        "озвучь последнюю голосовую команду",
    }
    VOICE_COMMAND_HISTORY_COMMANDS = {
        "история голосовых команд",
        "покажи историю голоса",
        "история распознавания",
        "история распознования",
    }
    VOICE_COMMAND_HISTORY_COUNT_COMMANDS = {
        "сколько голосовых команд",
    }
    VOICE_COMMAND_HISTORY_CLEAR_COMMANDS = {
        "очистить историю голосовых команд",
        "очисти историю голоса",
        "сбросить историю распознавания",
    }
    VOICE_RECOGNITION_CORRECTION_LIST_COMMANDS = {
        "голосовые исправления",
        "список голосовых исправлений",
        "покажи исправления распознавания",
    }
    VOICE_RECOGNITION_CORRECTION_COUNT_COMMANDS = {
        "сколько голосовых исправлений",
    }
    VOICE_RECOGNITION_CORRECTION_CLEAR_COMMANDS = {
        "очистить голосовые исправления",
        "очисти исправления распознавания",
        "сбросить голосовые исправления",
    }
    VOICE_RECOGNITION_CORRECTION_PREFIXES = (
        ("я сказал не ", ", а "),
        ("я говорил не ", ", а "),
        ("исправь распознавание: ", " -> "),
        ("исправь голос: ", " -> "),
        ("это не ", ", это "),
    )
    PENDING_VOICE_COMMAND_CLEAR_COMMANDS = {
        "отменить голосовую команду",
        "сбросить голосовую команду",
    }
    PENDING_VOICE_COMMAND_POSITIVE_CONFIRMATIONS = {
        "да",
        "подтверждаю",
        "выполнить",
        "выполни",
        "ок",
        "ага",
        "yes",
    }
    PENDING_VOICE_COMMAND_NEGATIVE_CONFIRMATIONS = {
        "нет",
        "отмена",
        "отмени",
        "не надо",
        "no",
    }
    AUDIO_DEPENDENCY_READINESS_COMMANDS = {
        "проверка аудио зависимостей",
        "проверить аудио зависимости",
        "проверить зависимости микрофона",
        "диагностика микрофона",
        "почему не работает микрофон",
        "проверить numpy",
        "статус numpy",
        "проверить sounddevice",
        "статус sounddevice",
        "проверить vosk пакет",
        "статус vosk пакета",
    }
    VOSK_BACKEND_SELECT_COMMANDS = {
        "выбрать vosk",
        "использовать vosk",
        "включить vosk backend",
        "переключиться на vosk",
        "выбери vosk backend",
        "используй vosk",
        "подключи vosk",
        "use vosk backend",
    }
    VOSK_BACKEND_PLAN_COMMANDS = {
        "план vosk",
        "как подключить vosk",
        "что нужно для vosk",
        "подключение vosk",
    }
    VOSK_PREFLIGHT_COMMANDS = {
        "preflight vosk",
        "проверка vosk",
        "проверь vosk",
        "диагностика vosk",
        "проверить воск",
        "диагностика воск",
        "vosk preflight",
    }
    VOSK_MISSING_REQUIREMENTS_COMMANDS = {
        "что не хватает vosk",
        "чего не хватает vosk",
        "чего не хватает для vosk",
        "что отсутствует для vosk",
        "требования vosk",
        "требования воск",
    }
    VOSK_MODEL_STATUS_COMMANDS = {
        "модель vosk",
        "статус модели vosk",
        "проверить модель vosk",
        "готовность модели vosk",
        "диагностика модели vosk",
        "модель vosk статус",
        "проверка модели vosk",
        "проверить установленную модель vosk",
        "модель воск",
        "статус модели воск",
    }
    VOSK_MODEL_PATH_STATUS_COMMANDS = {
        "путь модели vosk",
        "где модель vosk",
        "проверить путь модели vosk",
        "какой путь модели vosk",
    }
    VOSK_MODEL_PATH_PREFIXES = (
        "сохранить путь модели vosk",
        "установить путь модели vosk",
        "установи путь модели vosk",
        "задай путь модели vosk",
        "измени путь модели vosk",
        "сохрани путь модели vosk",
        "путь модели vosk",
        "модель vosk путь",
        "путь модели воск",
        "укажи путь к модели vosk",
        "установи путь к модели vosk",
    )
    VOSK_MODEL_PATH_CLEAR_COMMANDS = {
        "очистить путь модели vosk",
        "очисти путь модели vosk",
        "сбросить путь модели vosk",
        "сбрось путь модели vosk",
        "удалить путь модели vosk",
        "удали путь модели vosk",
    }
    VOSK_LANGUAGE_PREFIXES = (
        "язык модели vosk",
        "установить язык модели vosk",
        "установить язык vosk",
    )
    VOSK_LANGUAGE_STATUS_COMMANDS = {
        "язык vosk",
    }
    VOSK_SETTINGS_COMMANDS = {
        "настройки vosk",
    }
    VOSK_INSTALLATION_GUIDE_COMMANDS = {
        "установка vosk",
        "как установить vosk",
        "настроить vosk",
        "как настроить vosk",
        "инструкция vosk",
        "инструкция по установке vosk",
        "настройка распознавания",
        "vosk installation guide",
    }
    VOSK_MODEL_INSTALLATION_GUIDE_COMMANDS = {
        "как установить модель vosk",
        "инструкция установки модели vosk",
        "куда положить модель vosk",
    }
    VOSK_PYTHON_COMPATIBILITY_COMMANDS = {
        "совместимость vosk",
        "проверить совместимость vosk",
        "python vosk",
        "версия python vosk",
        "совместимость воск",
        "совместимость python vosk",
        "python для vosk",
        "версия python для vosk",
        "проверить python для vosk",
    }
    VOSK_MODEL_GUIDE_COMMANDS = {
        "скачать модель vosk",
        "какую модель vosk скачать",
        "рекомендуемая модель vosk",
        "русская модель vosk",
    }
    VOSK_SAFE_ENABLEMENT_COMMANDS = {
        "план подключения vosk",
        "безопасный план vosk",
        "подключить vosk план",
        "план воск",
        "безопасно подключить vosk",
        "безопасное подключение vosk",
        "план включения vosk",
        "vosk safe enablement",
    }
    VOSK_RISKS_COMMANDS = {
        "риски vosk",
        "риски подключения vosk",
        "опасности vosk",
        "риски воск",
    }
    VOSK_RUNTIME_STATUS_COMMANDS = {
        "runtime vosk",
        "статус runtime vosk",
        "статус рантайм vosk",
        "runtime воск",
        "рантайм vosk",
        "рантайм воск",
        "статус загрузчика vosk",
        "vosk runtime status",
    }
    VOSK_RUNTIME_BLOCKERS_COMMANDS = {
        "блокировки vosk runtime",
        "блокировки runtime vosk",
        "блокировки рантайм vosk",
        "почему runtime vosk не готов",
        "почему рантайм vosk не готов",
        "почему vosk не запускается",
        "что мешает загрузить vosk",
        "vosk runtime blockers",
    }
    VOSK_RUNTIME_SAFETY_COMMANDS = {
        "безопасность runtime vosk",
        "безопасность загрузчика vosk",
        "vosk runtime safety",
    }
    VOSK_RUNTIME_PREPARE_COMMANDS = {
        "подготовить runtime vosk",
        "подготовить загрузчик vosk",
        "prepare vosk runtime",
    }
    VOSK_RUNTIME_RECOGNIZE_COMMANDS = {
        "распознать через vosk",
        "запустить распознавание vosk",
        "recognize with vosk",
    }
    VOICE_SIMULATION_PREFIXES = (
        "голосовая команда",
        "распознанный текст",
        "голосом спроси",
        "голосом скажи",
        "джарвис спроси",
        "джарвис скажи",
        "голосом",
        "как голос",
        "джарвис",
        "jarvis",
        "скажи",
        "спроси",
    )
    VOICE_CONFIRMATION_COMMANDS = {
        "подтвердить голосовую команду",
        "подтверждаю голосовую команду",
        "голос подтверждаю",
        "подтвердить голосом",
        "подтверждаю",
        "да подтверждаю",
        "можно",
        "давай",
        "выполняй",
    }
    VOICE_CANCELLATION_COMMANDS = {
        "отменить голосовую команду",
        "отмени голосовую команду",
        "голос отмена",
        "отменить голосом",
        "отмена",
        "отбой",
        "не надо",
        "стоп",
    }
    COMMANDS_LIST_COMMANDS = {
        "покажи команды",
        "список команд",
        "какие команды есть",
        "все команды",
    }
    EXIT_COMMANDS = {
        "выход",
        "остановись",
        "завершить",
        "закрыть",
    }
    IDEA_ADD_PREFIXES = (
        "добавь идею",
        "запомни идею",
        "сохрани идею",
        "записать идею",
    )
    IDEA_LIST_COMMANDS = {
        "покажи идеи",
        "мои идеи",
        "список идей",
        "идеи",
    }
    IDEA_COUNT_COMMANDS = {
        "сколько идей",
        "количество идей",
        "сколько сохранено идей",
    }
    MEMORY_ADD_PREFIXES = (
        "запомни что",
        "запомни",
        "сохрани в память что",
        "сохрани в память",
        "сохрани это в память что",
        "сохрани это в память",
    )
    MEMORY_LIST_COMMANDS = {
        "что ты запомнил",
        "что ты помнишь",
        "покажи память",
        "покажи что ты запомнил",
        "что в памяти",
        "локальная память",
        "моя память",
        "память",
    }
    MEMORY_COUNT_COMMANDS = {
        "сколько ты помнишь",
        "сколько записей в памяти",
        "сколько у тебя памяти",
    }
    MEMORY_RECENT_COMMANDS = {
        "покажи последние записи памяти",
        "последние записи памяти",
        "последняя память",
        "последние воспоминания",
    }
    MEMORY_ABOUT_USER_COMMANDS = {
        "что ты знаешь обо мне",
        "что ты помнишь обо мне",
        "что ты знаешь про меня",
        "что ты помнишь про меня",
    }
    MEMORY_SEARCH_PREFIXES = (
        "вспомни про",
        "что ты помнишь про",
        "найди в памяти",
        "поиск в памяти",
        "вспомни",
    )
    MEMORY_DELETE_COMMANDS = {
        "забудь всё",
        "забудь все",
        "очисти память",
        "удали память",
    }

    def __init__(
        self,
        user_profile=None,
        dialogue_manager=None,
        idea_manager=None,
        memory_manager=None,
        system_status_provider=None,
        vosk_runtime_loader=None,
        vosk_recognition_dry_run=None,
        one_shot_vosk_recognition_bridge=None,
        one_shot_vosk_real_recognition=None,
        audio_dependency_readiness_checker=None,
        microphone_listening_mode_manager=None,
        user_profile_manager=None,
        safe_voice_command_allowlist=None,
        voice_command_history=None,
        voice_recognition_correction_manager=None,
        voice_output_manager=None,
        assistant_response_history=None,
        voice_dialogue_mode_manager=None,
    ):
        self.user_profile = user_profile or {}
        self.dialogue_manager = dialogue_manager or DialogueManager(self.user_profile)
        self.user_profile_manager = user_profile_manager
        self.idea_manager = idea_manager or IdeaManager()
        self.memory_manager = memory_manager or LocalMemoryManager()
        self.system_status_provider = (
            system_status_provider or self._default_system_status
        )
        self.action_router = SafeActionRouter(
            user_profile=self.user_profile,
            dialogue_manager=self.dialogue_manager,
        )
        self.voice_input_manager = None
        if voice_output_manager is None:
            from voice.voice_output_manager import VoiceOutputManager

            voice_output_manager = VoiceOutputManager()
        self.voice_output_manager = voice_output_manager
        self.assistant_response_history = (
            assistant_response_history or AssistantResponseHistory()
        )
        self.voice_dialogue_mode_manager = (
            voice_dialogue_mode_manager or VoiceDialogueModeManager()
        )
        self.vosk_runtime_loader = vosk_runtime_loader
        self.vosk_recognition_dry_run = vosk_recognition_dry_run
        self.one_shot_vosk_recognition_bridge = one_shot_vosk_recognition_bridge
        self.one_shot_vosk_real_recognition = one_shot_vosk_real_recognition
        self.audio_dependency_readiness_checker = audio_dependency_readiness_checker
        self.safe_voice_command_allowlist = safe_voice_command_allowlist
        if voice_command_history is None:
            from voice.voice_command_history import VoiceCommandSessionHistory

            voice_command_history = VoiceCommandSessionHistory()
        self.voice_command_history = voice_command_history
        self.voice_interaction_controls = VoiceInteractionControls(
            self.assistant_response_history,
            self.voice_command_history,
        )
        if voice_recognition_correction_manager is None:
            from voice.voice_recognition_corrections import (
                VoiceRecognitionCorrectionManager,
            )

            voice_recognition_correction_manager = (
                VoiceRecognitionCorrectionManager()
            )
        self.voice_recognition_correction_manager = (
            voice_recognition_correction_manager
        )
        self._pending_voice_command = None
        if microphone_listening_mode_manager is None:
            from voice.microphone_listening_modes import (
                MicrophoneListeningModeManager,
            )

            microphone_listening_mode_manager = MicrophoneListeningModeManager()
        self.microphone_listening_mode_manager = microphone_listening_mode_manager

    def set_voice_input_manager(self, voice_input_manager):
        self.voice_input_manager = voice_input_manager

    def set_voice_output_manager(self, voice_output_manager):
        self.voice_output_manager = voice_output_manager

    def process(self, command_text):
        self._current_source_command = str(command_text or "").strip()
        command = self._normalize(command_text)

        if not command:
            return self._result(
                "empty",
                self.dialogue_manager.empty_command_response(),
            )

        if command in self.SPEECH_BACKEND_STATUS_COMMANDS:
            status = (
                self.voice_input_manager.get_speech_backend_status()
                if self.voice_input_manager is not None
                else {
                    "name": "none",
                    "available": False,
                    "requires_permission": False,
                    "requires_installation": False,
                    "supports_streaming": False,
                    "supports_offline": False,
                }
            )
            return self._result(
                "speech.backend.status",
                self.dialogue_manager.speech_backend_status_response(status),
            )

        if command in self.AUDIO_DEPENDENCY_READINESS_COMMANDS:
            readiness = self._get_audio_dependency_readiness_checker().check()
            return self._result(
                "voice.audio_dependencies.status",
                self._audio_dependency_readiness_response(readiness),
            )

        if command in self.SPEECH_BACKEND_EXPLAIN_COMMANDS:
            return self._result(
                "speech.backend.explain",
                self.dialogue_manager.speech_backend_explain_response(),
            )

        if command in self.SPEECH_BACKEND_OPTIONS_COMMANDS:
            return self._result(
                "speech.backend.options",
                self.dialogue_manager.speech_backend_options_response(),
            )

        if command in self.VOSK_RECOGNITION_STATUS_COMMANDS:
            gate_result = self._get_vosk_recognition_gate_result()
            return self._result(
                "speech.backend.vosk.recognition.status",
                self._vosk_recognition_status_response(gate_result),
            )

        typed_simulation_text = self._extract_typed_voice_recognition_simulation_text(
            command_text,
            command,
        )
        if typed_simulation_text is not None:
            return self._process_typed_voice_recognition_simulation(
                typed_simulation_text
            )

        voice_output_text = self._extract_voice_output_text(command_text, command)
        if voice_output_text is not None:
            return self._voice_output_speak_result(voice_output_text)

        if command in self.VOICE_OUTPUT_STATUS_COMMANDS:
            return self._result(
                "voice.output.status",
                self.voice_output_manager.status_message(),
            )

        if command in self.VOICE_OUTPUT_MUTE_COMMANDS:
            self.voice_output_manager.safety_controller.request_stop()
            self.voice_dialogue_mode_manager.disable()
            return self._result(
                "voice.output.safety.muted",
                (
                    "Голосовая озвучка остановлена для следующих ответов.\n"
                    "Тихий режим: включён.\n"
                    "Голосовой диалог отключён.\n"
                    "Примечание: уже запущенная синхронная речь Windows может завершиться сама; "
                    "мгновенное прерывание будет отдельным этапом."
                ),
                speakable=False,
                allow_manual_dialogue=False,
            )

        if command in self.VOICE_OUTPUT_UNMUTE_COMMANDS:
            self.voice_output_manager.safety_controller.unmute()
            return self._result(
                "voice.output.safety.unmuted",
                (
                    "Тихий режим отключён.\n"
                    "Голосовая озвучка снова разрешена.\n"
                    "Чтобы JARVIS озвучивал текущие ответы, включите голосовой диалог отдельно."
                ),
                speakable=False,
            )

        if command in self.VOICE_OUTPUT_SKIP_NEXT_COMMANDS:
            self.voice_output_manager.safety_controller.skip_next_speech()
            return self._result(
                "voice.output.safety.skip_next",
                (
                    "Следующая голосовая озвучка будет пропущена.\n"
                    "После этого обычные настройки голоса сохранятся."
                ),
                speakable=False,
            )

        if command in self.VOICE_OUTPUT_SAFETY_STATUS_COMMANDS:
            return self._result(
                "voice.output.safety.status",
                self._voice_output_safety_status_response(),
                speakable=False,
            )

        if command in self.VOICE_OUTPUT_DRY_RUN_ENABLE_COMMANDS:
            result = self.voice_output_manager.enable_dry_run()
            return self._result("voice.output.dry_run.enabled", result["message"])

        if command in self.VOICE_OUTPUT_LOCAL_STATUS_COMMANDS:
            result = self.voice_output_manager.local_tts_status()
            return self._result("voice.output.local.status", result["message"])

        if command in self.VOICE_OUTPUT_LOCAL_ENABLE_COMMANDS:
            result = self.voice_output_manager.enable_windows_local()
            intent = (
                "voice.output.windows_local.enabled"
                if result["enabled"]
                else "voice.output.windows_local.unavailable"
            )
            return self._result(intent, result["message"])

        if command in self.VOICE_OUTPUT_DISABLE_COMMANDS:
            result = self.voice_output_manager.disable()
            response = result["message"]
            if self.voice_dialogue_mode_manager.is_manual_enabled():
                self.voice_dialogue_mode_manager.disable()
                response = (
                    "Голосовой ответ отключён.\n"
                    "Голосовой диалог также отключён."
                )
            return self._result("voice.output.disabled", response)

        if command in self.VOICE_OUTPUT_LOCAL_TEST_COMMANDS:
            return self._voice_output_local_test_result()

        if command in self.VOICE_OUTPUT_TEST_COMMANDS:
            return self._voice_output_test_result()

        if command in self.VOICE_OUTPUT_CAPABILITIES_COMMANDS:
            return self._result(
                "voice.output.capabilities",
                self.voice_output_manager.capabilities_message(),
                speakable=False,
            )

        if command in self.ASSISTANT_LAST_RESPONSE_COMMANDS:
            return self._last_assistant_response_result()

        if command in self.ASSISTANT_SPEAK_LAST_RESPONSE_COMMANDS:
            return self._speak_last_assistant_response_result()

        if command in self.ASSISTANT_RESPONSE_HISTORY_COMMANDS:
            return self._assistant_response_history_result()

        if command in self.ASSISTANT_RESPONSE_HISTORY_COUNT_COMMANDS:
            return self._assistant_response_history_count_result()

        if command in self.ASSISTANT_RESPONSE_HISTORY_CLEAR_COMMANDS:
            self.assistant_response_history.clear()
            return self._result(
                "assistant.response_history.clear",
                "История ответов JARVIS за текущую сессию очищена.",
                speakable=False,
            )

        if command in self.ASSISTANT_CLARIFY_SHORT_COMMANDS:
            return self._short_last_assistant_response_result()

        if command in self.ASSISTANT_CLARIFY_SIMPLE_COMMANDS:
            return self._simple_last_assistant_response_result()

        if command in self.VOICE_DIALOGUE_STATUS_COMMANDS:
            return self._result(
                "voice.dialogue.status",
                self._voice_dialogue_status_response(),
                speakable=False,
            )

        if command in self.VOICE_DIALOGUE_ENABLE_COMMANDS:
            return self._enable_voice_dialogue_result()

        if command in self.VOICE_DIALOGUE_DISABLE_COMMANDS:
            self.voice_dialogue_mode_manager.disable()
            return self._result(
                "voice.dialogue.disabled",
                (
                    "Голосовой диалог отключён.\n"
                    "JARVIS больше не будет озвучивать текущие ответы автоматически."
                ),
                speakable=False,
            )

        if command in self.VOSK_RECOGNITION_DRY_RUN_COMMANDS:
            dry_run_result = self._get_vosk_recognition_dry_run().run()
            return self._result(
                "speech.backend.vosk.recognition.dry_run",
                self._vosk_recognition_dry_run_response(dry_run_result),
            )

        if command in self.ONE_SHOT_VOSK_BRIDGE_COMMANDS:
            bridge_result = self._get_one_shot_vosk_recognition_bridge().run_once(
                explicit_one_shot_requested=True
            )
            return self._result(
                "speech.backend.vosk.one_shot_bridge",
                self._one_shot_vosk_bridge_response(bridge_result),
            )

        if command in self.ONE_SHOT_VOSK_REAL_RECOGNITION_COMMANDS:
            recognition_result = self._get_one_shot_vosk_real_recognition().run_once(
                explicit_one_shot_requested=True
            )
            one_shot_result = self._one_shot_vosk_real_recognition_response(
                recognition_result
            )
            if isinstance(one_shot_result, dict):
                return one_shot_result
            return self._result(
                "speech.backend.vosk.one_shot_real_recognition",
                one_shot_result,
            )

        if command in self.PENDING_VOICE_COMMAND_STATUS_COMMANDS:
            return self._result(
                "voice.pending_command.status",
                self._pending_voice_command_status_response(),
            )

        if command in self.SAFE_VOICE_COMMAND_ALLOWLIST_COMMANDS:
            return self._result(
                "voice.safe_allowlist.status",
                self._safe_voice_command_allowlist_response(),
            )

        if command in self.LAST_VOICE_RECOGNITION_COMMANDS:
            return self._result(
                "voice.history.last",
                self.voice_interaction_controls.format_last_voice_command_for_display(),
                speakable=False,
            )

        if command in self.REPEAT_LAST_VOICE_COMMAND_COMMANDS:
            return self._repeat_last_voice_command_result()

        if command in self.VOICE_COMMAND_HISTORY_COMMANDS:
            return self._result(
                "voice.history.list",
                self._voice_command_history_response(),
            )

        if command in self.VOICE_COMMAND_HISTORY_COUNT_COMMANDS:
            return self._result(
                "voice.history.count",
                self._voice_command_history_count_response(),
            )

        if command in self.VOICE_COMMAND_HISTORY_CLEAR_COMMANDS:
            self.voice_command_history.clear()
            return self._result(
                "voice.history.cleared",
                "История голосовых команд за текущую сессию очищена.",
            )

        correction_parts = self._parse_voice_recognition_correction(command)
        if correction_parts is not None:
            wrong_text, corrected_text = correction_parts
            correction = self.voice_recognition_correction_manager.add_correction(
                wrong_text,
                corrected_text,
            )
            self._record_voice_history(
                recognized_text=correction.wrong_text,
                corrected_text=correction.corrected_text,
                normalized_text=correction.normalized_wrong_text,
                canonical_command=correction.corrected_text,
                source=correction.source,
                status="correction_added",
                reason="explicit user session correction",
            )
            return self._result(
                "voice.recognition_correction.added",
                self._voice_recognition_correction_added_response(correction),
            )

        if command in self.VOICE_RECOGNITION_CORRECTION_LIST_COMMANDS:
            return self._result(
                "voice.recognition_correction.list",
                self._voice_recognition_corrections_response(),
            )

        if command in self.VOICE_RECOGNITION_CORRECTION_COUNT_COMMANDS:
            return self._result(
                "voice.recognition_correction.count",
                self._voice_recognition_corrections_count_response(),
            )

        if command in self.VOICE_RECOGNITION_CORRECTION_CLEAR_COMMANDS:
            self.voice_recognition_correction_manager.clear()
            return self._result(
                "voice.recognition_correction.cleared",
                "Голосовые исправления текущей сессии очищены.",
            )

        if command in self.PENDING_VOICE_COMMAND_CLEAR_COMMANDS and self.has_pending_voice_command():
            pending_command = self.get_pending_voice_command()
            self.clear_pending_voice_command()
            self._record_voice_history(
                recognized_text=pending_command,
                normalized_text=self._normalize(pending_command),
                status="canceled",
                reason="pending command cleared",
            )
            return self._result(
                "voice.pending_command.cleared",
                "Ожидающая голосовая команда очищена.",
            )

        if command in self.EXIT_COMMANDS:
            self.clear_pending_voice_command()
            return self._result(
                "system.exit",
                self.dialogue_manager.exit_response(),
                should_exit=True,
            )

        if self.has_pending_voice_command():
            return self._process_pending_voice_command_confirmation(command)

        if command in self.VOSK_BACKEND_STATUS_COMMANDS:
            status = (
                self.voice_input_manager.get_vosk_backend_status()
                if self.voice_input_manager is not None
                else {
                    "name": "vosk_local",
                    "available": False,
                    "supports_offline": True,
                }
            )
            return self._result(
                "speech.backend.vosk.status",
                self.dialogue_manager.speech_backend_status_response(status),
            )

        if command in self.VOSK_BACKEND_SELECT_COMMANDS:
            if self.voice_input_manager is None:
                return self._result(
                    "speech.backend.select.unavailable",
                    self.dialogue_manager.speech_backend_selection_unavailable_response(),
                )
            status = self.voice_input_manager.use_vosk_backend()
            return self._result(
                "speech.backend.vosk.select",
                self.dialogue_manager.speech_backend_selected_response(status),
            )

        if command in self.VOSK_BACKEND_PLAN_COMMANDS:
            return self._result(
                "speech.backend.vosk.plan",
                self.dialogue_manager.vosk_backend_plan_response(),
            )

        if command in self.VOSK_RUNTIME_STATUS_COMMANDS:
            loader = self._get_vosk_runtime_loader()
            return self._result(
                "speech.backend.vosk.runtime.status",
                self.dialogue_manager.vosk_runtime_status_response(
                    loader.get_runtime_status()
                ),
            )

        if command in self.VOSK_RUNTIME_BLOCKERS_COMMANDS:
            loader = self._get_vosk_runtime_loader()
            return self._result(
                "speech.backend.vosk.runtime.blockers",
                self.dialogue_manager.vosk_runtime_blockers_response(
                    loader.get_blockers()
                ),
            )

        if command in self.VOSK_RUNTIME_SAFETY_COMMANDS:
            loader = self._get_vosk_runtime_loader()
            return self._result(
                "speech.backend.vosk.runtime.safety",
                self.dialogue_manager.vosk_runtime_safety_response(
                    loader.get_safety_summary()
                ),
            )

        if command in self.VOSK_RUNTIME_PREPARE_COMMANDS:
            loader = self._get_vosk_runtime_loader()
            return self._result(
                "speech.backend.vosk.runtime.prepare.stub",
                self.dialogue_manager.vosk_runtime_prepare_response(
                    loader.prepare_runtime_stub()
                ),
            )

        if command in self.VOSK_RUNTIME_RECOGNIZE_COMMANDS:
            loader = self._get_vosk_runtime_loader()
            return self._result(
                "speech.backend.vosk.runtime.recognition.disabled",
                self.dialogue_manager.vosk_runtime_recognition_disabled_response(
                    loader.recognize_text_stub()
                ),
            )

        if command in self.VOSK_INSTALLATION_GUIDE_COMMANDS:
            guide = self._get_vosk_installation_guide()
            return self._result(
                "speech.backend.vosk.installation.guide",
                self.dialogue_manager.vosk_installation_guide_response(
                    guide.get_installation_summary()
                ),
            )

        if command in self.VOSK_MODEL_INSTALLATION_GUIDE_COMMANDS:
            return self._result(
                "speech.backend.vosk.model.installation.guide",
                self._vosk_model_installation_guidance_response(),
            )

        if command in self.VOSK_PYTHON_COMPATIBILITY_COMMANDS:
            guide = self._get_vosk_installation_guide()
            return self._result(
                "speech.backend.vosk.compatibility",
                self.dialogue_manager.vosk_python_compatibility_response(
                    guide.get_python_version_status()
                ),
            )

        if command in self.VOSK_MODEL_GUIDE_COMMANDS:
            guide = self._get_vosk_installation_guide()
            return self._result(
                "speech.backend.vosk.model.guide",
                self.dialogue_manager.vosk_model_download_guidance_response(
                    guide.get_recommended_model(),
                    guide.get_model_download_guidance(),
                ),
            )

        if command in self.VOSK_SAFE_ENABLEMENT_COMMANDS:
            guide = self._get_vosk_installation_guide()
            return self._result(
                "speech.backend.vosk.enablement.plan",
                self.dialogue_manager.vosk_safe_enablement_response(
                    guide.get_safe_enablement_steps()
                ),
            )

        if command in self.VOSK_RISKS_COMMANDS:
            guide = self._get_vosk_installation_guide()
            return self._result(
                "speech.backend.vosk.risks",
                self.dialogue_manager.vosk_runtime_risks_response(
                    guide.get_runtime_risks()
                ),
            )

        if command in self.VOSK_PREFLIGHT_COMMANDS:
            preflight = self._get_vosk_preflight()
            return self._result(
                "speech.backend.vosk.preflight",
                self.dialogue_manager.vosk_preflight_response(preflight),
            )

        if command in self.VOSK_MISSING_REQUIREMENTS_COMMANDS:
            preflight = self._get_vosk_preflight()
            return self._result(
                "speech.backend.vosk.requirements",
                self.dialogue_manager.vosk_missing_requirements_response(
                    preflight["missing_requirements"]
                ),
            )

        if command in self.VOSK_MODEL_STATUS_COMMANDS:
            readiness = self._get_vosk_model_readiness()
            return self._result(
                "speech.backend.vosk.model.status",
                self._vosk_model_readiness_response(readiness),
            )

        if command in self.VOSK_MODEL_PATH_STATUS_COMMANDS:
            status = self._get_vosk_model_status()
            return self._result(
                "speech.backend.vosk.model.path.status",
                self._vosk_model_path_status_response(status),
            )

        if command in self.VOSK_MODEL_PATH_CLEAR_COMMANDS:
            if self.voice_input_manager is None:
                return self._result(
                    "speech.backend.vosk.model_path.unavailable",
                    self.dialogue_manager.speech_backend_selection_unavailable_response(),
                )
            preflight = self.voice_input_manager.clear_vosk_model_path()
            return self._result(
                "speech.backend.vosk.model.path.cleared",
                self._vosk_model_path_cleared_response(preflight),
            )

        if command in self.VOSK_SETTINGS_COMMANDS:
            status = self._get_vosk_model_status()
            return self._result(
                "speech.backend.vosk.settings",
                self.dialogue_manager.vosk_settings_response(status),
            )

        if command in self.VOSK_LANGUAGE_STATUS_COMMANDS:
            status = self._get_vosk_model_status()
            return self._result(
                "speech.backend.vosk.language.status",
                self.dialogue_manager.vosk_language_status_response(
                    status.get("language", "ru")
                ),
            )

        language = self._extract_prefixed_value(
            command_text, command, self.VOSK_LANGUAGE_PREFIXES
        )
        if language is not None:
            if not language:
                return self._result(
                    "speech.backend.vosk.language.missing",
                    self.dialogue_manager.vosk_language_required_response(),
                )
            if self.voice_input_manager is None:
                return self._result(
                    "speech.backend.vosk.language.unavailable",
                    self.dialogue_manager.speech_backend_selection_unavailable_response(),
                )
            status = self.voice_input_manager.configure_vosk_language(language)
            return self._result(
                "speech.backend.vosk.language.set",
                self.dialogue_manager.vosk_language_configured_response(
                    language, status
                ),
            )

        model_path = self._extract_vosk_model_path(command_text, command)
        if model_path is not None:
            if not model_path:
                return self._result(
                    "speech.backend.vosk.model_path.missing",
                    self._vosk_model_path_required_response(),
                )
            if self.voice_input_manager is None:
                return self._result(
                    "speech.backend.vosk.model_path.unavailable",
                    self.dialogue_manager.speech_backend_selection_unavailable_response(),
                )
            preflight = self.voice_input_manager.configure_vosk_model_path(model_path)
            return self._result(
                "speech.backend.vosk.model.path.set",
                self._vosk_model_path_configured_response(model_path, preflight),
            )

        if command in self.MICROPHONE_STATUS_COMMANDS:
            return self._microphone_mode_status_result()

        if command in self.MICROPHONE_MODE_OFF_COMMANDS:
            return self._set_microphone_mode_result(
                "microphone.mode.off",
                "off",
            )

        if command in self.MICROPHONE_MODE_PARTIAL_COMMANDS:
            return self._set_microphone_mode_result(
                "microphone.mode.partial",
                "partial",
            )

        if command in self.MICROPHONE_MODE_CONTINUOUS_COMMANDS:
            return self._set_microphone_mode_result(
                "microphone.mode.continuous",
                "continuous",
            )

        if command in self.MICROPHONE_MODE_DISABLE_CONTINUOUS_COMMANDS:
            return self._set_microphone_mode_result(
                "microphone.mode.off",
                "off",
            )

        if command in self.MICROPHONE_ADAPTER_STATUS_COMMANDS:
            return self._microphone_result(
                "microphone.status",
                "microphone_status",
            )

        if command in self.MICROPHONE_PERMISSION_REQUEST_COMMANDS:
            return self._microphone_result(
                "microphone.permission.requested",
                "request_microphone_permission",
            )

        if command in self.MICROPHONE_PERMISSION_GRANT_COMMANDS:
            return self._microphone_result(
                "microphone.permission.granted",
                "grant_microphone_permission",
            )

        if command in self.MICROPHONE_PERMISSION_REVOKE_COMMANDS:
            return self._microphone_result(
                "microphone.permission.revoked",
                "revoke_microphone_permission",
            )

        if command in self.MICROPHONE_LISTEN_START_COMMANDS:
            return self._microphone_result(
                "microphone.listen.start",
                "start_microphone_input",
            )

        if command in self.MICROPHONE_LISTEN_STOP_COMMANDS:
            return self._microphone_result(
                "microphone.listen.stop",
                "stop_microphone_input",
            )

        if command in self.MICROPHONE_LISTEN_ONCE_COMMANDS:
            return self._microphone_result(
                "microphone.listen.once",
                "listen_once_from_microphone",
            )

        if self._is_voice_simulation_command(command):
            return self._process_voice_simulation(command)

        if command in self.VOICE_CONFIRMATION_COMMANDS:
            if self.voice_input_manager is None:
                if self._is_pending_voice_confirmation_word(command):
                    return self._result(
                        "voice.pending_command.none",
                        self._pending_voice_command_none_response(),
                    )
                return self._result(
                    "voice.confirmation.none",
                    self.dialogue_manager.voice_confirmation_none_response(),
                )

            if (
                self._is_pending_voice_confirmation_word(command)
                and not self.voice_input_manager.has_pending_confirmation()
            ):
                return self._result(
                    "voice.pending_command.none",
                    self._pending_voice_command_none_response(),
                )

            return self.voice_input_manager.confirm_pending_action()

        if command in self.VOICE_CANCELLATION_COMMANDS:
            if self.voice_input_manager is None:
                if self._is_pending_voice_confirmation_word(command):
                    return self._result(
                        "voice.pending_command.none",
                        self._pending_voice_command_none_response(),
                    )
                return self._result(
                    "voice.confirmation.none",
                    self.dialogue_manager.voice_cancellation_none_response(),
                )

            if (
                self._is_pending_voice_confirmation_word(command)
                and not self.voice_input_manager.has_pending_confirmation()
            ):
                return self._result(
                    "voice.pending_command.none",
                    self._pending_voice_command_none_response(),
                )

            return self.voice_input_manager.cancel_pending_action()

        if self._is_pending_voice_confirmation_word(command):
            return self._result(
                "voice.pending_command.none",
                self._pending_voice_command_none_response(),
            )

        if command in self.GREETING_COMMANDS:
            return self._result("assistant.greeting", self._greeting_response())

        if command in self.USER_IDENTITY_COMMANDS:
            return self._result(
                "user.identity",
                self.dialogue_manager.identity_response(),
            )

        if command in self.ASSISTANT_IDENTITY_COMMANDS:
            return self._result(
                "assistant.identity",
                self._assistant_name_response(),
            )

        assistant_name = self._extract_assistant_name(command_text, command)
        if assistant_name is not None:
            return self._change_assistant_name(assistant_name)

        if command in self.ASSISTANT_NAME_RESET_COMMANDS:
            return self._reset_assistant_name()

        if command in self.PROFILE_COMMANDS:
            return self._result(
                "user.profile",
                self.dialogue_manager.profile_response(),
            )

        if command in self.VERSION_COMMANDS:
            status = self.system_status_provider()
            return self._result(
                "system.version",
                self.dialogue_manager.version_response(status["version"]),
            )

        if command in self.SYSTEM_STATUS_COMMANDS:
            return self._result(
                "system.status",
                self.dialogue_manager.system_status_response(
                    self.system_status_provider()
                ),
            )

        if command in self.SYSTEM_SERVICES_COMMANDS:
            status = self.system_status_provider()
            return self._result(
                "system.services",
                self.dialogue_manager.services_response(status["services"]),
            )

        if command in self.VOICE_STATUS_COMMANDS:
            return self._result(
                "voice.status",
                self.dialogue_manager.voice_not_real_microphone_response(),
            )

        if command in self.VOICE_ENABLE_COMMANDS:
            return self._result(
                "voice.enable",
                self.dialogue_manager.voice_enabled_response(),
            )

        if command in self.VOICE_DISABLE_COMMANDS:
            return self._result(
                "voice.disable",
                self.dialogue_manager.voice_disabled_response(),
            )

        if command in self.COMMANDS_LIST_COMMANDS:
            return self._result(
                "assistant.commands",
                self.dialogue_manager.commands_response(),
            )

        if command in self.CAPABILITIES_COMMANDS:
            return self._result(
                "assistant.help",
                self._help_response(),
            )

        if command in self.MEMORY_DELETE_COMMANDS:
            return self._result(
                "memory.delete.requested",
                self.dialogue_manager.memory_delete_requires_future_confirmation_response(),
            )

        if self._is_idea_add_command(command):
            return self._add_idea(command)

        if self._is_memory_add_command(command):
            return self._add_memory(command)

        if command in self.MEMORY_COUNT_COMMANDS:
            return self._count_memories()

        if command in self.MEMORY_RECENT_COMMANDS:
            return self._recent_memories()

        if command in self.MEMORY_ABOUT_USER_COMMANDS:
            return self._about_user_memories()

        if command in self.MEMORY_LIST_COMMANDS:
            return self._list_memories()

        if self._is_memory_search_command(command):
            return self._search_memories(command)

        if command in self.IDEA_LIST_COMMANDS:
            return self._list_ideas()

        if command in self.IDEA_COUNT_COMMANDS:
            return self._count_ideas()

        route = self.action_router.route(command)
        return self._route_result(route)

    def _normalize(self, command_text):
        if command_text is None:
            return ""

        return " ".join(str(command_text).strip().lower().split())

    def _get_vosk_preflight(self):
        if self.voice_input_manager is None:
            from voice.vosk_local_backend import VoskLocalBackend

            return VoskLocalBackend().preflight_check()
        return self.voice_input_manager.get_vosk_preflight()

    @staticmethod
    def _get_vosk_installation_guide():
        from voice.vosk_installation_guide import VoskInstallationGuide

        return VoskInstallationGuide()

    def _get_vosk_model_status(self):
        if self.voice_input_manager is None:
            from voice.vosk_local_backend import VoskLocalBackend

            return VoskLocalBackend().get_status()
        return self.voice_input_manager.get_vosk_backend_status()

    def _get_vosk_model_readiness(self):
        from voice.vosk_model_readiness_verifier import VoskModelReadinessVerifier

        status = self._get_vosk_model_status()
        return VoskModelReadinessVerifier().verify(status.get("model_path"))

    def _get_vosk_recognition_gate_result(self):
        from voice.vosk_local_recognition_gate import (
            evaluate_vosk_local_recognition_gate,
        )

        status = self._get_vosk_model_status()
        return evaluate_vosk_local_recognition_gate(
            model_path=status.get("model_path"),
            package_available=status.get("vosk_package_available"),
            explicit_activation_required=True,
            microphone_capture_automatic=False,
            recognition_continuous=False,
        )

    def _get_vosk_recognition_dry_run(self):
        if self.vosk_recognition_dry_run is None:
            from voice.vosk_local_recognition_dry_run import (
                VoskLocalRecognitionDryRun,
            )

            self.vosk_recognition_dry_run = VoskLocalRecognitionDryRun(
                gate_checker=self._get_vosk_recognition_gate_result
            )
        return self.vosk_recognition_dry_run

    def _get_one_shot_vosk_recognition_bridge(self):
        if self.one_shot_vosk_recognition_bridge is None:
            from voice.one_shot_vosk_recognition_bridge import (
                OneShotVoskRecognitionBridge,
            )

            self.one_shot_vosk_recognition_bridge = OneShotVoskRecognitionBridge(
                gate_checker=self._get_vosk_recognition_gate_result
            )
        return self.one_shot_vosk_recognition_bridge

    def _get_one_shot_vosk_real_recognition(self):
        if self.one_shot_vosk_real_recognition is None:
            from voice.one_shot_vosk_real_recognition import (
                OneShotVoskRealRecognition,
            )

            self.one_shot_vosk_real_recognition = OneShotVoskRealRecognition()
        return self.one_shot_vosk_real_recognition

    def _get_audio_dependency_readiness_checker(self):
        if self.audio_dependency_readiness_checker is None:
            from voice.audio_dependency_readiness import (
                AudioDependencyReadinessChecker,
            )

            self.audio_dependency_readiness_checker = (
                AudioDependencyReadinessChecker()
            )
        return self.audio_dependency_readiness_checker

    def _get_safe_voice_command_allowlist(self):
        if self.safe_voice_command_allowlist is None:
            from voice.voice_command_allowlist import SafeVoiceCommandAllowlist

            self.safe_voice_command_allowlist = SafeVoiceCommandAllowlist()
        return self.safe_voice_command_allowlist

    @staticmethod
    def _audio_dependency_readiness_response(readiness):
        from voice.audio_dependency_readiness import (
            AudioDependencyReadinessChecker,
        )

        return AudioDependencyReadinessChecker.format_russian(readiness)

    @staticmethod
    def _vosk_recognition_status_response(gate_result):
        lines = [
            gate_result.message,
            (
                "Локальное распознавание Vosk сейчас разрешено: "
                + ("да." if gate_result.allowed else "нет.")
            ),
        ]

        if gate_result.blockers:
            lines.append("Причины:")
            lines.extend(f"- {blocker}" for blocker in gate_result.blockers)

        if gate_result.warnings:
            lines.append("Предупреждения:")
            lines.extend(f"- {warning}" for warning in gate_result.warnings)

        if gate_result.next_steps:
            lines.append("Следующие шаги:")
            lines.extend(f"- {step}" for step in gate_result.next_steps)

        lines.extend(
            [
                "Микрофон не запускается автоматически.",
                (
                    "Постоянное прослушивание пока не связано с реальным "
                    "распознаванием."
                ),
            ]
        )
        return "\n".join(lines)

    @staticmethod
    def _vosk_recognition_dry_run_response(dry_run_result):
        result_text = (
            "Пробный запуск Vosk выполнен."
            if dry_run_result.success
            else "Пробный запуск Vosk заблокирован."
        )
        lines = [
            result_text,
        ]

        if dry_run_result.recognized_text:
            lines.append(f"Тестовый распознанный текст: {dry_run_result.recognized_text}")

        if dry_run_result.blockers:
            lines.append("Причины:")
            lines.extend(f"- {blocker}" for blocker in dry_run_result.blockers)

        if dry_run_result.warnings:
            lines.append("Предупреждения:")
            lines.extend(f"- {warning}" for warning in dry_run_result.warnings)

        lines.append(
            "Безопасность: использовались только тестовые данные, микрофон не запускался, "
            "настоящая модель Vosk не загружалась, реальное распознавание не запускалось."
        )

        if dry_run_result.next_steps:
            lines.append(f"Следующий шаг: {dry_run_result.next_steps[0]}")

        return "\n".join(lines)

    @staticmethod
    def _one_shot_vosk_bridge_response(bridge_result):
        from voice.one_shot_vosk_recognition_bridge import OneShotVoskRecognitionBridge

        lines = [OneShotVoskRecognitionBridge.format_result(bridge_result)]
        lines.append(
            "Это только проверка bridge/coordinator: реальное распознавание и выполнение команд будут подключаться отдельной задачей."
        )
        return "\n".join(lines)

    def _one_shot_vosk_real_recognition_response(self, recognition_result):
        from voice.one_shot_vosk_real_recognition import OneShotVoskRealRecognition

        recognized_text = str(recognition_result.recognized_text or "").strip()
        if (
            recognition_result.allowed
            and recognition_result.completed
            and not recognition_result.blocked
            and recognized_text
        ):
            return self._process_recognized_voice_command_text(
                recognized_text,
                source="one_shot_vosk",
                completion_label="Распознавание завершено.",
                safe_response_style="one_shot_vosk",
                pending_intent=None,
            )
        elif recognition_result.blocked or not recognition_result.allowed:
            self._record_voice_history(
                recognized_text=recognized_text or None,
                status="blocked",
                reason=self._join_reasons(getattr(recognition_result, "reasons", None)),
                safety_notes=getattr(recognition_result, "safety_notes", None),
            )
        elif not recognition_result.completed:
            self._record_voice_history(
                recognized_text=recognized_text or None,
                status="failed",
                reason=self._join_reasons(getattr(recognition_result, "reasons", None)),
                safety_notes=getattr(recognition_result, "safety_notes", None),
            )
        elif not recognized_text:
            self._record_voice_history(
                recognized_text=None,
                status="empty",
                reason="speech not recognized",
                safety_notes=getattr(recognition_result, "safety_notes", None),
            )

        return OneShotVoskRealRecognition.format_result(recognition_result)

    def _process_typed_voice_recognition_simulation(self, recognized_text):
        recognized_text = str(recognized_text or "").strip()
        if not recognized_text:
            return self._result(
                "voice.recognition.typed_simulation.empty",
                "Укажите текст для симуляции распознавания.",
            )

        result = self._process_recognized_voice_command_text(
            recognized_text,
            source="typed_simulation",
            completion_label="Симуляция распознавания завершена.",
            safe_response_style="typed_simulation",
            pending_intent="voice.recognition.typed_simulation",
        )
        if isinstance(result, dict):
            result = dict(result)
            result["voice_recognition_source"] = "typed_simulation"
        return result

    def _process_recognized_voice_command_text(
        self,
        recognized_text,
        source="one_shot_vosk",
        completion_label="Распознавание завершено.",
        safe_response_style="one_shot_vosk",
        pending_intent=None,
    ):
        if self.has_pending_voice_command():
            pending_command = self.get_pending_voice_command()
            self._record_voice_history(
                recognized_text=pending_command,
                normalized_text=self._normalize(pending_command),
                source=source,
                status="canceled",
                reason="pending command replaced by new recognition",
            )
        self.clear_pending_voice_command()

        correction = self.voice_recognition_correction_manager.find_correction(
            recognized_text
        )
        command_text = (
            correction.corrected_text if correction is not None else recognized_text
        )
        decision = self._get_safe_voice_command_allowlist().decide(command_text)
        if decision.allowed:
            return self._execute_safe_voice_allowlisted_command(
                recognized_text,
                decision,
                correction=correction,
                source=source,
                completion_label=completion_label,
                response_style=safe_response_style,
            )

        self.set_pending_voice_command(command_text)
        self._record_voice_history(
            recognized_text=recognized_text,
            corrected_text=correction.corrected_text if correction else None,
            normalized_text=decision.normalized_text,
            source=source,
            status="pending_confirmation",
            reason=(
                "session correction applied; " + decision.reason
                if correction
                else decision.reason
            ),
            safety_notes=decision.safety_notes,
        )
        response = self._pending_recognized_voice_command_response(
            recognized_text,
            decision,
            correction=correction,
            completion_label=completion_label,
        )
        if pending_intent is None:
            return response
        return self._result(pending_intent, response)

    def _execute_safe_voice_allowlisted_command(
        self,
        recognized_text,
        decision,
        correction=None,
        source="one_shot_vosk",
        completion_label="Распознавание завершено.",
        response_style="one_shot_vosk",
    ):
        self.clear_pending_voice_command()
        result = self.process(decision.canonical_command)
        self._record_voice_history(
            recognized_text=recognized_text,
            corrected_text=correction.corrected_text if correction else None,
            normalized_text=decision.normalized_text,
            canonical_command=decision.canonical_command,
            source=source,
            status="correction_applied" if correction else "allowlisted_executed",
            reason=(
                "session correction applied; " + decision.reason
                if correction
                else decision.reason
            ),
            safety_notes=decision.safety_notes,
        )
        result = dict(result)
        if correction is None:
            if response_style == "typed_simulation":
                result["response"] = (
                    f"{completion_label}\n"
                    f"Я распознал: \"{recognized_text}\".\n"
                    "Команда входит в безопасный read-only список. Выполняю.\n"
                    "Безопасность: симуляция не обходит CommandProcessor и ActionRouter.\n"
                    f"{result['response']}"
                )
            else:
                result["response"] = (
                    f"{completion_label}\n"
                    f"Я распознал безопасную голосовую команду: \"{recognized_text}\".\n"
                    "Команда входит в безопасный список и будет выполнена без дополнительного подтверждения.\n"
                    f"Выполняю: {decision.canonical_command}\n"
                    "Безопасность: разрешены только заранее известные read-only команды; рискованные команды всё ещё требуют подтверждения.\n"
                    f"{result['response']}"
                )
        else:
            result["response"] = (
                f"{completion_label}\n"
                f"Я распознал: \"{recognized_text}\".\n"
                f"Применено исправление текущей сессии: \"{correction.corrected_text}\".\n"
                "Команда входит в безопасный read-only список. Выполняю.\n"
                f"Выполняю: {decision.canonical_command}\n"
                "Безопасность: исправление действует только в текущей сессии и не обходит проверку команд.\n"
                f"{result['response']}"
            )
        result["safe_voice_command_allowed"] = True
        result["recognized_voice_command"] = recognized_text
        if correction is not None:
            result["corrected_voice_command"] = correction.corrected_text
        result["canonical_voice_command"] = decision.canonical_command
        return result

    def has_pending_voice_command(self):
        return self._pending_voice_command is not None

    def get_pending_voice_command(self):
        return self._pending_voice_command

    def set_pending_voice_command(self, recognized_text):
        normalized = str(recognized_text or "").strip()
        self._pending_voice_command = normalized or None

    def clear_pending_voice_command(self):
        self._pending_voice_command = None

    def _process_pending_voice_command_confirmation(self, command):
        pending_command = self.get_pending_voice_command()
        if command in self.PENDING_VOICE_COMMAND_POSITIVE_CONFIRMATIONS:
            self.clear_pending_voice_command()
            result = self.process(pending_command)
            canonical_command = result.get("canonical_voice_command") or pending_command
            status = self._confirmed_voice_command_history_status(result)
            self._record_voice_history(
                recognized_text=pending_command,
                normalized_text=self._normalize(pending_command),
                canonical_command=canonical_command,
                status=status,
                reason="typed confirmation accepted",
            )
            result = dict(result)
            result["response"] = (
                "Подтверждение получено. Передаю распознанную команду в безопасную обработку: "
                f"{pending_command}\n{result['response']}"
            )
            result["confirmed_voice_command"] = pending_command
            return result

        if command in self.PENDING_VOICE_COMMAND_NEGATIVE_CONFIRMATIONS:
            self.clear_pending_voice_command()
            self._record_voice_history(
                recognized_text=pending_command,
                normalized_text=self._normalize(pending_command),
                status="canceled",
                reason="typed cancellation accepted",
            )
            return self._result(
                "voice.pending_command.cancelled",
                "Хорошо, распознанная голосовая команда отменена.",
            )

        self._record_voice_history(
            recognized_text=pending_command,
            normalized_text=self._normalize(pending_command),
            status="unknown_confirmation",
            reason=f"unknown confirmation response: {command}",
        )
        return self._result(
            "voice.pending_command.awaiting_confirmation",
            (
                "Ожидаю подтверждение для распознанной команды: "
                f"{pending_command}. Ответьте: да / нет."
            ),
        )

    def _is_pending_voice_confirmation_word(self, command):
        return (
            command in self.PENDING_VOICE_COMMAND_POSITIVE_CONFIRMATIONS
            or command in self.PENDING_VOICE_COMMAND_NEGATIVE_CONFIRMATIONS
        )

    @staticmethod
    def _pending_voice_command_none_response():
        return "Нет голосовой команды, ожидающей подтверждения."

    @staticmethod
    def _confirmed_voice_command_history_status(result):
        if (
            result.get("requires_confirmation") is True
            or result.get("category") == "confirmation_required"
            or result.get("intent") == "action.confirmation_required"
        ):
            return "confirmed_requires_additional_safety_confirmation"
        return "confirmed_safe_processing"

    def _pending_voice_command_status_response(self):
        if not self.has_pending_voice_command():
            return self._pending_voice_command_none_response()

        return (
            "Ожидает подтверждения голосовая команда: "
            f"{self.get_pending_voice_command()}. Ответьте: да / нет."
        )

    def _safe_voice_command_allowlist_response(self):
        return self._get_safe_voice_command_allowlist().format_read_only_commands()

    def _parse_voice_recognition_correction(self, command):
        for prefix, separator in self.VOICE_RECOGNITION_CORRECTION_PREFIXES:
            if not command.startswith(prefix):
                continue
            payload = command[len(prefix) :].strip()
            if separator not in payload:
                continue
            wrong_text, corrected_text = payload.split(separator, 1)
            wrong_text = wrong_text.strip()
            corrected_text = corrected_text.strip()
            if wrong_text and corrected_text:
                return wrong_text, corrected_text
        return None

    @staticmethod
    def _voice_recognition_correction_added_response(correction):
        return (
            "Исправление распознавания добавлено для текущей сессии:\n"
            f"- Было: {correction.wrong_text}\n"
            f"- Должно быть: {correction.corrected_text}\n"
            "Безопасность: исправление действует только в текущей сессии и не обходит проверку команд."
        )

    def _voice_recognition_corrections_response(self):
        corrections = self.voice_recognition_correction_manager.list_corrections()
        if not corrections:
            return "В текущей сессии нет голосовых исправлений."

        lines = ["Голосовые исправления текущей сессии:"]
        for index, correction in enumerate(corrections, start=1):
            lines.append(
                f"{index}. {correction.wrong_text} -> {correction.corrected_text}"
            )
        return "\n".join(lines)

    def _voice_recognition_corrections_count_response(self):
        return (
            "Голосовых исправлений в текущей сессии: "
            f"{self.voice_recognition_correction_manager.count()}."
        )

    @staticmethod
    def _pending_recognized_voice_command_response(
        recognized_text,
        decision,
        correction=None,
        completion_label="Распознавание завершено.",
    ):
        safety = " ".join(decision.safety_notes or [])
        command_text = correction.corrected_text if correction else recognized_text
        correction_line = (
            f"Применено исправление текущей сессии: \"{correction.corrected_text}\".\n"
            if correction
            else ""
        )
        correction_safety = (
            "Безопасность: исправление действует только в текущей сессии и не обходит проверку команд.\n"
            if correction
            else ""
        )
        return (
            f"{completion_label}\n"
            f"Я распознал: \"{recognized_text}\".\n"
            f"{correction_line}"
            "Выполнить эту команду? Подтвердите: да / нет.\n"
            "Безопасность: команда не выполнена автоматически.\n"
            f"{correction_safety}"
            f"Ожидает подтверждения: {command_text}.\n"
            f"Безопасность: {safety}"
        )

    def _record_voice_history(
        self,
        recognized_text=None,
        corrected_text=None,
        normalized_text=None,
        canonical_command=None,
        source="one_shot_vosk",
        status="recognized",
        reason=None,
        safety_notes=None,
    ):
        return self.voice_command_history.add_entry(
            recognized_text=recognized_text,
            corrected_text=corrected_text,
            normalized_text=normalized_text,
            canonical_command=canonical_command,
            source=source,
            status=status,
            reason=reason,
            safety_notes=safety_notes,
        )

    @staticmethod
    def _join_reasons(reasons):
        if not reasons:
            return None
        return "; ".join(str(reason) for reason in reasons if str(reason).strip())

    def _last_voice_recognition_response(self):
        entry = self.voice_command_history.last_entry()
        if entry is None:
            return "В этой сессии ещё нет голосовых распознаваний."

        lines = [
            "Последнее голосовое распознавание:",
            f"- Распознано: {entry.recognized_text or 'пусто / речь не распознана'}",
        ]
        if entry.canonical_command:
            lines.append(f"- Каноническая команда: {entry.canonical_command}")
        if entry.corrected_text:
            lines.append(f"- Исправлено на: {entry.corrected_text}")
        lines.append(f"- Статус: {self._voice_history_status_label(entry.status)}")
        lines.append(f"- Источник: {self._voice_history_source_label(entry.source)}")
        if entry.reason:
            lines.append(f"- Причина: {entry.reason}")
        return "\n".join(lines)

    def _voice_command_history_response(self):
        entries = self.voice_command_history.list_recent(limit=10)
        if not entries:
            return "В этой сессии ещё нет голосовых распознаваний."

        lines = ["История голосовых команд за текущую сессию:"]
        for index, entry in enumerate(entries, start=1):
            source_text = entry.recognized_text or "пусто / речь не распознана"
            if entry.corrected_text:
                source_text = f"{source_text} -> {entry.corrected_text}"
            elif entry.canonical_command:
                source_text = f"{source_text} -> {entry.canonical_command}"
            lines.append(
                f"{index}. {source_text} — {self._voice_history_status_label(entry.status)} "
                f"(источник: {self._voice_history_source_label(entry.source)})"
            )
        return "\n".join(lines)

    def _voice_command_history_count_response(self):
        return (
            "В этой сессии записано голосовых событий: "
            f"{self.voice_command_history.count()}."
        )

    @staticmethod
    def _voice_history_source_label(source):
        labels = {
            "one_shot_vosk": "one-shot Vosk",
            "typed_simulation": "текстовая симуляция",
            "user_session_correction": "исправление текущей сессии",
        }
        return labels.get(source, source)

    @staticmethod
    def _voice_history_status_label(status):
        labels = {
            "recognized": "распознано",
            "correction_added": "исправление добавлено",
            "correction_applied": "исправление применено",
            "allowlisted_executed": "выполнено как безопасная read-only команда",
            "pending_confirmation": "ожидает подтверждения",
            "confirmed_executed": "подтверждено и передано в безопасную обработку",
            "confirmed_safe_processing": "подтверждено и передано в безопасную обработку",
            "confirmed_requires_additional_safety_confirmation": "требует дополнительного подтверждения безопасности",
            "canceled": "отменено",
            "blocked": "заблокировано",
            "empty": "пусто / речь не распознана",
            "failed": "ошибка распознавания",
            "unknown_confirmation": "неизвестный ответ на подтверждение",
        }
        return labels.get(status, status)

    @staticmethod
    def _vosk_model_readiness_response(readiness):
        from voice.vosk_model_readiness_verifier import VoskModelReadinessVerifier

        return VoskModelReadinessVerifier.format_russian(readiness)

    @staticmethod
    def _vosk_model_installation_guidance_response():
        from voice.vosk_model_readiness_verifier import VoskModelReadinessVerifier

        return VoskModelReadinessVerifier.INSTALLATION_GUIDANCE

    @staticmethod
    def _vosk_model_path_status_response(status):
        model_path = status.get("model_path")
        if not model_path:
            return "Путь к модели Vosk пока не указан."

        path_status = CommandProcessor._safe_model_path_filesystem_status(model_path)
        if not path_status["exists"]:
            return f"Путь к модели Vosk указан, но папка не найдена: {model_path}"
        if not path_status["is_directory"]:
            return f"Путь к модели Vosk указан, но это не папка: {model_path}"

        return (
            "Текущий путь к модели Vosk: "
            f"{model_path}\n"
            "Это только чтение настройки; файлы модели не открываются, "
            "модель не загружается и микрофон не запускается."
        )

    def _extract_vosk_model_path(self, command_text, normalized_command):
        value = self._extract_prefixed_value(
            command_text, normalized_command, self.VOSK_MODEL_PATH_PREFIXES
        )
        if value is None:
            return None
        return self._normalize_vosk_model_path_text(value)

    @staticmethod
    def _normalize_vosk_model_path_text(model_path):
        normalized = str(model_path).strip()
        if len(normalized) >= 2 and normalized[0] == normalized[-1]:
            if normalized[0] in {'"', "'"}:
                normalized = normalized[1:-1].strip()
        return normalized

    @staticmethod
    def _safe_model_path_filesystem_status(model_path):
        try:
            path = Path(model_path)
            exists = path.exists()
            is_directory = path.is_dir() if exists else False
        except (OSError, TypeError, ValueError):
            exists = False
            is_directory = False
        return {"exists": exists, "is_directory": is_directory}

    @staticmethod
    def _vosk_model_path_required_response():
        return "Не удалось сохранить путь к модели Vosk: путь не указан."

    @staticmethod
    def _vosk_model_path_change_reminder():
        return (
            "Распознавание речи не запускается автоматически. "
            "Выполните команду 'статус vosk', чтобы проверить готовность."
        )

    @staticmethod
    def _vosk_model_path_configured_response(model_path, preflight):
        path_status = CommandProcessor._safe_model_path_filesystem_status(model_path)
        if path_status["exists"] and path_status["is_directory"]:
            result = "Путь к модели Vosk сохранен. Папка найдена."
        elif path_status["exists"] and not path_status["is_directory"]:
            result = "Путь к модели Vosk сохранен, но указанный путь не является папкой."
        else:
            result = (
                "Путь к модели Vosk сохранен, но папка пока не найдена. "
                "Проверьте, что модель скачана и распакована."
            )
        return f"{result}\n{CommandProcessor._vosk_model_path_change_reminder()}"

    @staticmethod
    def _vosk_model_path_cleared_response(preflight):
        return (
            "Путь к модели Vosk очищен.\n"
            f"{CommandProcessor._vosk_model_path_change_reminder()}"
        )

    @staticmethod
    def _extract_prefixed_value(command_text, normalized_command, prefixes):
        for prefix in prefixes:
            if normalized_command == prefix:
                return ""
            if normalized_command.startswith(prefix + " "):
                original = str(command_text).strip()
                return original[len(prefix) :].strip()
        return None

    def _result(
        self,
        intent,
        response,
        should_exit=False,
        speakable=None,
        allow_manual_dialogue=True,
    ):
        original_response = response
        result = {
            "intent": intent,
            "response": response,
            "should_exit": should_exit,
        }
        if speakable is None:
            speakable = self._is_result_speakable(intent)
        if speakable:
            self.assistant_response_history.add_response(
                response,
                source_command=getattr(self, "_current_source_command", None),
                speakable=True,
                source="command_processor",
            )
        if (
            allow_manual_dialogue
            and self.voice_dialogue_mode_manager.should_speak_response(
                original_response,
                source_command=getattr(self, "_current_source_command", None),
                speakable=speakable,
            )
        ):
            result["response"] = self._append_manual_voice_dialogue_note(
                original_response
            )
        return result

    def _default_system_status(self):
        return {
            "version": "0.2",
            "state": "running",
            "services": [
                "logger",
                "event_bus",
                "module_manager",
                "command_processor",
                "action_router",
                "idea_manager",
                "memory_manager",
                "microphone_input_adapter",
                "voice_input_manager",
            ],
        }

    def _microphone_result(self, intent, manager_method_name):
        if self.voice_input_manager is None:
            return self._result(
                intent,
                self.dialogue_manager.microphone_unavailable_response(),
            )

        manager_method = getattr(self.voice_input_manager, manager_method_name)
        manager_result = manager_method()
        return self._result(intent, manager_result["message"])

    def _microphone_mode_status_result(self):
        mode = self.microphone_listening_mode_manager.get_mode()
        return self._result(
            "microphone.mode.status",
            self._microphone_mode_status_response(mode),
        )

    def _set_microphone_mode_result(self, intent, mode):
        if mode == "off":
            self.microphone_listening_mode_manager.switch_to_off()
            response = "Микрофон выключен."
        elif mode == "partial":
            self.microphone_listening_mode_manager.switch_to_partial()
            response = (
                "Включено частичное прослушивание. "
                "Реальный захват микрофона пока не запускается автоматически."
            )
        elif mode == "continuous":
            self.microphone_listening_mode_manager.switch_to_continuous()
            response = (
                "Режим постоянного прослушивания включен как безопасное "
                "состояние. Реальный микрофон пока не запускается автоматически."
            )
        else:
            raise ValueError(f"Unsupported microphone mode command target: {mode}")

        return self._result(intent, response)

    @staticmethod
    def _microphone_mode_status_response(mode):
        responses = {
            "off": "Микрофон выключен.",
            "partial": (
                "Включено частичное прослушивание. JARVIS готов принять одну "
                "голосовую команду после явного запуска."
            ),
            "continuous": (
                "Включен режим постоянного прослушивания. Реальный захват "
                "микрофона пока не активирован в целях безопасности."
            ),
        }
        return responses[mode]

    def _is_voice_simulation_command(self, command):
        return any(
            command == prefix or command.startswith(prefix + " ")
            for prefix in self.VOICE_SIMULATION_PREFIXES
        )

    def _extract_typed_voice_recognition_simulation_text(
        self,
        command_text,
        normalized_command,
    ):
        for prefix in self.TYPED_VOICE_RECOGNITION_SIMULATION_PREFIXES:
            marker = prefix + ":"
            if normalized_command == marker:
                return ""
            if normalized_command.startswith(marker):
                original = str(command_text or "").strip()
                return original[len(marker) :].strip()
        return None

    def _extract_voice_output_text(self, command_text, normalized_command):
        for prefix in self.VOICE_OUTPUT_SAY_PREFIXES:
            if normalized_command == prefix:
                return ""
            if normalized_command.startswith(prefix):
                original = str(command_text or "").strip()
                return original[len(prefix) :].strip()
        return None

    def _voice_output_speak_result(self, text):
        speak_result = self.voice_output_manager.speak(text, source="command")
        return self._result(
            speak_result["intent"],
            speak_result["message"],
            speakable=False,
        )

    def _voice_output_test_result(self):
        if not self.voice_output_manager.is_enabled():
            speak_result = self.voice_output_manager.speak(
                "Исмаил, голосовой ответ JARVIS готов к тестированию.",
                source="test",
            )
            return self._result(
                speak_result["intent"],
                speak_result["message"],
                speakable=False,
            )

        speak_result = self.voice_output_manager.test_voice()
        intent = (
            speak_result["intent"]
            if not speak_result.get("backend_called", False)
            else "voice.output.test"
        )
        return self._result(intent, speak_result["message"], speakable=False)

    def _voice_output_local_test_result(self):
        speak_result = self.voice_output_manager.test_local_voice()
        return self._result(
            speak_result["intent"],
            speak_result["message"],
            speakable=False,
        )

    def _last_assistant_response_result(self):
        text = self.voice_interaction_controls.get_last_assistant_response()
        if text is None:
            return self._result(
                "assistant.last_response.empty",
                "В этой сессии ещё нет ответа JARVIS для повторения.",
                speakable=False,
            )
        return self._result(
            "assistant.last_response",
            f"Последний ответ JARVIS:\n{text}",
            speakable=False,
        )

    def _speak_last_assistant_response_result(self):
        text = self.voice_interaction_controls.get_last_assistant_response()
        if text is None:
            return self._result(
                "assistant.speak_last_response.empty",
                "В этой сессии ещё нет ответа JARVIS для повторения.",
                speakable=False,
            )

        speak_result = self.voice_output_manager.speak(
            text,
            source="repeat_last_response",
        )
        mode = speak_result["mode"]
        if speak_result["intent"] in {"voice.output.muted", "voice.output.skipped"}:
            response = speak_result["message"]
            intent = (
                "assistant.speak_last_response.muted"
                if speak_result["intent"] == "voice.output.muted"
                else "assistant.speak_last_response.skipped"
            )
        elif mode == self.voice_output_manager.OFF:
            response = (
                "Последний ответ JARVIS:\n"
                f"{text}\n\n"
                "Голосовой ответ отключён. Включите тестовый режим командой: "
                "включить тестовый голос или локальный голос командой: "
                "включить локальный голос."
            )
            intent = "assistant.speak_last_response.disabled"
        elif mode == self.voice_output_manager.DRY_RUN:
            response = (
                "Озвучиваю последний ответ JARVIS:\n"
                f"[TTS dry-run] {speak_result['spoken_text']}\n"
                "Безопасность: реальный звук не воспроизводился, облако не "
                "использовалось, аудиофайл не сохранялся."
            )
            intent = "assistant.speak_last_response.dry_run"
        elif speak_result["success"]:
            response = (
                "Последний ответ JARVIS озвучен локально.\n"
                "Безопасность: облако не использовалось, аудиофайл не сохранялся."
            )
            intent = "assistant.speak_last_response.windows_local"
        else:
            safe_error = str(speak_result.get("error") or "неизвестная ошибка").strip()
            response = (
                "Не удалось озвучить последний ответ локально.\n"
                f"Причина: {safe_error}.\n"
                "Можно переключиться в тестовый режим: включить тестовый голос."
            )
            intent = "assistant.speak_last_response.failed"

        return self._result(intent, response, speakable=False)

    def _repeat_last_voice_command_result(self):
        summary = self.voice_interaction_controls.get_last_voice_recognition_summary()
        if summary is None:
            return self._result(
                "voice.history.repeat.empty",
                "В этой сессии ещё нет распознанной голосовой команды.",
                speakable=False,
            )

        recognized_text = summary.recognized_text or "пусто / речь не распознана"
        speak_result = self.voice_output_manager.speak(
            recognized_text,
            source="repeat_last_voice_command",
        )
        if speak_result["intent"] in {"voice.output.muted", "voice.output.skipped"}:
            response = (
                f"{speak_result['message']}\n"
                f"Последняя распознанная голосовая команда: {recognized_text}\n"
                "Команда не выполнялась повторно."
            )
            intent = (
                "voice.history.repeat.muted"
                if speak_result["intent"] == "voice.output.muted"
                else "voice.history.repeat.skipped"
            )
        elif speak_result["mode"] == self.voice_output_manager.OFF:
            response = (
                f"Последняя распознанная голосовая команда: {recognized_text}\n"
                "Команда не выполнялась повторно.\n\n"
                "Голосовой ответ отключён. Включите тестовый режим командой: "
                "включить тестовый голос или локальный голос командой: "
                "включить локальный голос."
            )
            intent = "voice.history.repeat.disabled"
        elif speak_result["mode"] == self.voice_output_manager.DRY_RUN:
            response = (
                "Озвучиваю последнюю распознанную голосовую команду:\n"
                f"[TTS dry-run] {speak_result['spoken_text']}\n"
                "Команда не выполнялась повторно.\n"
                "Безопасность: реальный звук не воспроизводился, облако не использовалось, аудиофайл не сохранялся."
            )
            intent = "voice.history.repeat.dry_run"
        elif speak_result.get("success"):
            response = (
                "Последняя распознанная голосовая команда озвучена локально.\n"
                "Команда не выполнялась повторно.\n"
                "Безопасность: облако не использовалось, аудиофайл не сохранялся."
            )
            intent = "voice.history.repeat.windows_local"
        else:
            safe_error = str(speak_result.get("error") or "неизвестная ошибка").strip()
            response = (
                "Не удалось озвучить последнюю распознанную голосовую команду локально.\n"
                f"Причина: {safe_error}.\n"
                "Команда не выполнялась повторно."
            )
            intent = "voice.history.repeat.failed"

        return self._result(intent, response, speakable=False)

    def _short_last_assistant_response_result(self):
        text = self.voice_interaction_controls.get_short_last_assistant_response(
            max_chars=180
        )
        if text is None:
            return self._result(
                "assistant.clarify.empty",
                "Пока нет последнего ответа, который можно упростить.",
                speakable=False,
            )
        return self._result(
            "assistant.clarify.short",
            (
                "Коротко:\n"
                f"{text}\n\n"
                "Примечание: это безопасное локальное сокращение без AI-переформулирования."
            ),
            speakable=False,
        )

    def _simple_last_assistant_response_result(self):
        text = self.voice_interaction_controls.get_simple_last_assistant_response(
            max_chars=220
        )
        if text is None:
            return self._result(
                "assistant.clarify.empty",
                "Пока нет последнего ответа, который можно упростить.",
                speakable=False,
            )
        return self._result(
            "assistant.clarify.simple",
            (
                "Проще:\n"
                f"{text}\n\n"
                "Примечание: это безопасное локальное сокращение без AI-переформулирования."
            ),
            speakable=False,
        )

    def _assistant_response_history_result(self):
        entries = self.assistant_response_history.list_recent(limit=5)
        if not entries:
            response = "История ответов JARVIS за текущую сессию пуста."
        else:
            lines = ["История ответов JARVIS за текущую сессию:"]
            for index, entry in enumerate(entries, start=1):
                lines.append(f"{index}. {self._short_response_text(entry.text)}")
            response = "\n".join(lines)
        return self._result(
            "assistant.response_history.list",
            response,
            speakable=False,
        )

    def _assistant_response_history_count_result(self):
        count = self.assistant_response_history.count()
        return self._result(
            "assistant.response_history.count",
            f"В этой сессии записано ответов JARVIS: {count}.",
            speakable=False,
        )

    def _enable_voice_dialogue_result(self):
        if not self.voice_output_manager.is_enabled():
            return self._result(
                "voice.dialogue.enable_failed.voice_output_off",
                (
                    "Сначала включите голосовой ответ: включить тестовый голос или включить локальный голос.\n"
                    "Голосовой диалог не включён."
                ),
                speakable=False,
            )

        self.voice_dialogue_mode_manager.enable_manual()
        if self.voice_output_manager.mode == self.voice_output_manager.WINDOWS_LOCAL:
            mode_line = "Текущие подходящие ответы будут озвучиваться локальным голосом Windows."
        else:
            mode_line = "Текущие подходящие ответы будут озвучиваться в тестовом режиме."
        return self._result(
            "voice.dialogue.manual.enabled",
            (
                "Ручной голосовой диалог включён.\n"
                "Режим: MANUAL.\n"
                f"{mode_line}\n"
                "Безопасность: постоянное прослушивание не включено, облако не используется, аудиофайлы не сохраняются."
            ),
            speakable=False,
        )

    def _voice_output_safety_status_response(self):
        safety_status = self.voice_output_manager.safety_controller.status()
        dialogue_mode = self.voice_dialogue_mode_manager.mode
        voice_mode = self.voice_output_manager.mode
        if safety_status.muted:
            return (
                "Голосовая безопасность:\n"
                "Тихий режим: включён.\n"
                "Голосовая озвучка заблокирована до команды: снова говори.\n"
                f"Пропуск следующей озвучки: {'да' if safety_status.skip_next else 'нет'}.\n"
                f"Голосовой диалог: {dialogue_mode}.\n"
                f"Голосовой ответ: {voice_mode}."
            )
        return (
            "Голосовая безопасность:\n"
            "Тихий режим: выключен.\n"
            f"Пропуск следующей озвучки: {'да' if safety_status.skip_next else 'нет'}.\n"
            f"Голосовой диалог: {dialogue_mode}.\n"
            f"Голосовой ответ: {voice_mode}."
        )

    def _voice_dialogue_status_response(self):
        if self.voice_dialogue_mode_manager.is_manual_enabled():
            return (
                "Голосовой диалог включён в ручном режиме.\n"
                "Режим: MANUAL.\n"
                "JARVIS озвучивает только подходящие текущие ответы и только через включённый голосовой режим."
            )
        return (
            "Голосовой диалог отключён.\n"
            "Режим: OFF.\n"
            "JARVIS не озвучивает текущие ответы автоматически.\n"
            "Можно включить ручной режим командой: включить голосовой диалог."
        )

    def _append_manual_voice_dialogue_note(self, response):
        speak_result = self.voice_output_manager.speak(
            response,
            source="voice_dialogue_manual_mode",
        )
        if speak_result["intent"] in {"voice.output.muted", "voice.output.skipped"}:
            note = (
                "Голосовой диалог: текущий ответ не озвучен.\n"
                f"Причина: {speak_result['message']}"
            )
        elif speak_result["mode"] == self.voice_output_manager.DRY_RUN:
            note = (
                "Голосовой диалог:\n"
                f"[TTS dry-run] {speak_result['spoken_text']}\n"
                "Безопасность: реальный звук не воспроизводился, облако не использовалось, аудиофайл не сохранялся."
            )
        elif speak_result.get("success"):
            note = (
                "Голосовой диалог: текущий ответ озвучен локально.\n"
                "Безопасность: облако не использовалось, аудиофайл не сохранялся."
            )
        else:
            safe_error = str(
                speak_result.get("error")
                or speak_result.get("message")
                or "неизвестная ошибка"
            ).strip()
            note = (
                "Голосовой диалог: не удалось озвучить текущий ответ локально.\n"
                f"Причина: {safe_error}.\n"
                "JARVIS продолжает работу."
            )
        return f"{response}\n\n{note}"

    @staticmethod
    def _short_response_text(text, max_length=120):
        normalized = " ".join(str(text or "").split())
        if len(normalized) <= max_length:
            return normalized
        return normalized[: max_length - 3].rstrip() + "..."

    @staticmethod
    def _is_result_speakable(intent):
        if not intent:
            return False
        non_speakable_prefixes = (
            "voice.",
            "speech.backend.",
            "microphone.",
            "assistant.last_response",
            "assistant.speak_last_response",
            "assistant.response_history",
            "assistant.clarify",
        )
        return not str(intent).startswith(non_speakable_prefixes)

    def _process_voice_simulation(self, command):
        recognized_text = self._extract_prefixed_text(
            command,
            self.VOICE_SIMULATION_PREFIXES,
        )

        if self.voice_input_manager is None:
            return self._result(
                "voice.empty",
                self.dialogue_manager.voice_empty_input_response(),
            )

        result = self.voice_input_manager.process_recognized_text(recognized_text)
        result = dict(result)
        if result["intent"] not in {
            "voice.empty",
            "voice.confirmation_required",
            "voice.forbidden",
        }:
            result["intent"] = "voice.command.simulated"

        return result

    def _is_idea_add_command(self, command):
        return any(
            command == prefix or command.startswith(prefix + " ")
            for prefix in self.IDEA_ADD_PREFIXES
        )

    def _get_vosk_runtime_loader(self):
        if self.vosk_runtime_loader is None:
            from voice.vosk_runtime_loader import VoskRuntimeLoader

            self.vosk_runtime_loader = VoskRuntimeLoader()
        return self.vosk_runtime_loader

    def _add_idea(self, command):
        title = self._extract_idea_title(command)
        idea = self.idea_manager.add_idea(title)
        return self._result(
            "idea.add",
            self.dialogue_manager.idea_saved_response(idea["title"]),
        )

    def _extract_idea_title(self, command):
        for prefix in self.IDEA_ADD_PREFIXES:
            if command == prefix:
                return ""
            if command.startswith(prefix + " "):
                return command[len(prefix) :].strip()

        return command

    def _list_ideas(self):
        ideas = self.idea_manager.list_ideas()
        if not ideas:
            response = self.dialogue_manager.no_ideas_response()
        else:
            response = self.dialogue_manager.ideas_list_response(ideas)

        return self._result("idea.list", response)

    def _count_ideas(self):
        count = self.idea_manager.count_ideas()
        return self._result(
            "idea.count",
            f"{self.dialogue_manager.get_preferred_name()}, сохранено идей: {count}.",
        )

    def _is_memory_add_command(self, command):
        return any(
            command == prefix or command.startswith(prefix + " ")
            for prefix in self.MEMORY_ADD_PREFIXES
        )

    def _add_memory(self, command):
        content = self._extract_prefixed_text(command, self.MEMORY_ADD_PREFIXES)
        memory = self.memory_manager.add_memory(content)
        return self._result(
            "memory.add",
            self.dialogue_manager.memory_saved_response(memory["content"]),
        )

    def _list_memories(self):
        memories = self.memory_manager.list_memories()
        if not memories:
            response = "В локальной памяти пока нет сохранённых записей."
        else:
            response = self.dialogue_manager.memory_list_response(memories)

        return self._result("memory.list", response)

    def _count_memories(self):
        count = self.memory_manager.count_memories()
        return self._result(
            "memory.count",
            self.dialogue_manager.memory_count_response(count),
        )

    def _recent_memories(self):
        memories = self.memory_manager.get_recent_memories(limit=5)
        return self._result(
            "memory.recent",
            self.dialogue_manager.recent_memory_response(memories),
        )

    def _about_user_memories(self):
        memories = self.memory_manager.list_memories()
        return self._result(
            "memory.about_user",
            self.dialogue_manager.about_user_response(memories),
        )

    def _is_memory_search_command(self, command):
        return any(
            command == prefix or command.startswith(prefix + " ")
            for prefix in self.MEMORY_SEARCH_PREFIXES
        )

    def _search_memories(self, command):
        query = self._extract_prefixed_text(command, self.MEMORY_SEARCH_PREFIXES)
        memories = self.memory_manager.search_memories(query)
        return self._result(
            "memory.search",
            self.dialogue_manager.memory_recall_response(memories, query),
        )

    def _extract_prefixed_text(self, command, prefixes):
        for prefix in prefixes:
            if command == prefix:
                return ""
            if command.startswith(prefix + " "):
                return command[len(prefix) :].strip()

        return command

    def _greeting_response(self):
        return (
            f"{self.dialogue_manager.get_preferred_name()}, привет. "
            f"{self.dialogue_manager.get_assistant_name()} работает и готов помочь."
        )

    def _assistant_name_response(self):
        return (
            f"{self.dialogue_manager.get_preferred_name()}, меня зовут "
            f"{self.dialogue_manager.get_assistant_name()}."
        )

    def _change_assistant_name(self, assistant_name):
        try:
            assistant_name = UserProfileManager.validate_assistant_name(assistant_name)
        except ValueError:
            return self._result(
                "assistant.name.invalid",
                self._invalid_assistant_name_response(),
            )

        self._save_assistant_name(assistant_name)
        return self._result(
            "assistant.name.changed",
            (
                f"{self.dialogue_manager.get_preferred_name()}, имя ассистента изменено. "
                f"Теперь меня зовут {assistant_name}."
            ),
        )

    def _reset_assistant_name(self):
        assistant_name = UserProfileManager.DEFAULT_ASSISTANT_NAME
        self._save_assistant_name(assistant_name)
        return self._result(
            "assistant.name.reset",
            (
                f"{self.dialogue_manager.get_preferred_name()}, имя ассистента сброшено. "
                f"Теперь меня зовут {assistant_name}."
            ),
        )

    def _save_assistant_name(self, assistant_name):
        self.user_profile["assistant_name"] = assistant_name
        self.dialogue_manager.user_profile["assistant_name"] = assistant_name
        if self.voice_input_manager is not None:
            self.voice_input_manager.user_profile["assistant_name"] = assistant_name

        if self.user_profile_manager is not None:
            self.user_profile_manager.set_assistant_name(assistant_name)
        elif self._profile_looks_persisted():
            UserProfileManager().save_profile(self.user_profile)

    def _profile_looks_persisted(self):
        return bool(self.user_profile.get("created_at") or self.user_profile.get("updated_at"))

    def _extract_assistant_name(self, command_text, normalized_command):
        return self._extract_prefixed_value(
            command_text,
            normalized_command,
            self.ASSISTANT_NAME_CHANGE_PREFIXES,
        )

    def _invalid_assistant_name_response(self):
        return (
            f"{self.dialogue_manager.get_preferred_name()}, имя ассистента не изменено. "
            "Укажите короткое имя без переносов строк и специальных управляющих символов."
        )

    def _help_response(self):
        return (
            f"{self.dialogue_manager.get_preferred_name()}, сейчас я умею работать с профилем, "
            "показывать статус системы, вести локальную память и идеи, выполнять безопасную "
            "маршрутизацию действий и обнаружение рискованных команд; "
            "имя ассистента можно посмотреть, изменить или сбросить; "
            "режимы микрофона; настройка, статус и путь модели Vosk; пробный запуск Vosk на тестовых данных; "
            "реальное one-shot распознавание Vosk по явной команде; симуляция голосовой команды. "
            "Для проверки голосового pipeline без микрофона используйте: симулируй распознавание: <текст>. "
            "Реальный захват микрофона автоматически не включается. "
            "Голосовой ответ доступен явно и безопасно: статус голосового ответа; диагностика локального голоса; "
            "включить тестовый голос; включить локальный голос; выключить голос; скажи: <текст>; произнеси: <текст>; "
            "озвучь: <текст>; тест голоса; тест локального голоса. "
            "Управление безопасностью озвучки: замолчи; снова говори; не озвучивай следующий ответ; статус голосовой безопасности. "
            "Последний ответ за текущую сессию можно посмотреть или озвучить явно: последний ответ; "
            "что ты сказал; повтори текстом; повтори; озвучь последний ответ; повтори голосом; "
            "объясни короче; скажи проще; история ответов; статус голосового диалога. "
            "Ручной голосовой диалог можно включить только после голосового ответа: включить голосовой диалог; выключить голосовой диалог; статус голосового диалога. "
            "Для ручного режима сначала включите тестовый или локальный голос; постоянное прослушивание не включается. "
            "Команды стоп/тихий режим не включают постоянное прослушивание. В тестовом режиме звук не воспроизводится; в локальном режиме используется Windows TTS. Облако не используется, аудиофайлы не сохраняются. "
            "Некоторые заранее известные read-only голосовые команды могут выполняться без подтверждения; список: безопасные голосовые команды. "
            "Неизвестные и рискованные голосовые команды всё ещё требуют подтверждения да / нет; "
            "ожидающую голосовую команду можно проверить или отменить. "
            "Можно посмотреть последнее голосовое распознавание, что я сказал, последнюю голосовую команду, историю голосовых команд за сессию, количество событий и очистить историю голоса. "
            "Команда повтори последнюю голосовую команду может озвучить распознанный текст, но не выполняет команду повторно. "
            "Можно добавить исправление распознавания: я сказал не X, а Y; исправления действуют только в текущей сессии, их можно посмотреть или очистить. "
            "Рискованные действия не обходят безопасность, постоянное прослушивание не связано "
            "с реальным распознаванием. "
            "Зрение экрана и автоматизация запланированы позже. "
            "Для выхода напишите: выход."
        )

    def _route_result(self, route):
        intent_by_category = {
            "confirmation_required": "action.confirmation_required",
            "forbidden": "action.forbidden",
            "safe_action": "action.safe_action",
            "informational": "action.informational",
            "idea": "unknown",
            "empty": "empty",
        }
        return {
            "intent": intent_by_category.get(route["category"], "unknown"),
            "response": route["response"],
            "should_exit": False,
            "category": route["category"],
            "risk_level": route["risk_level"],
            "allowed": route["allowed"],
            "requires_confirmation": route["requires_confirmation"],
            "reason": route["reason"],
        }
