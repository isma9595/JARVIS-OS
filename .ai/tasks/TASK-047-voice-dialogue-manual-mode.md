# TASK-047 - Voice Dialogue Manual Mode / Speak Current Response Gate

## Goal

Add a safe manual voice dialogue mode where JARVIS can speak current assistant responses only after explicit user opt-in.

## Context

TASK-046 added current-session assistant response history and the speak-last-response gate:

- `последний ответ`
- `озвучь последний ответ`
- `повтори голосом`

TASK-047 adds the next safe step: session-only manual speaking of suitable current responses.

## Commands Added

- `статус голосового диалога`
- `режим голосового диалога`
- `включить голосовой диалог`
- `включи голосовой диалог`
- `включить ручной голосовой диалог`
- `включи ручной голосовой диалог`
- `говори ответы голосом`
- `озвучивай ответы`
- `озвучивай текущие ответы`
- `выключить голосовой диалог`
- `выключи голосовой диалог`
- `отключить голосовой диалог`
- `не озвучивай ответы`
- `перестань озвучивать ответы`

## Safety Boundaries

- OFF by default.
- Session-only state.
- No continuous listening.
- No background loops.
- No cloud TTS.
- No external text or audio services.
- No generated audio files.
- No persisted voice dialogue state.
- No persisted assistant response history.
- All speech goes through `VoiceOutputManager`.
- Voice output must be `DRY_RUN` or `WINDOWS_LOCAL` before enabling manual dialogue.
- Voice-control, history, speak-last, confirmation, and unsafe/noisy responses are not auto-spoken.

## Tests

Added:

- `tests/unit/test_voice_dialogue_mode.py`

Updated:

- `tests/unit/test_command_processor.py`

## Manual Verification Commands

```powershell
python -m pytest tests/unit/test_voice_dialogue_mode.py
python -m pytest tests/unit/test_command_processor.py
python -m pytest
.\scripts\health_check.ps1
git status
```

Manual `python run.py` flow:

```text
статус голосового диалога
включить голосовой диалог
включить тестовый голос
включить голосовой диалог
статус системы
последний ответ
озвучь последний ответ
статус голосового диалога
выключить голосовой диалог
статус системы
включить локальный голос
включить голосовой диалог
статус системы
выключить голос
статус голосового диалога
помощь
выход
```

## Expected Result

- Voice dialogue starts OFF.
- Enabling while voice output is OFF fails safely.
- DRY_RUN and WINDOWS_LOCAL voice output modes can enable manual dialogue.
- Suitable current responses are spoken only in manual mode.
- Speak-last behavior remains unchanged.
- Last meaningful response history is not replaced by speech metadata.
- Disabling voice output also disables manual dialogue.
- Tests and health check pass.

## Commit Message Suggestion

Add manual voice dialogue mode
