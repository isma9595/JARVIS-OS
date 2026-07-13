# Voice Dialogue Manual Mode

TASK-047 adds a session-only manual voice dialogue mode.

Manual mode is OFF by default. When the user explicitly enables it, JARVIS can speak the current meaningful assistant response after it is generated. Speech always goes through `VoiceOutputManager.speak(...)`.

## Requirements

Manual dialogue mode requires voice output to be enabled first:

- `включить тестовый голос`
- `включить локальный голос`

If voice output is OFF, JARVIS refuses to enable manual dialogue mode and asks the user to enable test or local voice first.

## Commands

- `включить голосовой диалог`
- `говори ответы голосом`
- `озвучивай ответы`
- `выключить голосовой диалог`
- `не озвучивай ответы`
- `статус голосового диалога`

## Safety

Manual voice dialogue mode:

- does not enable continuous listening;
- does not start background loops;
- does not use cloud TTS;
- does not send text or audio to external services;
- does not save generated audio files;
- does not persist mode state to disk;
- does not persist assistant response history to disk.

JARVIS does not speak voice-control commands, speak-last commands, response-history commands, risky confirmation prompts, pending yes/no prompts, empty responses, or responses beyond the voice output length limit.

Disabling voice output also disables manual voice dialogue mode for safety.

## Difference From Other Voice Features

`скажи: <текст>` speaks only the exact text after an explicit command.

`озвучь последний ответ` speaks the last meaningful response from the current session after an explicit command.

Manual voice dialogue speaks suitable current responses only after the user explicitly enables the manual dialogue mode for the current session.

Real voice recognition remains separate. Manual dialogue mode does not listen to the microphone and does not execute recognized commands.

## Future Direction

Possible future work requires separate safety review:

- stop speaking;
- interrupt speech;
- wake and stop words;
- one-shot voice dialogue;
- limited continuous mode.
