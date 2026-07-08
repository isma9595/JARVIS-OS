from core.command_processor import CommandProcessor
from dialogue import DialogueManager


class VoiceInputManager:
    DISABLED = "disabled"
    READY = "ready"
    LISTENING = "listening"
    STOPPED = "stopped"
    VOICE_PREFIXES = (
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

    def __init__(self, command_processor=None, dialogue_manager=None, user_profile=None):
        self.user_profile = user_profile or {}
        self.dialogue_manager = dialogue_manager or DialogueManager(self.user_profile)
        self.command_processor = command_processor or CommandProcessor(
            user_profile=self.user_profile,
            dialogue_manager=self.dialogue_manager,
        )
        self.state = self.DISABLED
        self._pending_confirmation = None

    def get_state(self):
        return self.state

    def enable(self):
        self.state = self.READY
        return {
            "state": self.state,
            "message": self.dialogue_manager.voice_enabled_response(),
        }

    def disable(self):
        self.state = self.DISABLED
        return {
            "state": self.state,
            "message": self.dialogue_manager.voice_disabled_response(),
        }

    def start_listening(self):
        if self.state == self.DISABLED:
            return {
                "state": self.state,
                "message": self.dialogue_manager.voice_disabled_response(),
            }

        if self.state == self.READY:
            self.state = self.LISTENING
            return {
                "state": self.state,
                "message": self.dialogue_manager.voice_listening_started_response(),
            }

        return {
            "state": self.state,
            "message": self.dialogue_manager.voice_not_real_microphone_response(),
        }

    def stop_listening(self):
        if self.state == self.LISTENING:
            self.state = self.READY
            return {
                "state": self.state,
                "message": self.dialogue_manager.voice_listening_stopped_response(),
            }

        return {
            "state": self.state,
            "message": self.dialogue_manager.voice_listening_stopped_response(),
        }

    def normalize_voice_text(self, text):
        if text is None:
            return ""

        return " ".join(str(text).strip().lower().split())

    def extract_voice_command(self, text):
        normalized_text = self.normalize_voice_text(text)
        for prefix in self.VOICE_PREFIXES:
            if normalized_text == prefix:
                return ""
            if normalized_text.startswith(prefix + " "):
                return normalized_text[len(prefix) :].strip()

        return normalized_text

    def is_voice_alias(self, text):
        normalized_text = self.normalize_voice_text(text)
        return any(
            normalized_text == prefix or normalized_text.startswith(prefix + " ")
            for prefix in self.VOICE_PREFIXES
        )

    def is_voice_confirmation(self, text):
        return self.normalize_voice_text(text) in self.VOICE_CONFIRMATION_COMMANDS

    def is_voice_cancel(self, text):
        return self.normalize_voice_text(text) in self.VOICE_CANCELLATION_COMMANDS

    def process_recognized_text(self, text):
        recognized_text = self.normalize_voice_text(text)
        command_text = self.extract_voice_command(recognized_text)
        if not command_text:
            return {
                "intent": "voice.empty",
                "response": self.dialogue_manager.voice_empty_input_response(),
                "should_exit": False,
                "channel": "voice",
                "source": "recognized_text",
            }

        if self.is_voice_confirmation(command_text):
            return self.confirm_pending_action()

        if self.is_voice_cancel(command_text):
            return self.cancel_pending_action()

        result = self.command_processor.process(command_text)
        category = result.get("category")

        if category == "confirmation_required" or result.get("requires_confirmation"):
            self._pending_confirmation = {
                "text": command_text,
                "channel": "voice",
                "risk": "confirmation_required",
            }
            return {
                "intent": "voice.confirmation_required",
                "response": self.dialogue_manager.voice_confirmation_required_response(
                    command_text
                ),
                "should_exit": False,
                "channel": "voice",
                "source": "recognized_text",
                "pending_confirmation": self.get_pending_confirmation(),
            }

        if category == "forbidden" or (
            result.get("allowed") is False and result.get("risk_level") == "high"
        ):
            self.clear_pending_confirmation()
            return {
                "intent": "voice.forbidden",
                "response": self.dialogue_manager.voice_forbidden_response(
                    command_text
                ),
                "should_exit": False,
                "channel": "voice",
                "source": "recognized_text",
            }

        result = dict(result)
        result["channel"] = "voice"
        result["source"] = "recognized_text"
        result["response"] = (
            self.dialogue_manager.voice_command_received_response(command_text)
            + "\n"
            + result["response"]
        )
        return result

    def has_pending_confirmation(self):
        return self._pending_confirmation is not None

    def get_pending_confirmation(self):
        if self._pending_confirmation is None:
            return None

        return dict(self._pending_confirmation)

    def clear_pending_confirmation(self):
        self._pending_confirmation = None

    def confirm_pending_action(self):
        pending = self.get_pending_confirmation()
        if pending is None:
            return {
                "intent": "voice.confirmation.none",
                "response": self.dialogue_manager.voice_confirmation_none_response(),
                "should_exit": False,
                "channel": "voice",
                "source": "confirmation_simulation",
            }

        self.clear_pending_confirmation()
        return {
            "intent": "voice.confirmation.confirmed",
            "response": self.dialogue_manager.voice_confirmation_confirmed_response(
                pending["text"]
            ),
            "should_exit": False,
            "channel": "voice",
            "source": "confirmation_simulation",
        }

    def cancel_pending_action(self):
        pending = self.get_pending_confirmation()
        if pending is None:
            return {
                "intent": "voice.confirmation.none",
                "response": self.dialogue_manager.voice_cancellation_none_response(),
                "should_exit": False,
                "channel": "voice",
                "source": "confirmation_simulation",
            }

        self.clear_pending_confirmation()
        return {
            "intent": "voice.confirmation.cancelled",
            "response": self.dialogue_manager.voice_confirmation_cancelled_response(
                pending["text"]
            ),
            "should_exit": False,
            "channel": "voice",
            "source": "confirmation_simulation",
        }

    def is_enabled(self):
        return self.state != self.DISABLED
