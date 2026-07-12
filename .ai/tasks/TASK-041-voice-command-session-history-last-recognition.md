# TASK-041 — Voice Command Session History & Last Recognition

- Task ID: TASK-041
- Title: Voice Command Session History & Last Recognition
- Goal: Add in-memory observability for the last voice recognition result and recent voice command attempts.

## Context

TASK-040 completed conservative voice command normalization and safe aliases.

- Stable commit: `2ef5fbb`
- Commit message: `Add conservative voice command normalization`
- One-shot Vosk recognition can run by explicit command.
- Known safe read-only voice commands can auto-execute through the allowlist.
- Unknown and risky commands still require confirmation.
- `выход` bypasses pending voice confirmation and exits normally.

## Commands Added

- `последнее распознавание`
- `последняя голосовая команда`
- `что ты услышал`
- `что ты распознал`
- `история голосовых команд`
- `покажи историю голоса`
- `история распознавания`
- `сколько голосовых команд`
- `очистить историю голосовых команд`
- `очисти историю голоса`
- `сбросить историю распознавания`

## Safety Boundaries

- Session-only history.
- No disk persistence for recognized voice text.
- No audio storage.
- No cloud audio or text sending.
- No continuous listening.
- No background microphone listeners.
- Unknown and risky commands still require confirmation.
- No bypass around `CommandProcessor` or `ActionRouter`.
- No installs or downloads.

## Tests

- `tests/unit/test_voice_command_history.py`
- `tests/unit/test_voice_command_confirmation_flow.py`
- `tests/unit/test_command_processor.py`
- Existing voice allowlist, one-shot Vosk, and audio readiness tests.

## Manual Verification Commands

```powershell
python -m pytest tests/unit/test_voice_command_history.py
python -m pytest tests/unit/test_voice_command_confirmation_flow.py
python -m pytest tests/unit/test_command_processor.py
python -m pytest tests/unit/test_voice_command_allowlist.py
python -m pytest tests/unit/test_one_shot_vosk_real_recognition.py
python -m pytest
.\scripts\health_check.ps1
git status
```

Manual `run.py` flow:

```text
python run.py
последнее распознавание
история голосовых команд
сколько голосовых команд
распознай голос один раз
# say: статус системы
последнее распознавание
история голосовых команд
распознай голос один раз
# say: открой браузер
ожидающая голосовая команда
история голосовых команд
нет
история голосовых команд
сколько голосовых команд
очистить историю голосовых команд
история голосовых команд
помощь
выход
```

## Expected Result

- Empty history reports that no recognition exists yet.
- Safe command recognition records recognized and canonical command text.
- Unknown or risky recognition records pending confirmation.
- Confirmation and cancellation append session events.
- Count and clear work.
- No audio is saved.
- No cloud audio/text is sent.
- No continuous listening is enabled.
- Unknown/risky commands still require confirmation.
- Tests and health check pass.

## Commit Message Suggestion

`Add voice command session history`
