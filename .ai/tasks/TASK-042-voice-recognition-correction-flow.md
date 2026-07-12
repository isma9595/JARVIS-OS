# TASK-042 - Voice Recognition Correction Flow

- Task ID: TASK-042
- Title: Voice Recognition Correction Flow
- Goal: Add a safe session-only correction flow for voice recognition mistakes.

## Context

TASK-041 added in-memory voice command history and last recognition tracking. TASK-042 builds on that flow so a user can explicitly correct Vosk misrecognitions during the current session.

## Commands Added

- `я сказал не <wrong>, а <correct>`
- `я говорил не <wrong>, а <correct>`
- `исправь распознавание: <wrong> -> <correct>`
- `исправь голос: <wrong> -> <correct>`
- `это не <wrong>, это <correct>`
- `голосовые исправления`
- `список голосовых исправлений`
- `покажи исправления распознавания`
- `сколько голосовых исправлений`
- `очистить голосовые исправления`
- `очисти исправления распознавания`
- `сбросить голосовые исправления`

## Safety Boundaries

- Corrections are session-only and in-memory.
- No disk persistence for corrections.
- No permanent allowlist modification.
- No broad fuzzy matching.
- Corrected text still passes through `CommandProcessor` and `ActionRouter`.
- Risky or unknown corrected commands still require confirmation.
- No continuous listening.
- No background microphone listeners.
- No cloud audio or text processing.
- No audio file storage.
- No automatic downloads or installs.

## Tests

- `tests/unit/test_voice_recognition_corrections.py`
- `tests/unit/test_voice_command_confirmation_flow.py`
- `tests/unit/test_command_processor.py`
- `tests/unit/test_voice_command_history.py`
- `tests/unit/test_voice_command_allowlist.py`
- `tests/unit/test_one_shot_vosk_real_recognition.py`
- `tests/unit/test_audio_dependency_readiness.py`

## Manual Verification Commands

```powershell
python -m pytest tests/unit/test_voice_recognition_corrections.py
python -m pytest tests/unit/test_voice_command_confirmation_flow.py
python -m pytest tests/unit/test_command_processor.py
python -m pytest tests/unit/test_voice_command_history.py
python -m pytest tests/unit/test_voice_command_allowlist.py
python -m pytest tests/unit/test_one_shot_vosk_real_recognition.py
python -m pytest
.\scripts\health_check.ps1
git status
python run.py
```

Manual `run.py` prompts:

- `голосовые исправления`
- `я сказал не статуя система, а статус системы`
- `голосовые исправления`
- `сколько голосовых исправлений`
- `распознай голос один раз`
- `последнее распознавание`
- `история голосовых команд`
- `исправь распознавание: браузер -> открой браузер`
- `распознай голос один раз`
- `нет`
- `очистить голосовые исправления`
- `голосовые исправления`
- `помощь`
- `выход`

## Expected Result

- Correction list/count/clear works.
- Corrections remain session-only.
- Original and corrected recognition text are visible.
- Corrected safe allowlisted commands may auto-execute.
- Corrected risky commands still require confirmation and safety processing.
- History records correction added/applied events.
- No continuous listening, cloud calls, audio files, installs, downloads, commit, or push.

## Commit Message Suggestion

`Add voice recognition correction flow`
