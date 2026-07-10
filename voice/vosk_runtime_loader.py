"""Safe, non-loading runtime boundary for a future Vosk integration."""

from voice.vosk_installation_guide import VoskInstallationGuide
from voice.vosk_local_backend import VoskLocalBackend


class VoskRuntimeLoader:
    """Describe runtime readiness without loading code, models, or audio."""

    def __init__(self, backend=None, installation_guide=None):
        self.backend = backend or VoskLocalBackend()
        self.installation_guide = installation_guide or VoskInstallationGuide()

    def can_prepare_runtime(self):
        return bool(
            self.backend.preflight_check().get(
                "backend_ready_for_real_recognition"
            )
        )

    def get_blockers(self):
        blockers = list(
            self.backend.preflight_check().get("missing_requirements", [])
        )
        blockers.append("runtime_loading_not_implemented")
        blockers.append("real_recognition_disabled")
        return blockers

    def get_runtime_status(self):
        preflight = self.backend.preflight_check()
        can_prepare = bool(
            preflight.get("backend_ready_for_real_recognition")
        )
        return {
            "runtime": "vosk",
            "loader_type": "safe_stub",
            "runtime_loaded": False,
            "vosk_package_available": bool(
                preflight.get("vosk_package_available")
            ),
            "dependency_available": bool(
                preflight.get("dependency_available")
            ),
            "model_path_configured": bool(
                preflight.get("model_path_configured")
            ),
            "model_path_exists": bool(preflight.get("model_path_exists")),
            "backend_ready_for_real_recognition": can_prepare,
            "can_prepare_runtime": can_prepare,
            "real_recognition_enabled": False,
            "microphone_enabled": False,
            "missing_requirements": list(
                preflight.get("missing_requirements", [])
            ),
            "recognition_disabled_reason": (
                preflight.get("recognition_disabled_reason")
                or "real_recognition_disabled"
            ),
            "message": (
                "Vosk runtime is not loaded. This safe stub performs readiness "
                "checks only; recognition and microphone access are disabled."
            ),
        }

    def get_safety_summary(self):
        return {
            "loader_type": "safe_stub",
            "runtime_loading_enabled": False,
            "model_loading_enabled": False,
            "real_recognition_enabled": False,
            "microphone_enabled": False,
            "audio_recording_enabled": False,
            "audio_file_access_enabled": False,
            "network_access_enabled": False,
            "environment_changes_enabled": False,
        }

    def get_next_steps(self):
        steps = []
        preflight = self.backend.preflight_check()
        missing = preflight.get("missing_requirements", [])
        if "vosk_dependency" in missing:
            steps.append("Provide the dependency manually in a compatible environment.")
        if "model_path" in missing:
            steps.append("Configure a local model directory.")
        elif "model_directory" in missing:
            steps.append("Correct the configured local model directory.")
        steps.append(
            "Implement and review a separate explicitly authorized runtime loader."
        )
        return steps

    def prepare_runtime_stub(self):
        return {
            "prepared": False,
            "runtime_loaded": False,
            "can_prepare_runtime": self.can_prepare_runtime(),
            "blockers": self.get_blockers(),
            "message": (
                "Preparation checked prerequisites only. Runtime loading is not "
                "implemented and no environment changes were made."
            ),
        }

    def unload_runtime_stub(self):
        return {
            "unloaded": False,
            "runtime_loaded": False,
            "message": "Runtime was not loaded; there is nothing to unload.",
        }

    def is_runtime_loaded(self):
        return False

    def recognize_text_stub(self, *_args, **_kwargs):
        return {
            "recognized": False,
            "text": None,
            "runtime_loaded": False,
            "real_recognition_enabled": False,
            "microphone_enabled": False,
            "reason": "real_recognition_disabled",
            "message": (
                "Recognition is disabled in the safe runtime loader stub."
            ),
        }
