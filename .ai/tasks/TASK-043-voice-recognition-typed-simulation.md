# TASK-043 - Voice Recognition Typed Simulation

- Task ID: TASK-043
- Title: Voice Recognition Typed Simulation
- Goal: Add a safe typed simulation command for the voice recognition pipeline.

## Context

TASK-042 completed the voice recognition correction flow. JARVIS can run one-shot Vosk recognition, auto-execute known safe read-only voice commands, require confirmation for unknown or risky voice commands, keep in-memory voice history, and apply session-only corrections before safety decisions.

TASK-043 adds typed simulation because live microphone and Vosk recognition can return empty text even when the command pipeline is correct.

## Commands Added

- `симулируй распознавание: <текст>`
- `симуляция распознавания: <текст>`
- `тест распознавания: <текст>`
- `тестовое распознавание: <текст>`
- `проверить голосовую команду: <текст>`
- `проверь голосовую команду: <текст>`

Empty text returns:

`Укажите текст для симуляции распознавания.`

## Safety Boundaries

- No microphone use.
- No Vosk/model loading.
- No cloud calls.
- No audio file storage.
- No persisted simulated recognition.
- No continuous listening.
- No background listeners.
- No automatic downloads or installs.
- Simulated text does not bypass allowlist, pending confirmation, `CommandProcessor`, or `ActionRouter`.
- Risky or unknown commands do not execute automatically.
- History records simulated input with source `typed_simulation`.

## Tests

- `tests/unit/test_voice_recognition_typed_simulation.py`
- `tests/unit/test_command_processor.py`
- `tests/unit/test_voice_recognition_corrections.py`
- `tests/unit/test_voice_command_confirmation_flow.py`
- `tests/unit/test_voice_command_history.py`
- `tests/unit/test_voice_command_allowlist.py`
- `tests/unit/test_one_shot_vosk_real_recognition.py`
- `tests/unit/test_audio_dependency_readiness.py`

## Manual Verification Commands

```powershell
python -m pytest tests/unit/test_voice_recognition_typed_simulation.py
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

- `симулируй распознавание: статус системы`
- `последнее распознавание`
- `история голосовых команд`
- `симулируй распознавание: открой браузер`
- `последнее распознавание`
- `история голосовых команд`
- `нет`
- `я сказал не статуя система, а статус системы`
- `симулируй распознавание: статуя система`
- `исправь распознавание: браузер -> открой браузер`
- `симулируй распознавание: браузер`
- `последнее распознавание`
- `история голосовых команд`
- `нет`
- `помощь`
- `выход`

## Expected Result

- Safe command simulation works.
- Risky command simulation creates pending confirmation.
- Risky commands are not auto-executed.
- Corrections apply to simulated recognition.
- Corrected risky commands still require confirmation and safety processing.
- History shows simulated events.
- No microphone, Vosk/model, cloud, audio files, installs, downloads, commit, or push.
- Full tests and health check pass.

## Commit Message Suggestion

`Add voice recognition typed simulation`
