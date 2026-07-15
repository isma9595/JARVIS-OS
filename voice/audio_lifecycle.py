"""Metadata-only audio lifecycle foundation for JARVIS voice I/O."""

from dataclasses import dataclass
from enum import Enum


class AudioLifecycleState(str, Enum):
    IDLE = "idle"
    READY = "ready"
    CAPTURING_ONCE = "capturing_once"
    SPEAKING = "speaking"
    PAUSED = "paused"
    ERROR = "error"
    UNAVAILABLE = "unavailable"


class AudioCaptureMode(str, Enum):
    OFF = "off"
    ONE_SHOT = "one_shot"
    PARTIAL = "partial"
    CONTINUOUS_DISABLED = "continuous_disabled"


class AudioOutputMode(str, Enum):
    OFF = "off"
    TEST = "test"
    LOCAL_TTS = "local_tts"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class AudioLifecycleStatus:
    lifecycle_enabled: bool
    state: str
    capture_mode: str
    output_mode: str
    microphone_available: bool
    microphone_active: bool
    one_shot_active: bool
    continuous_listening_enabled: bool
    continuous_listening_allowed: bool
    tts_available: bool
    tts_enabled: bool
    speaking_active: bool
    voice_dialogue_active: bool
    pending_voice_command: bool
    safe_to_start_capture: bool
    safe_to_stop_audio: bool
    network_used: bool
    audio_saved: bool
    auto_listening_on_startup: bool
    error: str | None
    notes_ru: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "lifecycle_enabled": self.lifecycle_enabled,
            "state": self.state,
            "capture_mode": self.capture_mode,
            "output_mode": self.output_mode,
            "microphone_available": self.microphone_available,
            "microphone_active": self.microphone_active,
            "one_shot_active": self.one_shot_active,
            "continuous_listening_enabled": self.continuous_listening_enabled,
            "continuous_listening_allowed": self.continuous_listening_allowed,
            "tts_available": self.tts_available,
            "tts_enabled": self.tts_enabled,
            "speaking_active": self.speaking_active,
            "voice_dialogue_active": self.voice_dialogue_active,
            "pending_voice_command": self.pending_voice_command,
            "safe_to_start_capture": self.safe_to_start_capture,
            "safe_to_stop_audio": self.safe_to_stop_audio,
            "network_used": self.network_used,
            "audio_saved": self.audio_saved,
            "auto_listening_on_startup": self.auto_listening_on_startup,
            "error": self.error,
            "notes_ru": self.notes_ru,
        }


@dataclass(frozen=True)
class AudioLifecycleEvent:
    event_type: str
    previous_state: str
    next_state: str
    safe: bool
    message_ru: str
    network_used: bool
    audio_saved: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "event_type": self.event_type,
            "previous_state": self.previous_state,
            "next_state": self.next_state,
            "safe": self.safe,
            "message_ru": self.message_ru,
            "network_used": self.network_used,
            "audio_saved": self.audio_saved,
        }


class AudioLifecycleController:
    """Read and mutate audio lifecycle metadata without touching audio devices."""

    def __init__(
        self,
        voice_input_manager=None,
        voice_output_manager=None,
        microphone_listening_mode_manager=None,
        voice_dialogue_mode_manager=None,
        pending_voice_command_checker=None,
    ):
        self.voice_input_manager = voice_input_manager
        self.voice_output_manager = voice_output_manager
        self.microphone_listening_mode_manager = microphone_listening_mode_manager
        self.voice_dialogue_mode_manager = voice_dialogue_mode_manager
        self.pending_voice_command_checker = pending_voice_command_checker
        self._state = AudioLifecycleState.IDLE
        self._one_shot_active = False
        self._paused = False
        self._error = None

    def status(self) -> AudioLifecycleStatus:
        microphone_status = self._microphone_status()
        microphone_active = microphone_status.get("state") == "listening"
        microphone_available = bool(microphone_status.get("backend_available", False))
        listening_mode = self._listening_mode()
        output_mode, tts_enabled, tts_available = self._output_state()
        voice_dialogue_active = self._voice_dialogue_active()
        pending_voice_command = self._pending_voice_command()
        one_shot_active = self._one_shot_active
        speaking_active = False
        state = self._derive_state(microphone_active, one_shot_active, speaking_active)
        safe_to_start_capture = (
            state in {AudioLifecycleState.IDLE.value, AudioLifecycleState.READY.value}
            and not microphone_active
            and not one_shot_active
            and not speaking_active
        )

        return AudioLifecycleStatus(
            lifecycle_enabled=True,
            state=state,
            capture_mode=self._capture_mode(listening_mode, one_shot_active),
            output_mode=output_mode,
            microphone_available=microphone_available,
            microphone_active=microphone_active,
            one_shot_active=one_shot_active,
            continuous_listening_enabled=False,
            continuous_listening_allowed=False,
            tts_available=tts_available,
            tts_enabled=tts_enabled,
            speaking_active=speaking_active,
            voice_dialogue_active=voice_dialogue_active,
            pending_voice_command=pending_voice_command,
            safe_to_start_capture=safe_to_start_capture,
            safe_to_stop_audio=bool(
                microphone_active or one_shot_active or speaking_active or self._state != AudioLifecycleState.IDLE
            ),
            network_used=False,
            audio_saved=False,
            auto_listening_on_startup=False,
            error=self._error,
            notes_ru=(
                "Audio lifecycle foundation is metadata-only.",
                "Microphone capture is not started by lifecycle status or controls.",
                "TTS playback is not started by lifecycle status or controls.",
                "Continuous listening is disabled and not allowed in this task.",
                "Network is not used; audio is not saved.",
            ),
        )

    def status_text_ru(self) -> str:
        status = self.status()
        yes_no = self._yes_no
        lines = [
            "Audio lifecycle status:",
            f"- audio lifecycle foundation: {'yes' if status.lifecycle_enabled else 'no'}",
            f"- state: {status.state}",
            f"- capture mode: {status.capture_mode}",
            f"- output mode: {status.output_mode}",
            f"- microphone available: {yes_no(status.microphone_available)}",
            f"- microphone active: {yes_no(status.microphone_active)}",
            f"- one-shot active: {yes_no(status.one_shot_active)}",
            f"- continuous listening enabled: {yes_no(status.continuous_listening_enabled)}",
            f"- continuous listening allowed: {yes_no(status.continuous_listening_allowed)}",
            f"- tts available: {yes_no(status.tts_available)}",
            f"- tts enabled: {yes_no(status.tts_enabled)}",
            f"- speaking active: {yes_no(status.speaking_active)}",
            f"- voice dialogue active: {yes_no(status.voice_dialogue_active)}",
            f"- pending voice command: {yes_no(status.pending_voice_command)}",
            f"- safe to start capture: {yes_no(status.safe_to_start_capture)}",
            f"- safe to stop audio: {yes_no(status.safe_to_stop_audio)}",
            f"- network used: {yes_no(status.network_used)}",
            f"- audio saved: {yes_no(status.audio_saved)}",
            f"- auto listening on startup: {yes_no(status.auto_listening_on_startup)}",
            "- no command executed",
        ]
        if status.error:
            lines.append(f"- error: {status.error}")
        lines.extend(f"- note: {note}" for note in status.notes_ru)
        return "\n".join(lines)

    def capabilities_text_ru(self) -> str:
        return "\n".join(
            [
                "Audio lifecycle capabilities:",
                "- can report safe lifecycle state",
                "- can expose status to future Desktop UI",
                "- can describe microphone/TTS state",
                "- can prepare safe start/stop semantics",
                "- does not start microphone",
                "- does not play audio",
                "- does not enable continuous listening",
                "- does not save audio",
                "- no network",
            ]
        )

    def start_one_shot_metadata_only(self) -> AudioLifecycleEvent:
        previous = self.status().state
        self._state = AudioLifecycleState.CAPTURING_ONCE
        self._one_shot_active = True
        self._paused = False
        self._error = None
        return self._event(
            "start_one_shot_metadata_only",
            previous,
            self._state.value,
            "Metadata-only one-shot capture state prepared. Microphone was not opened.",
        )

    def stop_audio_metadata_only(self) -> AudioLifecycleEvent:
        previous = self.status().state
        self._state = AudioLifecycleState.IDLE
        self._one_shot_active = False
        self._paused = False
        self._error = None
        return self._event(
            "stop_audio_metadata_only",
            previous,
            self._state.value,
            "Metadata-only audio stop/reset completed. Microphone and TTS were not called.",
        )

    def pause_output_metadata_only(self) -> AudioLifecycleEvent:
        previous = self.status().state
        self._state = AudioLifecycleState.PAUSED
        self._paused = True
        return self._event(
            "pause_output_metadata_only",
            previous,
            self._state.value,
            "Metadata-only output pause recorded. TTS was not called.",
        )

    def resume_output_metadata_only(self) -> AudioLifecycleEvent:
        previous = self.status().state
        self._state = AudioLifecycleState.IDLE
        self._paused = False
        return self._event(
            "resume_output_metadata_only",
            previous,
            self._state.value,
            "Metadata-only output resume recorded. TTS was not called.",
        )

    def reset_to_idle(self) -> AudioLifecycleEvent:
        previous = self.status().state
        self._state = AudioLifecycleState.IDLE
        self._one_shot_active = False
        self._paused = False
        self._error = None
        return self._event(
            "reset_to_idle",
            previous,
            self._state.value,
            "Audio lifecycle metadata reset to idle. No microphone, TTS, network, or command execution occurred.",
        )

    def _derive_state(self, microphone_active, one_shot_active, speaking_active):
        if self._error:
            return AudioLifecycleState.ERROR.value
        if self._paused:
            return AudioLifecycleState.PAUSED.value
        if one_shot_active:
            return AudioLifecycleState.CAPTURING_ONCE.value
        if speaking_active:
            return AudioLifecycleState.SPEAKING.value
        if microphone_active:
            return AudioLifecycleState.READY.value
        return self._state.value

    def _microphone_status(self):
        if self.voice_input_manager is None:
            return {
                "state": "disabled",
                "permission_granted": False,
                "backend_name": "unknown",
                "last_error": None,
                "backend_available": False,
            }
        try:
            return dict(self.voice_input_manager.get_microphone_status())
        except Exception as exc:
            self._error = str(exc)
            return {"state": "unavailable", "backend_available": False}

    def _listening_mode(self):
        if self.microphone_listening_mode_manager is None:
            return "off"
        try:
            return self.microphone_listening_mode_manager.get_mode()
        except Exception as exc:
            self._error = str(exc)
            return "off"

    def _output_state(self):
        if self.voice_output_manager is None:
            return AudioOutputMode.OFF.value, False, False
        mode = str(getattr(self.voice_output_manager, "mode", "OFF")).upper()
        tts_enabled = bool(self.voice_output_manager.is_enabled())
        if mode == "DRY_RUN":
            return AudioOutputMode.TEST.value, tts_enabled, True
        if mode == "WINDOWS_LOCAL":
            return AudioOutputMode.LOCAL_TTS.value, tts_enabled, True
        return AudioOutputMode.OFF.value, False, True

    def _capture_mode(self, listening_mode, one_shot_active):
        if one_shot_active:
            return AudioCaptureMode.ONE_SHOT.value
        if listening_mode == "partial":
            return AudioCaptureMode.PARTIAL.value
        if listening_mode == "continuous":
            return AudioCaptureMode.CONTINUOUS_DISABLED.value
        return AudioCaptureMode.OFF.value

    def _voice_dialogue_active(self):
        manager = self.voice_dialogue_mode_manager
        if manager is None:
            return False
        return bool(getattr(manager, "is_manual_enabled", lambda: False)())

    def _pending_voice_command(self):
        if self.pending_voice_command_checker is None:
            return False
        try:
            return bool(self.pending_voice_command_checker())
        except Exception as exc:
            self._error = str(exc)
            return False

    @staticmethod
    def _event(event_type, previous_state, next_state, message_ru):
        return AudioLifecycleEvent(
            event_type=event_type,
            previous_state=previous_state,
            next_state=next_state,
            safe=True,
            message_ru=message_ru,
            network_used=False,
            audio_saved=False,
        )

    @staticmethod
    def _yes_no(value):
        return "yes" if value else "no"
