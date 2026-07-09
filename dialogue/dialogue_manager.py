class DialogueManager:
    DEFAULT_PROFILE = {
        "user_name": "Пользователь",
        "preferred_name": "Пользователь",
        "assistant_name": "JARVIS",
        "language": "ru",
        "communication_style": "естественный, понятный, не робот",
    }

    def __init__(self, user_profile=None):
        self.user_profile = {
            **self.DEFAULT_PROFILE,
            **(user_profile or {}),
        }

    def get_user_name(self):
        return self._get_value("user_name")

    def get_preferred_name(self):
        return self._get_value("preferred_name")

    def get_assistant_name(self):
        return self._get_value("assistant_name")

    def get_language(self):
        return self._get_value("language")

    def get_communication_style(self):
        return self._get_value("communication_style")

    def greeting(self):
        return f"Добро пожаловать, {self.get_preferred_name()}."

    def startup_complete(self):
        return "Система успешно запущена."

    def shutdown_message(self):
        return "Система остановлена."

    def already_stopped_message(self):
        return "Ядро уже остановлено."

    def confirmation_request(self, action_description):
        return (
            f"{self.get_preferred_name()}, я могу выполнить действие: "
            f"{action_description}. Подтвердить?"
        )

    def action_requires_confirmation_response(self, action_description):
        return (
            f"{self.get_preferred_name()}, это действие требует подтверждения: "
            f"{action_description}. Я не буду выполнять его без вашего разрешения."
        )

    def forbidden_action_response(self, action_description):
        return (
            f"{self.get_preferred_name()}, я не могу выполнить это действие, "
            "потому что оно может быть опасным."
        )

    def future_idea_response(self, action_description):
        return (
            f"{self.get_preferred_name()}, я пока не умею выполнять эту команду, "
            "но могу сохранить её как идею для будущего."
        )

    def idea_saved_response(self, idea_title):
        return f"{self.get_preferred_name()}, я сохранил идею: {idea_title}."

    def ideas_list_response(self, ideas):
        lines = [
            f"{self.get_preferred_name()}, вот сохранённые идеи:",
        ]
        for index, idea in enumerate(ideas, start=1):
            lines.append(f"{index}. {idea.get('title', '')}")

        return "\n".join(lines)

    def no_ideas_response(self):
        return f"{self.get_preferred_name()}, пока нет сохранённых идей."

    def memory_saved_response(self, memory_content):
        return f"{self.get_preferred_name()}, я запомнил: {memory_content}."

    def memory_list_response(self, memories):
        if not memories:
            return self.no_memory_response()

        lines = [
            f"{self.get_preferred_name()}, вот что я помню:",
        ]
        for index, memory in enumerate(memories, start=1):
            lines.append(f"{index}. {memory.get('content', '')}")

        return "\n".join(lines)

    def memory_count_response(self, count):
        return (
            f"{self.get_preferred_name()}, в локальной памяти "
            f"сохранено записей: {count}."
        )

    def recent_memory_response(self, memories):
        if not memories:
            return self.no_memory_response()

        lines = [
            f"{self.get_preferred_name()}, вот последние записи памяти:",
        ]
        for index, memory in enumerate(memories, start=1):
            lines.append(f"{index}. {memory.get('content', '')}")

        return "\n".join(lines)

    def about_user_response(self, memories):
        if not memories:
            return self.no_memory_response()

        lines = [
            f"{self.get_preferred_name()}, вот что я знаю из локальной памяти:",
        ]
        for index, memory in enumerate(memories, start=1):
            lines.append(f"{index}. {memory.get('content', '')}")

        return "\n".join(lines)

    def memory_recall_response(self, memories, query):
        if not memories:
            return self.memory_not_found_response(query)

        lines = [
            f"{self.get_preferred_name()}, я нашёл в памяти:",
        ]
        for index, memory in enumerate(memories, start=1):
            lines.append(f"{index}. {memory.get('content', '')}")

        return "\n".join(lines)

    def memory_not_found_response(self, query):
        return (
            f"{self.get_preferred_name()}, я не нашёл в памяти "
            f"записей по запросу: {query}."
        )

    def no_memory_response(self):
        return f"{self.get_preferred_name()}, пока в локальной памяти ничего нет."

    def memory_search_response(self, memories, query):
        return self.memory_recall_response(memories, query)

    def memory_delete_requires_future_confirmation_response(self):
        return (
            f"{self.get_preferred_name()}, удаление памяти требует отдельной "
            "подтверждаемой функции в будущем. В этой версии я не удаляю память."
        )

    def safe_action_response(self, action_description):
        return (
            f"{self.get_preferred_name()}, это безопасная команда: "
            f"{action_description}. На этом этапе я только определяю действие "
            "и не выполняю его."
        )

    def acknowledgement(self, task_description):
        return f"Понял, {self.get_preferred_name()}. Подготовлю: {task_description}."

    def error_message(self, message):
        return f"{self.get_preferred_name()}, возникла ошибка: {message}."

    def identity_response(self):
        preferred_name = self.get_preferred_name()
        return (
            f"{preferred_name}, вы сохранены в профиле как "
            f"{preferred_name}."
        )

    def assistant_identity_response(self):
        return (
            f"Меня зовут {self.get_assistant_name()}. "
            "Я ваш персональный ассистент."
        )

    def unknown_command_response(self):
        return (
            f"{self.get_preferred_name()}, я пока не умею выполнять "
            "эту команду, но могу запомнить её как идею для будущего."
        )

    def empty_command_response(self):
        return (
            f"{self.get_preferred_name()}, я не услышал команду. "
            "Повторите, пожалуйста."
        )

    def exit_response(self):
        return f"Хорошо, {self.get_preferred_name()}. Завершаю работу."

    def capabilities_response(self):
        return self.help_response()

    def version_response(self, version):
        return (
            f"{self.get_preferred_name()}, текущая версия JARVIS OS: "
            f"v{version}."
        )

    def system_status_response(self, status):
        services = status.get("services") or []
        state = status.get("state") or "unknown"
        state_text = "работает" if state == "running" else state
        return (
            f"{self.get_preferred_name()}, система {state_text}. "
            f"Версия: v{status.get('version')}. "
            f"Активных сервисов: {len(services)}."
        )

    def services_response(self, services):
        lines = [
            f"{self.get_preferred_name()}, активные системные сервисы:",
        ]
        for index, service_name in enumerate(services, start=1):
            lines.append(f"{index}. {service_name}")

        return "\n".join(lines)

    def commands_response(self):
        return "\n".join(
            [
                f"{self.get_preferred_name()}, сейчас доступны такие команды:",
                "",
                "Профиль:",
                "- кто я",
                "- покажи профиль",
                "",
                "Память:",
                "- запомни что ...",
                "- что ты помнишь",
                "- вспомни про ...",
                "",
                "Идеи:",
                "- добавь идею ...",
                "- покажи идеи",
                "",
                "Система:",
                "- статус системы",
                "- покажи версию",
                "- покажи сервисы",
                "- голос",
                "- включи голос",
                "- отключи голос",
                "- покажи команды",
                "",
                "Безопасность:",
                "- команды с риском требуют подтверждения",
                "- опасные действия блокируются",
                "",
                "Выход:",
                "- выход",
            ]
        )

    def help_response(self):
        return (
            f"{self.get_preferred_name()}, сейчас я умею работать с профилем, "
            "сохранять идеи, запоминать факты, искать по памяти, показывать "
            "статус системы и различать риск действий. Голос, зрение экрана "
            "и автоматизация будут добавлены позже. Для выхода напишите: выход."
        )

    def voice_disabled_response(self):
        return (
            f"{self.get_preferred_name()}, голосовой ввод отключён. "
            "Я не слушаю микрофон."
        )

    def voice_enabled_response(self):
        return (
            f"{self.get_preferred_name()}, голосовой ввод подготовлен, "
            "но реальный микрофон пока не включается. "
            "Это будет добавлено безопасно позже."
        )

    def voice_listening_started_response(self):
        return (
            f"{self.get_preferred_name()}, голосовой ввод переведён в режим ожидания. "
            "Микрофон в этой версии не включается."
        )

    def voice_listening_stopped_response(self):
        return (
            f"{self.get_preferred_name()}, режим ожидания голосового ввода остановлен. "
            "Микрофон не использовался."
        )

    def voice_empty_input_response(self):
        return (
            f"{self.get_preferred_name()}, я не получил распознанный текст "
            "для голосовой команды."
        )

    def voice_command_received_response(self, text):
        return (
            f"{self.get_preferred_name()}, я принял голосовую команду: "
            f"{text}."
        )

    def voice_confirmation_required_response(self, text):
        return (
            f"{self.get_preferred_name()}, эта голосовая команда требует "
            f"подтверждения: {text}."
        )

    def voice_confirmation_confirmed_response(self, text):
        return (
            f"{self.get_preferred_name()}, подтверждение принято. "
            "Реальное выполнение действий будет добавлено позже безопасно."
        )

    def voice_confirmation_cancelled_response(self, text):
        return f"{self.get_preferred_name()}, голосовое действие отменено."

    def voice_confirmation_none_response(self):
        return (
            f"{self.get_preferred_name()}, сейчас нет голосового действия "
            "для подтверждения."
        )

    def voice_cancellation_none_response(self):
        return (
            f"{self.get_preferred_name()}, сейчас нет голосового действия "
            "для отмены."
        )

    def voice_forbidden_response(self, text):
        return (
            f"{self.get_preferred_name()}, я не могу выполнить эту "
            "голосовую команду, потому что она может быть опасной."
        )

    def voice_not_real_microphone_response(self):
        return (
            f"{self.get_preferred_name()}, голосовой фундамент есть, "
            "но микрофон пока не включается. "
            "Голосовые команды будут добавлены безопасно позже."
        )

    def microphone_status_response(self, status):
        state = status.get("state", "unknown")
        backend_name = status.get("backend_name", "none")
        permission_text = (
            "разрешен"
            if status.get("permission_granted")
            else "не разрешен"
        )
        return (
            f"{self.get_preferred_name()}, статус микрофона: {state}. "
            f"Доступ: {permission_text}. Backend: {backend_name}."
        )

    def speech_backend_status_response(self, status):
        name = status.get("name", "none")
        availability = "доступен" if status.get("available") else "недоступен"
        mode = "офлайн" if status.get("supports_offline") else "без распознавания"
        return (
            f"{self.get_preferred_name()}, речевой backend: {name}; "
            f"статус: {availability}; режим: {mode}. "
            "Проверка статуса не включает микрофон и не записывает звук."
        )

    def speech_backend_explain_response(self):
        return (
            f"{self.get_preferred_name()}, сейчас выбран безопасный backend без "
            "распознавания речи. Микрофон не включается, звук не записывается. "
            "Локальный backend можно будет подключить отдельно после установки "
            "и явного разрешения."
        )

    def speech_backend_options_response(self):
        return (
            f"{self.get_preferred_name()}, кандидаты для локального распознавания: "
            "Vosk, Whisper и адаптер Windows Speech Recognition. Рекомендуемый "
            "первый прототип — Vosk за единым безопасным интерфейсом; зависимости "
            "и доступ к микрофону должны подключаться отдельно и явно."
        )

    def speech_backend_selected_response(self, status):
        name = status.get("name", "none")
        return (
            f"{self.get_preferred_name()}, выбран речевой backend: {name}. "
            "Это безопасный skeleton: распознавание речи не запущено, "
            "микрофон не включается и звук не записывается."
        )

    def speech_backend_selection_unavailable_response(self):
        return (
            f"{self.get_preferred_name()}, выбрать речевой backend сейчас нельзя: "
            "voice input manager не подключён."
        )

    def vosk_backend_plan_response(self):
        return (
            f"{self.get_preferred_name()}, для подключения Vosk нужны локальная "
            "библиотека, совместимая модель и отдельный безопасный аудио-адаптер. "
            "Сейчас доступен только skeleton: микрофон не включается, звук не "
            "записывается и данные не отправляются в интернет."
        )

    def vosk_installation_guide_response(self, summary):
        python_status = summary["python"]
        pip_info = summary["pip"]
        model = summary["model"]
        return (
            f"{self.get_preferred_name()}, Vosk автоматически не устанавливается. "
            f"{python_status['message']} "
            f"Команда для ручной установки: {pip_info['command']} "
            f"(pip {pip_info['minimum_pip_version']} или новее). "
            f"Первая русская small-модель: {model['name']}. "
            "Это только текстовая инструкция: команды не запускаются, модель "
            "не скачивается, микрофон не включается."
        )

    def vosk_python_compatibility_response(self, status):
        compatibility = (
            "версия выглядит совместимой"
            if status["is_likely_compatible"]
            else "совместимость не гарантируется"
        )
        return (
            f"{self.get_preferred_name()}, текущий Python: "
            f"{status['python_version']}; официальный диапазон инструкции Vosk: "
            f"{status['official_supported_range']}; {compatibility}. "
            "Проверка информационная. Рекомендуется отдельный совместимый venv."
        )

    def vosk_model_download_guidance_response(self, model, guidance):
        return (
            f"{self.get_preferred_name()}, рекомендуемая первая русская модель: "
            f"{model['name']} ({model['size']}). Откройте официальный каталог "
            "Vosk вручную, проверьте источник, скачайте и распакуйте архив в "
            "отдельную локальную папку, затем укажите путь в настройках. "
            f"{guidance['message']} Микрофон не включается."
        )

    def vosk_safe_enablement_response(self, steps):
        lines = [
            f"{self.get_preferred_name()}, безопасный план подключения Vosk:",
        ]
        lines.extend(
            f"{index}. {step}" for index, step in enumerate(steps, start=1)
        )
        lines.append(
            "Сейчас это только план: установка, загрузка модели, runtime и "
            "микрофон не запускаются."
        )
        return "\n".join(lines)

    def vosk_runtime_risks_response(self, risks):
        lines = [
            f"{self.get_preferred_name()}, риски подключения Vosk:",
        ]
        lines.extend(
            f"{index}. {risk}" for index, risk in enumerate(risks, start=1)
        )
        lines.append(
            "Это информационная оценка: установка, runtime и микрофон не запускаются."
        )
        return "\n".join(lines)

    def vosk_skeleton_unavailable_response(self):
        return (
            f"{self.get_preferred_name()}, Vosk skeleton готов, но библиотека и "
            "модель ещё не подключены. Микрофон не включён, звук не записывается."
        )

    def vosk_preflight_response(self, preflight):
        if preflight.get("ready"):
            state = "зависимость и папка модели найдены"
        else:
            state = "не хватает: " + ", ".join(
                preflight.get("missing_requirements", [])
            )
        return (
            f"{self.get_preferred_name()}, preflight Vosk: {state}. "
            "Это только проверка готовности: распознавание не запускается, "
            "микрофон не включается и звук не записывается."
        )

    def vosk_missing_requirements_response(self, missing_requirements):
        if missing_requirements:
            details = ", ".join(missing_requirements)
            return (
                f"{self.get_preferred_name()}, для Vosk не хватает: {details}. "
                "Я ничего не устанавливаю и не скачиваю."
            )
        return (
            f"{self.get_preferred_name()}, обязательные prerequisites Vosk найдены. "
            "Распознавание речи всё равно не запущено."
        )

    def vosk_model_status_response(self, preflight):
        model_path = preflight.get("model_path")
        if not model_path:
            state = "путь к модели не задан"
        elif preflight.get("model_path_exists"):
            state = f"папка модели найдена: {model_path}"
        else:
            state = f"папка модели не найдена: {model_path}"
        return (
            f"{self.get_preferred_name()}, статус модели Vosk: {state}. "
            "Это только проверка; модель не загружается и микрофон не включается."
        )

    def vosk_model_path_required_response(self):
        return (
            f"{self.get_preferred_name()}, после команды нужно указать локальный "
            "путь к папке модели Vosk."
        )

    def vosk_model_path_configured_response(self, model_path, preflight):
        path_state = (
            "папка существует"
            if preflight.get("model_path_exists")
            else "папка не найдена"
        )
        return (
            f"{self.get_preferred_name()}, локальный путь к модели сохранён: "
            f"{model_path}; {path_state}. Файлы модели не изменялись."
        )

    def vosk_model_path_cleared_response(self, preflight):
        return (
            f"{self.get_preferred_name()}, сохранённый путь к модели Vosk очищен. "
            "Файлы и папки модели не удалялись."
        )

    def vosk_settings_response(self, status):
        model_path = status.get("model_path") or "не задан"
        language = status.get("language", "ru")
        return (
            f"{self.get_preferred_name()}, локальные настройки Vosk: "
            f"путь модели — {model_path}; язык — {language}. "
            "Микрофон не запускался."
        )

    def vosk_language_required_response(self):
        return (
            f"{self.get_preferred_name()}, после команды нужно указать язык "
            "модели Vosk."
        )

    def vosk_language_status_response(self, language):
        return (
            f"{self.get_preferred_name()}, сохранённый язык модели Vosk: "
            f"{language}. Микрофон не запускался."
        )

    def vosk_language_configured_response(self, language, status):
        return (
            f"{self.get_preferred_name()}, язык модели Vosk сохранён: {language}. "
            "Распознавание речи и микрофон не запускались."
        )

    def microphone_permission_required_response(self):
        return (
            f"{self.get_preferred_name()}, для микрофона нужно явное разрешение. "
            "Микрофон не включается."
        )

    def microphone_permission_granted_response(self):
        return (
            f"{self.get_preferred_name()}, доступ к микрофону разрешён. "
            "Реальная запись звука не запускается."
        )

    def microphone_permission_revoked_response(self):
        return (
            f"{self.get_preferred_name()}, доступ к микрофону отозван. "
            "Я не слушаю микрофон."
        )

    def microphone_unavailable_response(self):
        return (
            f"{self.get_preferred_name()}, backend распознавания речи ещё не подключён. "
            "Я не включаю микрофон."
        )

    def microphone_listening_started_response(self):
        return (
            f"{self.get_preferred_name()}, режим микрофона включён. "
            "Реальное прослушивание не запускается."
        )

    def microphone_listening_stopped_response(self):
        return f"{self.get_preferred_name()}, микрофон остановлен."

    def microphone_not_listening_response(self):
        return f"{self.get_preferred_name()}, микрофон сейчас не слушает."

    def profile_response(self):
        lines = [
            f"Имя пользователя: {self.get_user_name()}",
            f"Имя ассистента: {self.get_assistant_name()}",
            f"Язык: {self.get_language()}",
            f"Стиль общения: {self.get_communication_style()}",
        ]

        age = self.user_profile.get("age")
        if age:
            lines.append(f"Возраст: {age}")

        main_use_cases = self.user_profile.get("main_use_cases") or []
        if main_use_cases:
            lines.append(
                "Основные сферы использования: "
                + ", ".join(str(item) for item in main_use_cases)
            )

        return "\n".join(lines)

    def _get_value(self, key):
        return self.user_profile.get(key) or self.DEFAULT_PROFILE[key]
