# TASK-036A - Vosk Settings Test Isolation Fix

## Issue

After TASK-036, a real local Vosk model path may be configured in local project
settings:

`C:\JARVIS-OS\models\vosk-model-small-ru-0.22`

Some unit tests expected no Vosk model path to be configured and were reading
the real local settings file. That made health checks depend on the developer's
machine state.

## Why Tests Must Be Isolated

Unit tests must be repeatable whether or not a user has configured a real Vosk
model path. Tests that need "no model path" should create temporary settings
with no path. Tests that need a configured path should use a temporary fake
directory or path.

## Changes

- Updated Vosk local backend tests to inject `VoskSettingsManager` instances
  backed by temporary test settings files.
- Updated the command processor test helper to create an isolated temporary
  Vosk settings file by default.
- Updated the Vosk model readiness command test to use the isolated voice
  manager setup instead of a bare command processor that reads local settings.

## Safety Notes

- The real configured Vosk model path is not removed or cleared.
- The real `models/` directory is not modified.
- No microphone capture is started.
- Real Vosk recognition is not enabled.
- Real Vosk models are not loaded.
- No downloads or installs are performed.

## Verification Commands

```powershell
python -m pytest tests/unit/test_vosk_local_backend.py
python -m pytest tests/unit/test_command_processor.py
python -m pytest tests/unit/test_vosk_settings_manager.py
python -m pytest tests/unit/test_vosk_model_readiness_verifier.py
python -m pytest tests/unit/test_vosk_local_recognition_gate.py
python -m pytest
.\scripts\health_check.ps1
```

## Commit Message Suggestion

Fix Vosk settings test isolation
