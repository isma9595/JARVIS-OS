# TASK-069 - JARVIS App Service Layer

## Goal

Create a safe application service layer between a future Windows desktop UI and
the existing JARVIS core.

## Context

TASK-068 added the command registry and capability manifest foundation. The
registry is metadata-only: no network, no disk writes, no command execution.
`CommandProcessor` remains the execution source.

## User Requirements

- Prepare JARVIS for future desktop UI, dashboard cards, provider settings,
  secure key storage UI, installer/product mode, command preview, and stable
  app-facing execution.
- Do not create a GUI, installer, secure key storage, file/document reading,
  screen capture, automation, or new dependencies.
- Do not rewrite `CommandProcessor`.
- Do not replace `run.py`.
- Do not commit or push.

## Files Changed

- `app/__init__.py`
- `app/app_service.py`
- `core/command_registry.py`
- `core/command_processor.py`
- `voice/voice_command_allowlist.py`
- `docs/JARVIS_APP_SERVICE.md`
- `docs/COMMAND_REGISTRY.md`
- `docs/AI_PROVIDER_LIVE_VERIFICATION.md`
- `docs/AI_PROVIDER_ROUTER.md`
- `docs/AI_PROVIDER_FALLBACK_EXECUTION.md`
- `.ai/CHECKPOINT.md`
- `tests/unit/test_app_service.py`
- `tests/unit/test_command_processor.py`
- `tests/unit/test_command_registry.py`
- `tests/unit/test_voice_command_allowlist.py`

## Commands Added

- `статус app service`
- `статус jarvis app service`
- `статус сервиса приложения`
- `статус приложения jarvis`
- `app service status`
- `app service capabilities`
- `возможности app service`
- `возможности приложения jarvis`
- `app service manifest`
- `app service commands`
- `команды app service`
- `app preview: <text>`
- `предпросмотр команды: <text>`
- `preview command: <text>`
- `предварительная проверка команды: <text>`

## Safety Boundaries

- AppService does not bypass `CommandProcessor`.
- AppService does not bypass `CommandRegistry` metadata.
- AppService does not call `ActionRouter` directly.
- AppService does not call shell/system/file/network APIs directly.
- AppService does not call external AI providers.
- Network is not default.
- AppService does not store prompts or responses.
- AppService does not print secrets in text outputs.
- AI responses are not executed as commands.
- Preview does not execute target commands.

## Tests

- `python -m pytest tests/unit/test_app_service.py`
- `python -m pytest tests/unit/test_command_registry.py`
- `python -m pytest tests/unit/test_command_processor.py`
- `python -m pytest tests/unit/test_voice_command_allowlist.py`
- `python -m pytest`
- `.\scripts\health_check.ps1`
- `git diff --check`
- `git status`

## Manual Verification Commands

Run `python run.py`, then:

- `статус app service`
- `статус jarvis app service`
- `статус сервиса приложения`
- `статус приложения jarvis`
- `app service capabilities`
- `возможности приложения jarvis`
- `app service commands`
- `app preview: статус ai`
- `app preview: groq реальный запрос: test`
- `app preview: неизвестная команда`
- `статус command registry`
- `реестр команд`
- `команды приложение`
- `статус ai verification`
- `статус ai fallback execution`
- `симулируй распознавание: статус app service`
- `симулируй распознавание: app service capabilities`
- `симулируй распознавание: app preview: статус ai`
- `ожидающая голосовая команда`
- `нет`
- `помощь`
- `выход`

## Expected Result

- AppService status, capabilities, command list, and preview work.
- Preview does not execute the target command.
- Groq real request preview shows network/risk/privacy metadata but makes no
  provider request.
- Unknown preview is safe.
- Existing registry and AI commands still work.
- Voice AppService status/capability/list commands auto-execute.
- Voice preview commands require confirmation.
- No secrets printed.
- No network called by status/preview/list.
- `run.py` still works.

## Commit Message Suggestion

Add JARVIS app service layer
