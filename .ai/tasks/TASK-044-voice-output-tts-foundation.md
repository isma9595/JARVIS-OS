# TASK-044 — Voice Output / Text-to-Speech Foundation

## Goal

Add a safe foundation for JARVIS voice output / text-to-speech behavior.

## Context

TASK-043 completed typed voice recognition simulation. JARVIS can now simulate recognized text, route known safe read-only voice commands through the allowlist, require confirmation for risky commands, keep in-memory voice history, and apply session-only recognition corrections before routing.

## Commands Added

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

## Safety Boundaries

- No cloud TTS.
- No external text/audio service calls.
- No generated audio files.
- No background speech loops.
- No automatic speech for every JARVIS response.
- No package installs or downloads.
- No `pyttsx3`, `win32com`, PowerShell speech, or system TTS dependency.
- No real audio playback in this task.
- No bypass around `CommandProcessor` or `ActionRouter`.

## Tests

- `tests/unit/test_speech_synthesis_backend.py`
- `tests/unit/test_voice_output_manager.py`
- `tests/unit/test_command_processor.py`
- Existing voice recognition tests remain part of verification.

## Manual Verification Commands

```powershell
python -m pytest tests/unit/test_speech_synthesis_backend.py
python -m pytest tests/unit/test_voice_output_manager.py
python -m pytest tests/unit/test_command_processor.py
python -m pytest tests/unit/test_voice_recognition_typed_simulation.py
python -m pytest tests/unit/test_voice_recognition_corrections.py
python -m pytest tests/unit/test_voice_command_confirmation_flow.py
python -m pytest tests/unit/test_voice_command_history.py
python -m pytest tests/unit/test_voice_command_allowlist.py
python -m pytest tests/unit/test_one_shot_vosk_real_recognition.py
python -m pytest
.\scripts\health_check.ps1
git status
python run.py
```

Manual `run.py` commands:

```text
статус голосового ответа
скажи: привет Исмаил
включить тестовый голос
статус голосового ответа
тест голоса
скажи: привет Исмаил
произнеси: система работает
озвучь: голосовой ответ тестируется
выключить голос
скажи: это не должно озвучиваться
помощь
выход
```

## Expected Result

- Initial voice output mode is `OFF`.
- Say commands while `OFF` do not call a backend and explain how to enable test mode.
- Test voice mode switches to `DRY_RUN`.
- Test and say commands show what would be spoken.
- Disabling returns to `OFF`.
- No real audio playback, cloud TTS, or audio files.
- Tests and health check pass.

## Commit Message Suggestion

Add voice output TTS foundation
