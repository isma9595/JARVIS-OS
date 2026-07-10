from core.action_router import SafeActionRouter
from dialogue import DialogueManager
from ideas import IdeaManager
from memory import LocalMemoryManager


class CommandProcessor:
    USER_IDENTITY_COMMANDS = {
        "кто я",
        "как меня зовут",
        "мое имя",
        "моё имя",
    }
    ASSISTANT_IDENTITY_COMMANDS = {
        "как тебя зовут",
        "кто ты",
        "твое имя",
        "твоё имя",
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
        "статус vosk",
        "локальный vosk",
        "восок",
        "воск",
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
        "проверить vosk",
        "preflight vosk",
        "проверка vosk",
        "проверь vosk",
        "диагностика vosk",
        "проверить воск",
        "диагностика воск",
        "готов ли vosk",
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
        "модель воск",
        "статус модели воск",
    }
    VOSK_MODEL_PATH_PREFIXES = (
        "путь модели vosk",
        "сохранить путь модели vosk",
        "установить путь модели vosk",
        "модель vosk путь",
        "путь модели воск",
        "укажи путь к модели vosk",
        "установи путь к модели vosk",
    )
    VOSK_MODEL_PATH_CLEAR_COMMANDS = {
        "очистить путь модели vosk",
        "очисти путь модели vosk",
        "сбросить путь модели vosk",
        "удалить путь модели vosk",
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
        "инструкция vosk",
        "инструкция по установке vosk",
        "vosk installation guide",
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
    MEMORY_ADD_PREFIXES = (
        "запомни что",
        "запомни",
        "сохрани в память что",
        "сохрани в память",
        "сохрани это в память что",
        "сохрани это в память",
    )
    MEMORY_LIST_COMMANDS = {
        "что ты помнишь",
        "покажи память",
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
        microphone_listening_mode_manager=None,
    ):
        self.user_profile = user_profile or {}
        self.dialogue_manager = dialogue_manager or DialogueManager(self.user_profile)
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
        self.vosk_runtime_loader = vosk_runtime_loader
        if microphone_listening_mode_manager is None:
            from voice.microphone_listening_modes import (
                MicrophoneListeningModeManager,
            )

            microphone_listening_mode_manager = MicrophoneListeningModeManager()
        self.microphone_listening_mode_manager = microphone_listening_mode_manager

    def set_voice_input_manager(self, voice_input_manager):
        self.voice_input_manager = voice_input_manager

    def process(self, command_text):
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
            status = self._get_vosk_model_status()
            return self._result(
                "speech.backend.vosk.model.status",
                self.dialogue_manager.vosk_model_status_response(status),
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
                self.dialogue_manager.vosk_model_path_cleared_response(preflight),
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
                    self.dialogue_manager.vosk_model_path_required_response(),
                )
            if self.voice_input_manager is None:
                return self._result(
                    "speech.backend.vosk.model_path.unavailable",
                    self.dialogue_manager.speech_backend_selection_unavailable_response(),
                )
            preflight = self.voice_input_manager.configure_vosk_model_path(model_path)
            return self._result(
                "speech.backend.vosk.model.path.set",
                self.dialogue_manager.vosk_model_path_configured_response(
                    model_path, preflight
                ),
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
                return self._result(
                    "voice.confirmation.none",
                    self.dialogue_manager.voice_confirmation_none_response(),
                )

            return self.voice_input_manager.confirm_pending_action()

        if command in self.VOICE_CANCELLATION_COMMANDS:
            if self.voice_input_manager is None:
                return self._result(
                    "voice.confirmation.none",
                    self.dialogue_manager.voice_cancellation_none_response(),
                )

            return self.voice_input_manager.cancel_pending_action()

        if command in self.USER_IDENTITY_COMMANDS:
            return self._result(
                "user.identity",
                self.dialogue_manager.identity_response(),
            )

        if command in self.ASSISTANT_IDENTITY_COMMANDS:
            return self._result(
                "assistant.identity",
                self.dialogue_manager.assistant_identity_response(),
            )

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
                self.dialogue_manager.help_response(),
            )

        if command in self.EXIT_COMMANDS:
            return self._result(
                "system.exit",
                self.dialogue_manager.exit_response(),
                should_exit=True,
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

    def _extract_vosk_model_path(self, command_text, normalized_command):
        return self._extract_prefixed_value(
            command_text, normalized_command, self.VOSK_MODEL_PATH_PREFIXES
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

    def _result(self, intent, response, should_exit=False):
        return {
            "intent": intent,
            "response": response,
            "should_exit": should_exit,
        }

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
            response = self.dialogue_manager.no_memory_response()
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
