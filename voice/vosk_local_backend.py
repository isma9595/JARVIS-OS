import importlib.util
from pathlib import Path

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
        """Store a local model path in memory; do not create or modify files."""
        if model_path is None:
            self.model_path = None
        else:
            normalized_path = str(model_path).strip()
            self.model_path = normalized_path or None
        self.model_available = self.check_model_path_exists()
        return self.preflight_check()

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
