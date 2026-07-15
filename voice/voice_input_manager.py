from core.command_processor import CommandProcessor
from dialogue import DialogueManager
from voice.microphone_input_adapter import MicrophoneInputAdapter
from voice.vosk_local_backend import VoskLocalBackend


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

    def __init__(
        self,
        command_processor=None,
        dialogue_manager=None,
        user_profile=None,
        microphone_adapter=None,
        vosk_settings_manager=None,
    ):
        self.user_profile = user_profile or {}
        self.dialogue_manager = dialogue_manager or DialogueManager(self.user_profile)
        self.command_processor = command_processor or CommandProcessor(
            user_profile=self.user_profile,
            dialogue_manager=self.dialogue_manager,
        )
        self.microphone_adapter = microphone_adapter or MicrophoneInputAdapter()
        current_backend = self.microphone_adapter.get_speech_backend()
        self._vosk_backend = (
            current_backend
            if isinstance(current_backend, VoskLocalBackend)
            else VoskLocalBackend(settings_manager=vosk_settings_manager)
        )
        self.state = self.DISABLED
        self._pending_confirmation = None

    def get_state(self):
        return self.state

    def get_microphone_status(self):
        return self.microphone_adapter.get_status()

    def get_speech_backend_status(self):
        return self.microphone_adapter.speech_backend_status()

    def get_speech_backend_name(self):
        return self.microphone_adapter.get_speech_backend_name()

    def set_speech_backend(self, backend):
        return self.microphone_adapter.set_speech_backend(backend)

    def select_speech_backend(self, backend_name):
        return self.microphone_adapter.select_speech_backend(backend_name)

    def use_vosk_backend(self):
        return self.set_speech_backend(self._vosk_backend)

    def get_vosk_backend_status(self):
        if self.get_speech_backend_name() == "vosk_local":
            return self.get_speech_backend_status()
        return self._vosk_backend.get_status()

    def get_vosk_preflight(self):
        return self._vosk_backend.preflight_check()

    def configure_vosk_model_path(self, model_path):
        return self._vosk_backend.configure_model_path(model_path)

    def clear_vosk_model_path(self):
        return self._vosk_backend.clear_model_path()

    def configure_vosk_language(self, language):
        return self._vosk_backend.configure_language(language)

    def microphone_status(self):
        status = self.get_microphone_status()
        return {
            "state": self.state,
            "microphone": status,
            "message": self.dialogue_manager.microphone_status_response(status),
        }

    def request_microphone_permission(self):
        status = self.microphone_adapter.request_permission()
        return {
            "state": self.state,
            "microphone": status,
            "message": self.dialogue_manager.microphone_permission_required_response(),
        }

    def grant_microphone_permission(self):
        status = self.microphone_adapter.grant_permission()
        self.state = self.READY
        return {
            "state": self.state,
            "microphone": status,
            "message": self.dialogue_manager.microphone_permission_granted_response(),
        }

    def revoke_microphone_permission(self):
        status = self.microphone_adapter.revoke_permission()
        self.state = self.DISABLED
        return {
            "state": self.state,
            "microphone": status,
            "message": self.dialogue_manager.microphone_permission_revoked_response(),
        }

    def start_microphone_input(self):
        status = self.microphone_adapter.start_listening()
        if status["state"] == MicrophoneInputAdapter.PERMISSION_REQUIRED:
            self.state = self.DISABLED
            return {
                "state": self.state,
                "microphone": status,
                "message": self.dialogue_manager.microphone_permission_required_response(),
            }

        if status["state"] == MicrophoneInputAdapter.UNAVAILABLE:
            self.state = self.READY if status["permission_granted"] else self.DISABLED
            return {
                "state": self.state,
                "microphone": status,
                "message": self.dialogue_manager.microphone_unavailable_response(),
            }

        self.state = self.LISTENING
        return {
            "state": self.state,
            "microphone": status,
            "message": self.dialogue_manager.microphone_listening_started_response(),
        }

    def stop_microphone_input(self):
        microphone_state = self.microphone_adapter.get_state()
        if microphone_state == MicrophoneInputAdapter.UNAVAILABLE:
            status = self.microphone_adapter.stop_listening()
            self.state = self.READY if status["permission_granted"] else self.DISABLED
            return {
                "state": self.state,
                "microphone": status,
                "message": self.dialogue_manager.microphone_listening_stopped_response(),
            }

        if microphone_state != MicrophoneInputAdapter.LISTENING:
            return {
                "state": self.state,
                "microphone": self.get_microphone_status(),
                "message": self.dialogue_manager.microphone_not_listening_response(),
            }

        status = self.microphone_adapter.stop_listening()
        self.state = self.READY if status["permission_granted"] else self.DISABLED
        return {
            "state": self.state,
            "microphone": status,
            "message": self.dialogue_manager.microphone_listening_stopped_response(),
        }

    def listen_once_from_microphone(self):
        if self.get_speech_backend_name() == "vosk_local":
            read_result = self.microphone_adapter.read_text()
            self.state = self.STOPPED
            return {
                "state": self.state,
                "microphone": self.get_microphone_status(),
                "text": read_result["text"],
                "message": self.dialogue_manager.vosk_skeleton_unavailable_response(),
            }

        if not self.microphone_adapter.permission_granted:
            status = self.microphone_adapter.request_permission()
            self.state = self.DISABLED
            return {
                "state": self.state,
                "microphone": status,
                "text": None,
                "message": self.dialogue_manager.microphone_permission_required_response(),
            }

        read_result = self.microphone_adapter.read_text()
        self.state = self.STOPPED
        return {
            "state": self.state,
            "microphone": self.get_microphone_status(),
            "text": read_result["text"],
            "message": self.dialogue_manager.microphone_unavailable_response(),
        }

    def enable(self):
        self.microphone_adapter.request_permission()
        self.microphone_adapter.grant_permission()
        self.state = self.READY
        return {
            "state": self.state,
            "microphone": self.get_microphone_status(),
            "message": self.dialogue_manager.voice_enabled_response(),
        }

    def disable(self):
        self.microphone_adapter.disable()
        self.state = self.DISABLED
        return {
            "state": self.state,
            "microphone": self.get_microphone_status(),
            "message": self.dialogue_manager.voice_disabled_response(),
        }

    def start_listening(self):
        if self.state == self.DISABLED:
            return {
                "state": self.state,
                "message": self.dialogue_manager.voice_disabled_response(),
            }

        if self.state == self.READY:
            status = self.microphone_adapter.start_listening()
            if status["state"] == MicrophoneInputAdapter.UNAVAILABLE:
                return {
                    "state": self.state,
                    "microphone": status,
                    "message": self.dialogue_manager.microphone_unavailable_response(),
                }

            self.state = self.LISTENING
            return {
                "state": self.state,
                "microphone": status,
                "message": self.dialogue_manager.voice_listening_started_response(),
            }

        return {
            "state": self.state,
            "message": self.dialogue_manager.voice_not_real_microphone_response(),
        }

    def stop_listening(self):
        if self.state == self.LISTENING:
            self.microphone_adapter.stop_listening()
            self.state = self.READY
            return {
                "state": self.state,
                "microphone": self.get_microphone_status(),
                "message": self.dialogue_manager.voice_listening_stopped_response(),
            }

        return {
            "state": self.state,
            "microphone": self.get_microphone_status(),
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

        previous_suppression = getattr(
            self.command_processor,
            "_suppress_conversational_fallback",
            False,
        )
        self.command_processor._suppress_conversational_fallback = True
        try:
            result = self.command_processor.process(command_text)
        finally:
            self.command_processor._suppress_conversational_fallback = previous_suppression
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
