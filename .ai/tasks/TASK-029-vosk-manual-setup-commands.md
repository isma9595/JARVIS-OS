# TASK-029: Vosk Manual Setup Commands

## Goal

Add Russian-first text commands for checking Vosk setup status and explaining
manual Vosk setup steps.

## What Was Added

- Russian Vosk readiness/status commands in `CommandProcessor`.
- Russian manual setup/help aliases for Vosk.
- Read-only model path status commands.
- Russian documentation for supported commands and safety boundaries.
- Unit tests for command routing, responses, path reporting, and safety.

## Russian Commands Added

Status/readiness:

- `статус vosk`
- `проверить vosk`
- `готов ли vosk`
- `готово ли распознавание`
- `статус распознавания`
- `проверка распознавания`
- `локальное распознавание`
- `готово ли локальное распознавание`

Setup/help:

- `настроить vosk`
- `как настроить vosk`
- `инструкция vosk`
- `настройка распознавания`

Model path status:

- `путь модели vosk`
- `где модель vosk`

## Intentionally Not Enabled

- Real speech recognition.
- Microphone capture.
- One-shot microphone capture connected to Vosk.
- `CONTINUOUS` mode connected to real recognition.
- Background listeners or infinite loops.
- Automatic model downloads.
- Automatic package installs.
- Real Vosk model loading in tests.
- Audio recording to disk.
- Cloud audio sending.
- Silent settings changes.

## Safety Rules

The new status commands use the existing safe Vosk recognition gate and remain
read-only. They do not access microphone devices, do not start capture, do not
load Vosk models, and do not import or execute the real Vosk runtime.

## Russian-First Behavior

User-facing responses explain readiness, blockers, warnings, next steps, and
manual setup in Russian. Internal code names remain English for consistency
with the existing codebase.

## Tests

Added or updated tests in `tests/unit/test_command_processor.py` for:

- Vosk status/readiness commands.
- Manual setup/help commands.
- Missing model path status.
- Configured model path status.
- Status response blockers and safe next steps.
- No microphone capture or Vosk selection calls from status commands.
- Existing command processor behavior.

## Manual Verification Commands

```powershell
python -m pytest tests/unit/test_vosk_local_recognition_gate.py
python -m pytest tests/unit/test_vosk_runtime_loader.py
python -m pytest tests/unit/test_vosk_local_backend.py
python -m pytest tests/unit/test_vosk_settings_manager.py
python -m pytest tests/unit/test_command_processor.py
python -m pytest
.\scripts\health_check.ps1
```

## Expected Result

JARVIS-OS understands Russian Vosk manual setup/status commands, explains
readiness and blockers in Russian, reports model path status safely, and does
not start real recognition, microphone capture, downloads, installs, or model
loading.

## Commit Message Suggestion

`Add Vosk manual setup commands`
