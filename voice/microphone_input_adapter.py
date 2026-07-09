from voice.speech_recognition_backend import NoSpeechRecognitionBackend
from voice.vosk_local_backend import VoskLocalBackend


class MicrophoneInputAdapter:
    DISABLED = "disabled"
    PERMISSION_REQUIRED = "permission_required"
    READY = "ready"
    LISTENING = "listening"
    UNAVAILABLE = "unavailable"
    STOPPED = "stopped"

    STATES = {
        DISABLED,
        PERMISSION_REQUIRED,
        READY,
        LISTENING,
        UNAVAILABLE,
        STOPPED,
    }

    def __init__(self, backend_name="none", speech_backend=None):
        self.state = self.DISABLED
        self.permission_granted = False
        self.speech_backend = speech_backend or self._create_speech_backend(backend_name)
        self.backend_name = self.speech_backend.get_name()
        self.last_error = None

    def get_state(self):
        return self.state

    def get_status(self):
        return {
            "state": self.state,
            "permission_granted": self.permission_granted,
            "backend_name": self.backend_name,
            "last_error": self.last_error,
            "backend_available": self.has_backend(),
        }

    def has_backend(self):
        return self.speech_backend.is_available()

    def get_speech_backend(self):
        return self.speech_backend

    def get_speech_backend_name(self):
        return self.speech_backend.get_name()

    def speech_backend_status(self):
        return self.speech_backend.get_status()

    def set_speech_backend(self, backend):
        if isinstance(backend, str):
            backend = self._create_speech_backend(backend)
        self.speech_backend = backend or NoSpeechRecognitionBackend()
        self.backend_name = self.speech_backend.get_name()
        return self.speech_backend_status()

    def select_speech_backend(self, backend_name):
        return self.set_speech_backend(backend_name)

    @staticmethod
    def _create_speech_backend(backend_name):
        normalized_name = str(backend_name or "none").strip().lower()
        if normalized_name in {"vosk", "vosk_local"}:
            return VoskLocalBackend()
        if normalized_name == "none":
            return NoSpeechRecognitionBackend()
        raise ValueError(f"Unknown speech recognition backend: {backend_name}")

    def request_permission(self):
        self.last_error = None
        if self.permission_granted:
            self.state = self.READY
        else:
            self.state = self.PERMISSION_REQUIRED

        return self.get_status()

    def grant_permission(self):
        self.permission_granted = True
        self.last_error = None
        self.state = self.READY
        return self.get_status()

    def revoke_permission(self):
        self.permission_granted = False
        self.last_error = None
        self.state = self.DISABLED
        return self.get_status()

    def enable(self):
        if not self.permission_granted:
            return self.request_permission()

        self.last_error = None
        self.state = self.READY
        return self.get_status()

    def disable(self):
        self.last_error = None
        self.state = self.DISABLED
        return self.get_status()

    def start_listening(self):
        if not self.permission_granted:
            self.last_error = "microphone permission is required"
            self.state = self.PERMISSION_REQUIRED
            return self.get_status()

        if not self.has_backend():
            self.last_error = "speech recognition backend is not connected"
            self.state = self.UNAVAILABLE
            return self.get_status()

        self.last_error = None
        self.state = self.LISTENING
        return self.get_status()

    def stop_listening(self):
        self.last_error = None
        if self.state == self.DISABLED:
            return self.get_status()

        if self.permission_granted:
            self.state = self.READY
        else:
            self.state = self.STOPPED

        return self.get_status()

    def read_text(self):
        result = dict(self.listen_once())
        result.update(
            {
                "state": self.state,
                "permission_granted": self.permission_granted,
                "backend_name": self.backend_name,
                "last_error": self.last_error,
            }
        )
        return result

    def listen_once(self):
        result = self.speech_backend.recognize_once()
        if not self.speech_backend.is_available():
            self.last_error = "speech recognition backend is not connected"
            self.state = self.UNAVAILABLE
        return result
