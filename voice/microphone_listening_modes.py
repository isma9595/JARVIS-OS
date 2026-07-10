from enum import Enum


class MicrophoneListeningMode(str, Enum):
    OFF = "off"
    PARTIAL = "partial"
    CONTINUOUS = "continuous"


class MicrophoneListeningModeManager:
    def __init__(self, mode=MicrophoneListeningMode.OFF):
        self._mode = self.validate_mode(mode)

    @classmethod
    def allowed_modes(cls):
        return {mode.value for mode in MicrophoneListeningMode}

    @classmethod
    def is_valid_mode(cls, mode):
        try:
            cls.validate_mode(mode)
        except ValueError:
            return False
        return True

    @classmethod
    def validate_mode(cls, mode):
        if isinstance(mode, MicrophoneListeningMode):
            return mode

        normalized_mode = str(mode or "").strip().lower()
        try:
            return MicrophoneListeningMode(normalized_mode)
        except ValueError as exc:
            allowed = ", ".join(sorted(cls.allowed_modes()))
            raise ValueError(
                f"Unknown microphone listening mode: {mode}. "
                f"Allowed modes: {allowed}"
            ) from exc

    def get_mode(self):
        return self._mode.value

    def set_mode(self, mode):
        self._mode = self.validate_mode(mode)
        return self.get_status()

    def switch_to_off(self):
        return self.set_mode(MicrophoneListeningMode.OFF)

    def switch_to_partial(self):
        return self.set_mode(MicrophoneListeningMode.PARTIAL)

    def switch_to_continuous(self):
        return self.set_mode(MicrophoneListeningMode.CONTINUOUS)

    def allows_listening(self):
        return self._mode in {
            MicrophoneListeningMode.PARTIAL,
            MicrophoneListeningMode.CONTINUOUS,
        }

    def allows_limited_listening(self):
        return self._mode == MicrophoneListeningMode.PARTIAL

    def is_continuous(self):
        return self._mode == MicrophoneListeningMode.CONTINUOUS

    def requires_explicit_user_activation(self):
        return self._mode in {
            MicrophoneListeningMode.PARTIAL,
            MicrophoneListeningMode.CONTINUOUS,
        }

    def starts_microphone_capture(self):
        return False

    def get_status(self):
        return {
            "mode": self.get_mode(),
            "allows_listening": self.allows_listening(),
            "limited_listening": self.allows_limited_listening(),
            "continuous": self.is_continuous(),
            "requires_explicit_user_activation": (
                self.requires_explicit_user_activation()
            ),
            "starts_microphone_capture": self.starts_microphone_capture(),
        }
