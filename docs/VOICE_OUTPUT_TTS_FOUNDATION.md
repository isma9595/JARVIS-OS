# Voice Output / TTS Foundation

TASK-044 adds a safe foundation for JARVIS voice output without enabling real audio playback.

## What Was Added

- `SpeechSynthesisBackend`: base interface for future speech synthesis backends.
- `SpeechSynthesisResult`: structured result for synthesis attempts.
- `DryRunSpeechSynthesisBackend`: safe simulated backend that only reports what would be spoken.
- `VoiceOutputManager`: mode control, text validation, dry-run speech routing, and safety responses.
- Explicit Russian-first commands for voice output status, test mode, disabling, and manual speech.

## Modes

### OFF

Default mode. JARVIS does not speak and does not call a TTS backend.

### DRY_RUN

Safe test mode. JARVIS returns text like:

```text
[TTS dry-run] Исмаил, система работает.
```

No real sound is played.

## Safety Boundaries

- Cloud TTS is not used.
- Text and audio are not sent to external services.
- Audio files are not generated or saved.
- Real playback is not started.
- Background speech loops are not added.
- JARVIS does not speak every response automatically.
- Commands stay explicit and routed through `CommandProcessor`.

## Commands

- `статус голосового ответа`
- `статус голоса`
- `голосовой ответ статус`
- `включить тестовый голос`
- `включи тестовый голос`
- `режим голоса dry run`
- `режим голоса тест`
- `выключить голос`
- `выключи голос`
- `отключить голосовой ответ`
- `скажи: <текст>`
- `произнеси: <текст>`
- `озвучь: <текст>`
- `тест голоса`
- `проверка голоса`
- `что ты можешь сказать голосом`

## Why Real Playback Is Not Enabled Yet

Real playback requires platform-specific or package-specific dependencies such as Windows SAPI, `pyttsx3`, or another approved local engine. This task intentionally avoids those dependencies so the behavior is deterministic, offline, and safe.

## Future Direction

- Windows SAPI backend after explicit approval.
- `pyttsx3` or another local backend after dependency approval.
- Speak last response.
- Voice dialogue mode.
- Voice selection, speed, and volume controls.
