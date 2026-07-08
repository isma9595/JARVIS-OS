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
