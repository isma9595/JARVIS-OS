# TASK-046 - Voice Dialogue Mode / Speak Last Response Gate

## Goal

Add a safe `speak last response` gate and a session-only assistant response
history foundation.

## Context

TASK-045 completed the Windows local TTS backend gate. JARVIS can now speak
only after explicit voice output commands and explicit mode enablement. TASK-046
keeps that safety model and adds repeat-last-response behavior without enabling
automatic voice dialogue.

Stable baseline:

- Last stable commit: `5940dec`
- Last stable commit message: `Add Windows local TTS backend gate`

## Commands Added

- `последний ответ`
- `покажи последний ответ`
- `что ты ответил`
- `что ты сказал последний раз`
- `последний ответ jarvis`
- `последний ответ джарвис`
- `озвучь последний ответ`
- `скажи последний ответ`
- `произнеси последний ответ`
- `повтори голосом`
- `повтори последний ответ голосом`
- `скажи это голосом`
- `озвучь это`
- `история ответов`
- `история ответов jarvis`
- `сколько ответов`
- `очистить историю ответов`
- `очисти историю ответов`
- `статус голосового диалога`
- `режим голосового диалога`

## Safety Boundaries

- No automatic speaking of every assistant response.
- No always-on voice dialogue mode.
- No background speech loops.
- No continuous listening.
- No direct TTS backend calls from `CommandProcessor`.
- No cloud TTS.
- No external text or audio services.
- No generated audio files saved.
- No persisted assistant response history.
- No package installs or downloads.

## Tests

Added:

- `tests/unit/test_assistant_response_history.py`

Updated:

- `tests/unit/test_command_processor.py`
- `tests/unit/test_voice_output_manager.py`

## Manual Verification Commands

```powershell
python -m pytest tests/unit/test_assistant_response_history.py
python -m pytest tests/unit/test_command_processor.py
python -m pytest tests/unit/test_voice_output_manager.py
python -m pytest tests/unit/test_windows_local_tts_backend.py
python -m pytest tests/unit/test_speech_synthesis_backend.py
python -m pytest tests/unit/test_voice_recognition_typed_simulation.py
python -m pytest tests/unit/test_voice_recognition_corrections.py
python -m pytest tests/unit/test_voice_command_confirmation_flow.py
python -m pytest tests/unit/test_voice_command_history.py
python -m pytest tests/unit/test_voice_command_allowlist.py
python -m pytest tests/unit/test_one_shot_vosk_real_recognition.py
python -m pytest
.\scripts\health_check.ps1
git status
```

Manual `run.py` flow:

```text
последний ответ
статус системы
последний ответ
озвучь последний ответ
включить тестовый голос
озвучь последний ответ
последний ответ
история ответов
сколько ответов
статус голосового диалога
включить локальный голос
повтори голосом
выключить голос
очистить историю ответов
последний ответ
помощь
выход
```

## Expected Result

- The first `последний ответ` reports that no JARVIS response exists yet.
- Normal assistant responses are stored in current-session memory.
- `последний ответ` shows the previous meaningful response.
- `озвучь последний ответ` while OFF does not speak and explains how to enable
  voice output.
- DRY_RUN speaks the last response as a dry-run only.
- WINDOWS_LOCAL speaks the last response only after explicit local voice enable.
- Speak-last commands do not replace the last meaningful response.
- History, count, clear, and voice dialogue status commands work.
- No automatic speaking, cloud TTS, audio-file storage, installs, or downloads.

## Commit Message Suggestion

`Add speak last response gate`
