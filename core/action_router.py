from dialogue import DialogueManager


class SafeActionRouter:
    INFORMATIONAL_PHRASES = {
        "кто я",
        "как тебя зовут",
        "покажи профиль",
        "что ты умеешь",
        "помощь",
    }
    SAFE_ACTION_PHRASES = {
        "покажи список команд",
        "объясни что ты умеешь",
        "подготовь черновик",
        "составь текст",
        "помоги написать письмо",
    }
    CONFIRMATION_PHRASES = {
        "отправь письмо",
        "удали файл",
        "загрузи документ",
        "опубликуй объявление",
        "измени настройки",
        "заполни форму и отправь",
        "подпиши документ",
        "создай файл",
        "открой приложение",
        "открой браузер",
        "скачай файл",
    }
    FORBIDDEN_PHRASES = {
        "удали system32",
        "отключи защиту",
        "взломай",
        "укради данные",
        "обойди пароль",
        "форматируй диск",
        "удали все файлы",
        "отключи антивирус",
        "получи чужой доступ",
    }

    def __init__(self, user_profile=None, dialogue_manager=None):
        self.user_profile = user_profile or {}
        self.dialogue_manager = dialogue_manager or DialogueManager(self.user_profile)

    def route(self, command_text, intent=None):
        command = self._normalize(command_text)

        if not command:
            return self._decision(
                category="empty",
                risk_level="low",
                allowed=False,
                requires_confirmation=False,
                reason="empty command",
                response=self.dialogue_manager.empty_command_response(),
            )

        if self._contains_any(command, self.FORBIDDEN_PHRASES):
            return self._decision(
                category="forbidden",
                risk_level="high",
                allowed=False,
                requires_confirmation=False,
                reason="dangerous or disallowed action",
                response=self.dialogue_manager.forbidden_action_response(command),
            )

        if self._contains_any(command, self.CONFIRMATION_PHRASES):
            return self._decision(
                category="confirmation_required",
                risk_level="medium",
                allowed=True,
                requires_confirmation=True,
                reason="action requires explicit user confirmation",
                response=self.dialogue_manager.action_requires_confirmation_response(
                    command
                ),
            )

        if command in self.INFORMATIONAL_PHRASES:
            return self._decision(
                category="informational",
                risk_level="low",
                allowed=True,
                requires_confirmation=False,
                reason="informational command",
                response=self.dialogue_manager.safe_action_response(command),
            )

        if self._contains_any(command, self.SAFE_ACTION_PHRASES):
            return self._decision(
                category="safe_action",
                risk_level="low",
                allowed=True,
                requires_confirmation=False,
                reason="safe non-executing action",
                response=self.dialogue_manager.safe_action_response(command),
            )

        return self._decision(
            category="idea",
            risk_level="unknown",
            allowed=False,
            requires_confirmation=False,
            reason="unsupported command can be saved as a future idea",
            response=self.dialogue_manager.future_idea_response(command),
        )

    def _normalize(self, command_text):
        if command_text is None:
            return ""

        return str(command_text).strip().lower()

    def _contains_any(self, command, phrases):
        return any(phrase in command for phrase in phrases)

    def _decision(
        self,
        category,
        risk_level,
        allowed,
        requires_confirmation,
        reason,
        response,
    ):
        return {
            "category": category,
            "risk_level": risk_level,
            "allowed": allowed,
            "requires_confirmation": requires_confirmation,
            "reason": reason,
            "response": response,
        }
