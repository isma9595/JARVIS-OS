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

    def acknowledgement(self, task_description):
        return f"Понял, {self.get_preferred_name()}. Подготовлю: {task_description}."

    def error_message(self, message):
        return f"{self.get_preferred_name()}, возникла ошибка: {message}."

    def _get_value(self, key):
        return self.user_profile.get(key) or self.DEFAULT_PROFILE[key]
