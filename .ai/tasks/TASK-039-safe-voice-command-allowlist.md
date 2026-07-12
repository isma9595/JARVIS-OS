# TASK-039 — Safe Voice Command Allowlist

## Goal

Add a safe allowlist for low-risk read-only voice commands after the TASK-038 confirmation flow.

## Context

TASK-038 added one-shot Vosk recognition result confirmation. Recognized text creates a pending voice command and asks for typed confirmation `да / нет`.

TASK-039 keeps that flow for unknown and risky commands, but lets known safe read-only commands execute without extra confirmation.

## Commands Added

- список безопасных голосовых команд
- безопасные голосовые команды
- voice allowlist
- какие голосовые команды без подтверждения

## Initial Allowlist

- статус системы
- помощь
- статус vosk
- проверить модель vosk
- проверка аудио зависимостей
- проверить зависимости микрофона
- диагностика микрофона
- проверить numpy
- проверить sounddevice
- проверить vosk пакет
- как тебя зовут
- имя ассистента
- ожидающая голосовая команда
- сколько идей
- список идей
- что ты запомнил
- локальная память

## Safety Boundaries

- Do not allow all voice commands to auto-execute.
- Do not bypass `CommandProcessor` or `ActionRouter`.
- Do not auto-execute modifying commands.
- Do not auto-execute file, system, shell, install, download, email, internet, automation, or destructive commands.
- Do not enable continuous listening.
- Do not add background microphone listeners.
- Do not send audio to cloud.
- Do not save audio files by default.
- Do not install or download anything.

## Tests

- `tests/unit/test_voice_command_allowlist.py`
- `tests/unit/test_voice_command_confirmation_flow.py`
- `tests/unit/test_command_processor.py`
- `tests/unit/test_one_shot_vosk_real_recognition.py`
- `tests/unit/test_audio_dependency_readiness.py`

## Manual Verification Commands

```powershell
python -m pytest tests/unit/test_voice_command_allowlist.py
python -m pytest tests/unit/test_voice_command_confirmation_flow.py
python -m pytest tests/unit/test_command_processor.py
python -m pytest tests/unit/test_one_shot_vosk_real_recognition.py
python -m pytest tests/unit/test_audio_dependency_readiness.py
python -m pytest
.\scripts\health_check.ps1
git status
python run.py
```

Manual `run.py` checks:

```text
список безопасных голосовых команд
распознай голос один раз
# say: статус системы
распознай голос один раз
# say: помощь
распознай голос один раз
# say something unknown, for example: открой браузер
ожидающая голосовая команда
нет
помощь
выход
```

## Expected Result

Safe read-only allowlisted commands execute through the normal `CommandProcessor` flow without pending confirmation. Unknown and risky commands still create a pending command or are blocked by the safety router. Continuous listening, background listeners, cloud audio, audio-file saving, automatic installs, and downloads remain disabled.

## Commit Message Suggestion

Add safe voice command allowlist
