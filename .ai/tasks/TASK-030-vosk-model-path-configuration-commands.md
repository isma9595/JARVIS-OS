# TASK-030 — Vosk Model Path Configuration Commands

## Goal

Add safe Russian-first text commands for configuring, reading, checking, and
clearing the local Vosk model path.

## What Was Added

- Russian commands to read the configured Vosk model path.
- Russian commands to save or update the configured Vosk model path.
- Russian commands to clear the configured Vosk model path.
- Safe path parsing for unquoted Windows paths and quoted paths with spaces.
- Path-state responses for missing paths, existing folders, missing folders,
  and file paths that are not directories.
- Tests for command parsing, persistence, clearing, and safety boundaries.
- Russian documentation for the manual path configuration workflow.

## Russian Commands Added

Read/check path:

- `путь модели vosk`
- `где модель vosk`
- `проверить путь модели vosk`
- `какой путь модели vosk`

Set/update path:

- `установи путь модели vosk <path>`
- `задай путь модели vosk <path>`
- `измени путь модели vosk <path>`
- `сохрани путь модели vosk <path>`
- `путь модели vosk <path>`

Clear path:

- `очисти путь модели vosk`
- `сбрось путь модели vosk`
- `удали путь модели vosk`
- `удалить путь модели vosk`

## What Was Intentionally Not Enabled

- Real speech recognition.
- Microphone capture.
- One-shot microphone capture connected to Vosk recognition.
- `CONTINUOUS` mode connected to real recognition.
- Background listeners or infinite loops.
- Automatic Vosk model downloads.
- Automatic Python package installs.
- Real Vosk model loading in tests.
- Audio recording to disk.
- Cloud audio sending.

## Safety Rules

The commands are configuration-only. They may save, show, check, or clear the
stored model path through the existing Vosk settings mechanism. They must not
import Vosk, load a model, open audio, start microphone capture, install
packages, download models, or activate recognition automatically.

## Russian-First Behavior

User-facing commands and responses are Russian-first. Internal class and method
names remain English to match the existing project style.

## Tests

Added or updated unit tests for:

- missing configured model path;
- configured existing directory;
- configured missing directory;
- configured path that is not a directory;
- set/update aliases;
- quoted path parsing;
- path with spaces;
- empty path rejection;
- clear aliases;
- safety hooks proving path commands do not start capture or load runtime;
- settings manager quote normalization.

## Manual Verification Commands

```powershell
python -m pytest tests/unit/test_vosk_settings_manager.py
python -m pytest tests/unit/test_vosk_local_recognition_gate.py
python -m pytest tests/unit/test_vosk_runtime_loader.py
python -m pytest tests/unit/test_vosk_local_backend.py
python -m pytest tests/unit/test_command_processor.py
python -m pytest
.\scripts\health_check.ps1
```

## Expected Result

JARVIS-OS understands Russian Vosk model path configuration commands. It can
set, show, check, and clear the Vosk model path safely, and it warns when the
configured path is missing or is not a directory. No real recognition,
microphone capture, continuous listening, automatic download, automatic install,
or model loading starts.

## Commit Message Suggestion

`Add Vosk model path commands`
