# Voice Backend Research

## Current state

JARVIS OS has voice-command simulation and confirmation flow, but it does not
capture audio or perform speech recognition. `SpeechRecognitionBackend` is the
extension boundary for a future implementation.

## NoSpeechRecognitionBackend

The default backend is intentionally unavailable. It never opens a microphone,
records audio, invokes system commands, uses a network, or returns recognized
text. Calls return the `speech.backend.unavailable` intent.

## Candidate backends

- **Vosk local:** offline, relatively lightweight, and suitable for streaming;
  requires a separately installed engine and language model.
- **Whisper local:** generally robust recognition but needs more compute and a
  separately installed runtime and model.
- **Windows Speech Recognition adapter:** can use an operating-system facility,
  but is Windows-specific and requires careful permission and lifecycle handling.

## Recommendation

Prototype a Vosk adapter first behind this interface because it is offline and
stream-oriented. Keep Whisper as an opt-in higher-accuracy alternative. Make
Windows integration a platform-specific adapter. Any implementation needs a
separate review and explicit dependency and microphone authorization.

## Safety rules

- Microphone access must require explicit user permission.
- Never start capture during construction, status checks, or command parsing.
- Keep audio and transcripts local unless the user explicitly approves otherwise.
- Do not retain audio by default; disclose and control any retention.
- Validate backend availability and installation without executing arbitrary
  system commands.
- Preserve confirmation checks after recognition; recognized text is untrusted
  input and must not directly execute actions.
