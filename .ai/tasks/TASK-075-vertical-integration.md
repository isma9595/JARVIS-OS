# TASK-075 - Vertical Integration

## Goal

Create a safe vertical integration foundation that verifies the current JARVIS
stack works end-to-end across the major layers without adding product features.

## Context

- TASK-074 - Audio Lifecycle is completed and pushed.
- Current stable commit: `1f6133b`
- Commit message: `Add audio lifecycle foundation`
- Previous full pytest: 1219 passed.
- Previous strict DeprecationWarning pytest: 1219 passed.
- Previous health_check passed.

## User Requirements

- No new product features.
- No AI Provider Settings UI, installer, mobile app, or admin/support backend.
- No provider request behavior changes.
- No secure key or audio behavior changes.
- No microphone, TTS, provider, or network calls.
- No prompts/responses or secrets stored.
- No CommandProcessor rewrite.
- No AppService bypass.
- No dependencies.
- No commit or push.

## Files Changed

- `app/vertical_integration.py`
- `app/app_service.py`
- `app/__init__.py`
- `core/command_registry.py`
- `core/command_processor.py`
- `voice/voice_command_allowlist.py`
- `docs/VERTICAL_INTEGRATION.md`
- short references in AppService, contracts, desktop shell, audio lifecycle,
  command registry, and secure key docs
- `tests/unit/test_vertical_integration.py`
- targeted updates to AppService, CommandProcessor, CommandRegistry, and voice
  allowlist tests

## Commands Added

- `статус vertical integration`
- `статус интеграции jarvis`
- `статус вертикальной интеграции`
- `vertical integration status`
- `integration status`
- `vertical integration checklist`
- `чеклист vertical integration`
- `чеклист интеграции jarvis`
- `чеклист вертикальной интеграции`
- `vertical integration summary`
- `кратко vertical integration`
- `кратко интеграция jarvis`

## Checks Added

- CommandRegistry availability and required categories
- AppService contract availability and manifest safety
- AppService status and preview safety
- DesktopShellViewModel safe construction and preview
- Secure key metadata safety
- Audio lifecycle metadata safety
- Voice allowlist boundaries
- AI provider explicit-only safety
- No network/no secret/no provider integration flags
- Metadata-only CommandProcessor smoke placeholder

## Safety Boundaries

- no network
- no secrets
- no providers called
- no microphone or TTS start
- no audio saved
- no response execution
- no risky command execution

## Tests

Run:

```powershell
python -m pytest tests/unit/test_vertical_integration.py
python -m pytest tests/unit/test_app_service.py
python -m pytest tests/unit/test_command_processor.py
python -m pytest tests/unit/test_command_registry.py
python -m pytest tests/unit/test_voice_command_allowlist.py
python -m pytest tests/unit/test_desktop_shell.py
python -m pytest
python -W error::DeprecationWarning -m pytest
.\scripts\health_check.ps1
git diff --check
git status
```

## Manual Verification Commands

```powershell
python run.py
```

Then:

- `статус vertical integration`
- `статус интеграции jarvis`
- `статус вертикальной интеграции`
- `vertical integration checklist`
- `чеклист интеграции jarvis`
- `vertical integration summary`
- `кратко интеграция jarvis`
- `статус app contracts`
- `app status cards`
- `статус app service`
- `статус desktop app`
- `статус secure keys`
- `статус audio lifecycle`
- `статус command registry`
- `симулируй распознавание: статус vertical integration`
- `симулируй распознавание: чеклист интеграции jarvis`
- `симулируй распознавание: vertical integration summary`
- `симулируй распознавание: groq реальный запрос: test`
- `ожидающая голосовая команда`
- `нет`
- `помощь`
- `выход`

Desktop smoke:

```powershell
python run_desktop.py
```

## Expected Result

- Vertical integration report passes.
- No network called.
- No providers called.
- No secrets printed.
- No microphone/TTS starts.
- Risky voice commands remain confirmation-required.
- Full pytest and strict DeprecationWarning pytest pass.
- health_check succeeds.
- run.py and run_desktop.py still work.

## Commit Message Suggestion

`Add vertical integration checks`
