# TASK-031 — Vosk Local Recognition Dry Run

## Goal

Add a safe local Vosk recognition dry-run foundation to JARVIS-OS.

## What Was Added

- `voice.vosk_local_recognition_dry_run.VoskLocalRecognitionDryRun`
- `VoskLocalRecognitionDryRunResult` structured result
- Fake/stub audio payload for dry-run recognition
- Dependency injection for gate checks and fake recognizer behavior
- CommandProcessor support for explicit dry-run commands
- Unit tests for blocked, successful, failing, and safety-only paths
- Russian documentation for dry-run behavior

## Russian Commands Added

- `пробный запуск vosk`
- `тест vosk`
- `тест распознавания`
- `пробное распознавание`
- `проверить локальное распознавание`
- `dry run vosk`

## What Was Intentionally Not Enabled

- Real speech recognition
- Microphone capture
- One-shot microphone capture connected to Vosk
- `CONTINUOUS` mode connected to real recognition
- Background listeners
- Infinite loops
- Vosk model downloads
- Python package installs
- Real Vosk model loading in tests
- Audio recording to disk
- Cloud audio sending
- Automatic setting changes

## Dry-Run Behavior

The dry run first consults the existing Vosk local recognition gate. If the gate
blocks recognition, the result is blocked and reports Russian-first blockers.
If the gate allows recognition, the dry run calls only an injected or default
fake recognizer using test data.

The result records:

- `success`
- `allowed`
- `dry_run`
- `used_fake_audio`
- `microphone_used`
- `real_model_loaded`
- `recognized_text`
- `blockers`
- `warnings`
- `message`
- `next_steps`

## Safety Rules

The dry run must remain fake/stub-based and explicit. It must not start
microphone capture, must not load a real Vosk model, must not call one-shot
capture, must not start continuous listening, and must not store or send audio.

## Russian-First Behavior

User-facing command responses are Russian-first. Responses explicitly confirm
whether the dry run was blocked or completed, list blockers when present, and
state that the real microphone and real model were not used.

## Tests

Added:

- `tests/unit/test_vosk_local_recognition_dry_run.py`

Updated:

- `tests/unit/test_command_processor.py`

## Manual Verification Commands

```powershell
python -m pytest tests/unit/test_vosk_local_recognition_dry_run.py
python -m pytest tests/unit/test_vosk_local_recognition_gate.py
python -m pytest tests/unit/test_vosk_settings_manager.py
python -m pytest tests/unit/test_vosk_runtime_loader.py
python -m pytest tests/unit/test_vosk_local_backend.py
python -m pytest tests/unit/test_command_processor.py
python -m pytest
.\scripts\health_check.ps1
```

## Expected Result

JARVIS-OS has a safe Vosk local recognition dry-run pathway. JARVIS can run a
fake/stub recognition dry run through safe gate checks and explain the result
in Russian. No real recognition, microphone capture, continuous listening,
download, install, model loading, audio recording, or cloud sending starts.

## Commit Message Suggestion

Add Vosk recognition dry run
