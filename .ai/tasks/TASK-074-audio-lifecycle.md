# TASK-074 - Audio Lifecycle

## Goal

Create a stable, safe audio lifecycle foundation for JARVIS voice input/output.

## Context

TASK-073 - AppService Contracts is the current stable stage.

- Stable commit: `6cf56af`
- Commit message: `Add AppService contracts`

## Requirements

- Metadata-only lifecycle surface.
- No real continuous listening.
- No automatic microphone startup.
- No audio capture on startup.
- No new dependencies.
- No provider or secure key behavior changes.
- No GUI audio settings.
- No installer.
- No voice system rewrite.
- No commit or push.

## Files Changed

- `voice/audio_lifecycle.py`
- `voice/__init__.py`
- `app/app_service.py`
- `core/command_processor.py`
- `core/command_registry.py`
- `voice/voice_command_allowlist.py`
- `docs/AUDIO_LIFECYCLE.md`
- Short doc references in AppService, desktop shell, contracts, and command registry docs.
- Audio lifecycle unit tests.

## Commands Added

- `статус audio lifecycle`
- `статус audio`
- `статус аудио`
- `статус аудио цикла`
- `статус голосового lifecycle`
- `статус голосового цикла расширенный`
- `audio lifecycle capabilities`
- `возможности audio lifecycle`
- `возможности аудио цикла`
- `возможности голосового цикла`
- `reset audio lifecycle`

## Safety Boundaries

- Status/capabilities are read-only.
- Reset/stop is metadata-only and not voice-auto-allowed.
- No microphone call.
- No TTS call.
- No network.
- No audio saved.
- No recognized text execution.
- `auto_listening_on_startup` is false.
- `continuous_listening_allowed` is false.

## Tests

- `python -m pytest tests/unit/test_audio_lifecycle.py`
- `python -m pytest tests/unit/test_audio_lifecycle_commands.py`
- `python -m pytest tests/unit/test_audio_lifecycle_voice_allowlist.py`
- `python -m pytest tests/unit/test_app_contracts.py`
- `python -m pytest tests/unit/test_app_service.py`
- `python -m pytest tests/unit/test_command_registry.py`
- `python -m pytest`
- `python -W error::DeprecationWarning -m pytest`
- `.\scripts\health_check.ps1`
- `git diff --check`
- `git status`

## Manual Verification

Run `python run.py`, then try:

- `статус audio lifecycle`
- `статус audio`
- `статус аудио`
- `статус аудио цикла`
- `audio lifecycle capabilities`
- `возможности аудио цикла`
- `reset audio lifecycle`
- `app status cards`
- `симулируй распознавание: статус audio lifecycle`
- `симулируй распознавание: возможности аудио цикла`
- `симулируй распознавание: reset audio lifecycle`

Expected: status/capability commands work; reset is metadata-only; no microphone starts; no TTS starts; no audio is saved; no network is called.

## Commit Message Suggestion

`Add audio lifecycle foundation`
