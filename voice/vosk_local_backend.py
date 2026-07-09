from voice.speech_recognition_backend import SpeechRecognitionBackend


class VoskLocalBackend(SpeechRecognitionBackend):
    """Safe placeholder for a future local Vosk integration."""

    backend_name = "vosk_local"

    def __init__(
        self,
        model_path=None,
        language="ru",
        installed=False,
        model_available=False,
    ):
        self.model_path = model_path
        self.language = language
        self.installed = bool(installed)
        self.model_available = bool(model_available)

    def get_name(self):
        return self.backend_name

    def is_available(self):
        # This skeleton deliberately cannot recognize speech.
        return False

    def requires_permission(self):
        return True

    def requires_installation(self):
        return not self.installed

    def supports_offline(self):
        return True

    def get_status(self):
        status = super().get_status()
        status.update(
            {
                "language": self.language,
                "model_path": self.model_path,
                "installed": self.installed,
                "model_available": self.model_available,
                "skeleton": True,
            }
        )
        return status

    def recognize_once(self):
        return {
            "intent": "speech.backend.unavailable",
            "text": None,
            "status": self.get_status(),
            "reason": "Vosk local backend is a skeleton and is not connected.",
        }

    def get_description(self):
        return (
            "Safe Vosk local backend skeleton. Speech recognition, microphone "
            "access, audio recording, model loading, and network access are disabled."
        )
