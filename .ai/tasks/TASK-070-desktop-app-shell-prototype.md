# TASK-070 — Desktop App Shell Prototype

## Goal

Create the first safe desktop application shell prototype for JARVIS.

## Context

TASK-069 completed the JARVIS App Service Layer at stable commit `e4b52c4`
with commit message `Add JARVIS app service layer`. AppService wraps
`CommandProcessor` safely, and `CommandRegistry` is the metadata foundation.

## User Requirements

- Future Windows desktop application foundation.
- Dashboard-style command UI.
- Command input from UI.
- Command preview before execution.
- Command execution through `JarvisAppService`.
- Command registry/category browsing.
- Future AI provider settings, secure key storage, installer/product mode.

## Files Changed

- `app/desktop_shell.py`
- `app/__init__.py`
- `run_desktop.py`
- `core/command_processor.py`
- `core/command_registry.py`
- `voice/voice_command_allowlist.py`
- `docs/DESKTOP_APP_SHELL.md`
- `docs/JARVIS_APP_SERVICE.md`
- `docs/COMMAND_REGISTRY.md`
- `docs/AI_PROVIDER_LIVE_VERIFICATION.md`
- `.ai/CHECKPOINT.md`
- `tests/unit/test_desktop_shell.py`
- `tests/unit/test_command_processor.py`
- `tests/unit/test_command_registry.py`
- `tests/unit/test_voice_command_allowlist.py`

## Commands Added

- `статус desktop app`
- `статус jarvis desktop`
- `статус desktop shell`
- `статус app shell`
- `статус окна jarvis`
- `возможности desktop app`
- `возможности desktop shell`
- `возможности окна jarvis`
- `desktop app capabilities`

## Safety Boundaries

- No new dependencies.
- Tkinter only, from Python standard library.
- GUI does not need to run for tests.
- `run.py` unchanged.
- No installer.
- No secure key storage.
- No file/document reading.
- No screen capture.
- No automation.
- No network by default.
- No external AI provider calls unless the user explicitly executes an existing provider command.
- No prompts/responses stored.
- No secrets stored or printed.
- No AI response execution.
- No commit or push.

## Tests

```powershell
python -m pytest tests/unit/test_desktop_shell.py
python -m pytest tests/unit/test_app_service.py
python -m pytest tests/unit/test_command_registry.py
python -m pytest tests/unit/test_command_processor.py
python -m pytest tests/unit/test_voice_command_allowlist.py
python -m pytest
.\scripts\health_check.ps1
git diff --check
git status
```

## Manual Verification Commands

```powershell
python run.py
```

Then run:

```text
статус desktop app
статус jarvis desktop
статус desktop shell
статус app shell
статус окна jarvis
возможности desktop app
возможности desktop shell
возможности окна jarvis
статус app service
app preview: статус ai
app preview: groq реальный запрос: test
статус command registry
команды приложение
симулируй распознавание: статус desktop app
симулируй распознавание: возможности desktop app
симулируй распознавание: app preview: статус ai
ожидающая голосовая команда
нет
помощь
выход
```

Desktop smoke, if tkinter is available:

```powershell
python run_desktop.py
```

## Expected Result

- Desktop status and capability commands work.
- AppService and registry still work.
- Preview does not execute.
- Voice status/capability commands auto-execute.
- Voice preview/arbitrary/provider/fallback/consensus commands still require confirmation or are not allowlisted.
- `run.py` still works.
- `run_desktop.py` exists and is separate.
- No secrets printed.
- No network called by status, preview, or list.

## Commit Message Suggestion

Add desktop app shell prototype
