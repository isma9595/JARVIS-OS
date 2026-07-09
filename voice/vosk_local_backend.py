import importlib.util
from pathlib import Path

from voice.speech_recognition_backend import SpeechRecognitionBackend
from voice.vosk_settings_manager import VoskSettingsManager


_UNSET = object()


class VoskLocalBackend(SpeechRecognitionBackend):
    """Safe placeholder for a future local Vosk integration."""

    backend_name = "vosk_local"

    def __init__(
        self,
        model_path=_UNSET,
        language=None,
        installed=False,
        model_available=False,
        settings_manager=None,
    ):
        self.settings_manager = settings_manager or VoskSettingsManager()
        settings = self.settings_manager.load_settings()
        self.model_path = (
            settings.get("model_path") if model_path is _UNSET else model_path
        )
        self.language = language or settings.get("language", "ru")
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
        return not (self.installed or self.check_dependency_available())

    def supports_offline(self):
        return True

    def get_status(self):
        status = super().get_status()
        preflight = self.preflight_check()
        status.update(
            {
                "language": self.language,
                "model_path": self.model_path,
                "installed": preflight["dependency_available"],
                "model_available": preflight["model_path_exists"],
                "skeleton": True,
                "preflight": preflight,
            }
        )
        return status

    def check_dependency_available(self):
        """Check package metadata without importing or executing Vosk."""
        try:
            return importlib.util.find_spec("vosk") is not None
        except (ImportError, AttributeError, ValueError):
            return False

    def check_model_path_configured(self):
        return bool(self.model_path and str(self.model_path).strip())

    def check_model_path_exists(self):
        if not self.check_model_path_configured():
            return False
        try:
            return Path(self.model_path).is_dir()
        except (OSError, TypeError, ValueError):
            return False

    def get_missing_requirements(self):
        missing = []
        if not self.check_dependency_available():
            missing.append("vosk_dependency")
        if not self.check_model_path_configured():
            missing.append("model_path")
        elif not self.check_model_path_exists():
            missing.append("model_directory")
        return missing

    def preflight_check(self):
        dependency_available = self.check_dependency_available()
        model_path_configured = self.check_model_path_configured()
        model_path_exists = self.check_model_path_exists()
        missing_requirements = []
        if not dependency_available:
            missing_requirements.append("vosk_dependency")
        if not model_path_configured:
            missing_requirements.append("model_path")
        elif not model_path_exists:
            missing_requirements.append("model_directory")

        return {
            "dependency_available": dependency_available,
            "model_path_configured": model_path_configured,
            "model_path_exists": model_path_exists,
            "ready": not missing_requirements,
            "missing_requirements": missing_requirements,
        }

    def get_preflight_summary(self):
        status = self.preflight_check()
        if status["ready"]:
            return (
                "Vosk prerequisites are ready. Speech recognition and microphone "
                "access remain disabled."
            )
        return "Missing Vosk prerequisites: " + ", ".join(
            status["missing_requirements"]
        )

    def configure_model_path(self, model_path):
        """Persist a local model path without reading or modifying model files."""
        if model_path is None:
            self.model_path = None
        else:
            normalized_path = str(model_path).strip()
            self.model_path = normalized_path or None
        self.settings_manager.set_model_path(self.model_path)
        self.model_available = self.check_model_path_exists()
        return self.preflight_check()

    def clear_model_path(self):
        self.model_path = None
        self.settings_manager.clear_model_path()
        self.model_available = False
        return self.preflight_check()

    def configure_language(self, language):
        normalized_language = str(language).strip()
        if not normalized_language:
            raise ValueError("Vosk model language must not be empty")
        self.language = normalized_language
        self.settings_manager.set_language(normalized_language)
        return self.get_status()

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
