# Audio Lifecycle

TASK-074 adds a metadata-only audio lifecycle foundation for JARVIS voice input and output.

The lifecycle exists so future Desktop UI and vertical integrations can ask one safe surface about microphone, capture, TTS, dialogue, and pending voice command state without starting audio resources.

## Relationships

- VoiceInputManager remains responsible for current voice input behavior.
- MicrophoneInputAdapter remains responsible for real microphone state and capture primitives.
- VoiceOutputManager and local TTS remain responsible for explicit speech output.
- AppService exposes lifecycle status and a safe status card for future UI surfaces.

## Safe Defaults

- No automatic listening on startup.
- No continuous listening enablement.
- No microphone capture from lifecycle status or metadata controls.
- No TTS playback from lifecycle status or metadata controls.
- No network.
- No audio saved.
- No command execution from lifecycle status output.

## Metadata-Only Controls

The controller can prepare or reset lifecycle metadata:

- `start_one_shot_metadata_only()`
- `stop_audio_metadata_only()`
- `pause_output_metadata_only()`
- `resume_output_metadata_only()`
- `reset_to_idle()`

In TASK-074 these methods do not open the microphone, play TTS, call providers, save files, or execute recognized text.

## Commands

- `статус audio lifecycle`
- `статус audio`
- `статус аудио`
- `статус аудио цикла`
- `audio lifecycle capabilities`
- `возможности аудио цикла`
- `reset audio lifecycle`

Status and capabilities are read-only and may be voice-auto-allowed. Reset/stop metadata commands are not voice-auto-allowed.

## Future

- Desktop audio controls.
- Audio settings UI.
- Safe one-shot capture button.
- Safe output controls.
- Audio resource cleanup for partial/continuous modes.
