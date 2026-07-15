# TASK-071 — Secure Settings & API Key Storage

## Goal

Create a secure API key storage foundation for JARVIS without adding UI,
provider behavior changes, network validation, dependencies, commits, or pushes.

## Context

- TASK-070 — Desktop App Shell Prototype is the current stable stage.
- Stable commit: `ff8145c`
- Stable commit message: `Add desktop app shell prototype`
- `run_desktop.py`, `AppService`, `CommandRegistry`, and `CommandProcessor`
  already exist.

## User Requirements

Future desktop app work should be able to support adding/removing API keys,
checking key presence, enabling/disabling providers later, and enabling models
safely later. TASK-071 only creates the secure storage foundation.

## Files Changed

- `security/__init__.py`
- `security/secure_key_store.py`
- `security/api_key_manager.py`
- `core/command_processor.py`
- `core/command_registry.py`
- `voice/voice_command_allowlist.py`
- `app/app_service.py`
- `app/desktop_shell.py`
- `docs/SECURE_KEY_STORAGE.md`
- `docs/JARVIS_APP_SERVICE.md`
- `docs/DESKTOP_APP_SHELL.md`
- `docs/COMMAND_REGISTRY.md`
- `docs/AI_PROVIDER_ROUTER.md`
- `.ai/CHECKPOINT.md`
- tests under `tests/unit/`

## Commands Added

- `статус secure keys`
- `статус api ключей`
- `список api ключей`
- `статус ключей ai`
- `безопасность api ключей`
- `импортировать openai ключ из env`
- `импортировать gemini ключ из env`
- `импортировать groq ключ из env`
- `импортировать gigachat ключ из env`
- `удалить openai ключ`
- `удалить gemini ключ`
- `удалить groq ключ`
- `удалить gigachat ключ`

## Safety Boundaries

- No GUI screen.
- No installer.
- No provider enable/disable toggles.
- No automatic provider usage from secure storage.
- No external network.
- No real provider validation.
- No raw-key command arguments.
- No plain-text persistent key storage.
- No secret values printed.
- No new dependencies.
- No commit or push.

## Tests

Added/updated tests for secure key store, API key manager, command processor,
command registry, voice command allowlist, app service, and desktop shell.

## Manual Verification Commands

```powershell
python -m pytest tests/unit/test_secure_key_store.py
python -m pytest tests/unit/test_api_key_manager.py
python -m pytest tests/unit/test_command_processor.py
python -m pytest tests/unit/test_command_registry.py
python -m pytest tests/unit/test_voice_command_allowlist.py
python -m pytest tests/unit/test_app_service.py
python -m pytest tests/unit/test_desktop_shell.py
python -m pytest
.\scripts\health_check.ps1
git diff --check
git status
```

## Expected Result

Status/list/help are safe, no key values are printed, missing env import refuses
safely, dummy env import stores through encrypted/fake backend in tests, delete
works, no network is called, real provider request behavior is unchanged, and
voice auto-execution is limited to read-only secure key commands.

## Commit Message Suggestion

`Add secure API key storage foundation`
