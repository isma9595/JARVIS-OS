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
    VOICE_SIMULATION_PREFIXES = (
        "голосовая команда",
        "голосом",
        "как голос",
        "распознанный текст",
    )
    VOICE_CONFIRMATION_COMMANDS = {
        "подтвердить голосовую команду",
        "подтверждаю голосовую команду",
        "голос подтверждаю",
        "подтвердить голосом",
    }
    VOICE_CANCELLATION_COMMANDS = {
        "отменить голосовую команду",
        "отмени голосовую команду",
        "голос отмена",
        "отменить голосом",
    }
    COMMANDS_LIST_COMMANDS = {
        "покажи команды",
        "список команд",
        "какие команды есть",
        "все команды",
    }
    EXIT_COMMANDS = {
        "выход",
        "стоп",
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

    def set_voice_input_manager(self, voice_input_manager):
        self.voice_input_manager = voice_input_manager

    def process(self, command_text):
        command = self._normalize(command_text)

        if not command:
            return self._result(
                "empty",
                self.dialogue_manager.empty_command_response(),
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

        return str(command_text).strip().lower()

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
                "voice_input_manager",
            ],
        }

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
