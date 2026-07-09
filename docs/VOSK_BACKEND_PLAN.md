# Vosk local backend plan

`VoskLocalBackend` is a safe, selectable skeleton for a future offline
speech-recognition backend. It does not import Vosk, load a model, access a
microphone, record audio, recognize speech, run system commands, or use the
network.

## Current contract

- Backend name: `vosk_local`
- Default language: `ru`
- Default model path: `None`
- Installation and model availability default to `False`
- Offline capability is declared, but runtime availability is always `False`
- `recognize_once()` always returns no text and an unavailable status

The backend can be selected through `MicrophoneInputAdapter`,
`VoiceInputManager`, or a supported command. Selection only replaces the
logical backend object. It does not request permission or start listening.

## Future implementation gates

Real recognition must be implemented as a separate, explicitly reviewed task.
Before changing runtime availability, that task must define dependency and
model provisioning, model-path validation, explicit microphone permission,
audio lifetime and non-retention rules, failure isolation, offline guarantees,
and tests with injected audio sources. No microphone or model loading should
occur during import, construction, status checks, or backend selection.
