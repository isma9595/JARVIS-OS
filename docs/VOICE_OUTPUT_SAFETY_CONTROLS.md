# Voice Output Safety Controls

TASK-048 adds session-only brakes for JARVIS voice output.

## What They Do

- `замолчи`, `тихо`, `стоп голос` mute future voice output.
- Stop/mute also disables manual voice dialogue mode immediately.
- `снова говори` unmutes future voice output.
- Unmute does not re-enable manual voice dialogue. Use `включить голосовой диалог` separately.
- `не озвучивай следующий ответ` skips exactly the next voice output attempt, then clears itself.
- `статус голосовой безопасности` shows mute, skip, voice dialogue, and voice output state.

All speech still goes through `VoiceOutputManager`. Explicit speech commands, speak-last, tests, and manual dialogue current-response speech all respect mute and skip.

## Commands

- `замолчи`
- `тихо`
- `стоп голос`
- `снова говори`
- `не озвучивай следующий ответ`
- `статус голосовой безопасности`

## Safety Boundaries

- Mute state is in memory only for the current session.
- Skip-next state is in memory only for the current session.
- Voice dialogue mode is not persisted.
- No cloud TTS is used.
- No generated audio files are saved.
- No continuous listening is enabled.
- No background speech loops are added.
- No automatic downloads or installs are added.

## Windows TTS Limitation

The current Windows local TTS backend speaks synchronously. A command such as `стоп голос` mutes future speech and disables manual dialogue mode, but it does not claim to interrupt an already-started synchronous Windows `Speak()` call. True mid-speech interruption requires a future non-blocking, cancelable backend task.
