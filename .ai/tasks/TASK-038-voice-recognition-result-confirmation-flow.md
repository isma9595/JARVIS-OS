# TASK-038 — Voice Recognition Result Confirmation Flow

## Goal

Add a safe confirmation flow between real one-shot Vosk recognition and command
execution.

## Context

TASK-037 enabled explicit real one-shot Vosk recognition. TASK-037A added audio
capture dependency diagnostics. The stable commit before this task is
`f167f8f` with message `Add audio capture dependency diagnostics`.

Before TASK-038, recognized text was displayed but not executable. TASK-038
stores a successful non-empty recognition result as a pending in-memory command
and requires explicit confirmation before processing it.

## Commands added

Status:

- `ожидающая голосовая команда`
- `pending voice command`
- `какая голосовая команда ожидает подтверждения`

Cancel:

- `отменить голосовую команду`
- `сбросить голосовую команду`

Confirm aliases:

- `да`
- `подтверждаю`
- `выполнить`
- `выполни`
- `ок`
- `ага`
- `yes`

Cancel aliases:

- `нет`
- `отмена`
- `отмени`
- `не надо`
- `no`

## Safety boundaries

- No automatic execution without confirmation.
- No continuous listening.
- No background microphone listeners.
- No cloud audio.
- No audio files saved by default.
- No automatic installs or downloads.
- No dangerous command bypass.
- Confirmation only routes recognized text through normal command processing.

## Tests

Added `tests/unit/test_voice_command_confirmation_flow.py`.

Updated:

- `tests/unit/test_command_processor.py`
- `tests/unit/test_one_shot_vosk_real_recognition.py`

Covered behavior includes pending creation, no immediate execution,
confirmation aliases, cancellation aliases, unrelated input while pending,
status/cancel commands, replacement by new recognition, empty/blocked
recognition, safe command confirmation, safety router preservation, recursion
safety, and help text.

## Manual verification commands

```powershell
python -m pytest tests/unit/test_voice_command_confirmation_flow.py
python -m pytest tests/unit/test_command_processor.py
python -m pytest tests/unit/test_one_shot_vosk_real_recognition.py
python -m pytest tests/unit/test_audio_dependency_readiness.py
python -m pytest
.\scripts\health_check.ps1
git status
```

Manual `run.py` flow:

```text
python run.py
распознай голос один раз
# say: статус системы
ожидающая голосовая команда
да
распознай голос один раз
# say: статус системы
нет
ожидающая голосовая команда
распознай голос один раз
# say: статус системы
отменить голосовую команду
помощь
выход
```

## Expected result

After real one-shot recognition, JARVIS asks for confirmation and does not
execute recognized text automatically. `да` executes the pending recognized
command through the normal processor. `нет` cancels it. Status and cancel
commands work. Help mentions the confirmation flow. Continuous listening, cloud
audio, and default audio saving remain disabled.

## Commit message suggestion

`Add voice command confirmation flow`
