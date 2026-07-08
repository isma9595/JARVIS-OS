from core.action_router import SafeActionRouter
from dialogue import DialogueManager


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
    }
    EXIT_COMMANDS = {
        "выход",
        "стоп",
        "остановись",
        "завершить",
        "закрыть",
    }

    def __init__(self, user_profile=None, dialogue_manager=None):
        self.user_profile = user_profile or {}
        self.dialogue_manager = dialogue_manager or DialogueManager(self.user_profile)
        self.action_router = SafeActionRouter(
            user_profile=self.user_profile,
            dialogue_manager=self.dialogue_manager,
        )

    def process(self, command_text):
        command = self._normalize(command_text)

        if not command:
            return self._result(
                "empty",
                self.dialogue_manager.empty_command_response(),
            )

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

        if command in self.CAPABILITIES_COMMANDS:
            return self._result(
                "assistant.capabilities",
                self.dialogue_manager.capabilities_response(),
            )

        if command in self.EXIT_COMMANDS:
            return self._result(
                "system.exit",
                self.dialogue_manager.exit_response(),
                should_exit=True,
            )

        route = self.action_router.route(command)
        return self._route_result(route)

    def _normalize(self, command_text):
        if command_text is None:
            return ""

        return str(command_text).strip().lower()

    def _result(self, intent, response, should_exit=False):
        return {
            "intent": intent,
            "response": response,
            "should_exit": should_exit,
        }

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
