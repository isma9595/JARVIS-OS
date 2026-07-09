class SpeechRecognitionBackend:
    def get_name(self):
        return "base"

    def is_available(self):
        return False

    def requires_permission(self):
        return False

    def requires_installation(self):
        return False

    def get_status(self):
        return {
            "name": self.get_name(),
            "available": self.is_available(),
            "requires_permission": self.requires_permission(),
            "requires_installation": self.requires_installation(),
            "supports_streaming": self.supports_streaming(),
            "supports_offline": self.supports_offline(),
            "description": self.get_description(),
        }

    def recognize_once(self):
        return {
            "intent": "speech.backend.not_implemented",
            "text": None,
            "status": self.get_status(),
        }

    def supports_streaming(self):
        return False

    def supports_offline(self):
        return False

    def get_description(self):
        return "Base speech recognition backend interface; recognition is not implemented."


class NoSpeechRecognitionBackend(SpeechRecognitionBackend):
    def get_name(self):
        return "none"

    def recognize_once(self):
        return {
            "intent": "speech.backend.unavailable",
            "text": None,
            "status": self.get_status(),
        }

    def get_description(self):
        return (
            "Speech recognition is unavailable. This backend does not record audio "
            "or access a microphone."
        )
