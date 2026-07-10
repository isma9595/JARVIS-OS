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
        return not self.installed

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
                "vosk_package_available": preflight["vosk_package_available"],
                "model_path_configured": preflight["model_path_configured"],
                "backend_ready_for_real_recognition": preflight[
                    "backend_ready_for_real_recognition"
                ],
                "real_recognition_enabled": False,
                "microphone_enabled": False,
                "missing_requirements": preflight["missing_requirements"],
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
        return list(self.preflight_check()["missing_requirements"])

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
        backend_ready = not missing_requirements

        return {
            "vosk_package_available": dependency_available,
            "dependency_available": dependency_available,
            "model_path_configured": model_path_configured,
            "model_path_exists": model_path_exists,
            "backend_ready_for_real_recognition": backend_ready,
            "ready": backend_ready,
            "real_recognition_enabled": False,
            "microphone_enabled": False,
            "safe_bootstrap_only": True,
            "missing_requirements": missing_requirements,
            "recognition_disabled_reason": (
                "real_recognition_not_enabled_for_task_023"
                if backend_ready
                else "missing_safe_requirements"
            ),
        }

    def get_preflight_summary(self):
        status = self.preflight_check()
        if status["backend_ready_for_real_recognition"]:
            return (
                "Vosk prerequisites are ready. Speech recognition and microphone "
                "access remain disabled."
            )
        return "Missing Vosk prerequisites: " + ", ".join(
            status["missing_requirements"]
        )

    def get_readiness_report(self):
        """Return a side-effect-free readiness report for local Vosk setup."""
        preflight = self.preflight_check()
        return {
            "backend": self.backend_name,
            "language": self.language,
            "model_path": self.model_path,
            "vosk_package_available": preflight["vosk_package_available"],
            "model_path_configured": preflight["model_path_configured"],
            "model_path_exists": preflight["model_path_exists"],
            "backend_ready_for_real_recognition": preflight[
                "backend_ready_for_real_recognition"
            ],
            "real_recognition_enabled": False,
            "microphone_enabled": False,
            "requires_permission": self.requires_permission(),
            "requires_installation": self.requires_installation(),
            "supports_offline": self.supports_offline(),
            "supports_streaming": self.supports_streaming(),
            "missing_requirements": preflight["missing_requirements"],
            "safe_bootstrap_only": True,
            "message": self.get_preflight_summary(),
        }

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
