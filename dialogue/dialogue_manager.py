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

    def no_memory_response(self):
        return f"{self.get_preferred_name()}, пока в локальной памяти ничего нет."

    def memory_search_response(self, memories, query):
        if not memories:
            return f"{self.get_preferred_name()}, я не нашёл в памяти ничего по запросу: {query}."

        lines = [
            f"{self.get_preferred_name()}, я нашёл в памяти:",
        ]
        for index, memory in enumerate(memories, start=1):
            lines.append(f"{index}. {memory.get('content', '')}")

        return "\n".join(lines)

    def memory_delete_requires_future_confirmation_response(self):
        return (
            f"{self.get_preferred_name()}, удаление памяти требует отдельной "
            "подтверждаемой функции в будущем. В TASK-009 я не удаляю память."
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
        return (
            "Сейчас я умею запускать ядро, показывать профиль пользователя, "
            "вести естественный диалог и понимать простые текстовые команды. "
            "Голос, зрение экрана и автоматизация будут добавлены позже."
        )

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
