from core.command_processor import CommandProcessor
from dialogue import DialogueManager


class VoiceInputManager:
    DISABLED = "disabled"
    READY = "ready"
    LISTENING = "listening"
    STOPPED = "stopped"

    def __init__(self, command_processor=None, dialogue_manager=None, user_profile=None):
        self.user_profile = user_profile or {}
        self.dialogue_manager = dialogue_manager or DialogueManager(self.user_profile)
        self.command_processor = command_processor or CommandProcessor(
            user_profile=self.user_profile,
            dialogue_manager=self.dialogue_manager,
        )
        self.state = self.DISABLED

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

    def process_recognized_text(self, text):
        recognized_text = "" if text is None else str(text).strip()
        if not recognized_text:
            return {
                "intent": "voice.empty",
                "response": self.dialogue_manager.voice_empty_input_response(),
                "should_exit": False,
            }

        return self.command_processor.process(recognized_text)

    def is_enabled(self):
        return self.state != self.DISABLED
