# TASK-073 — AppService Contracts

## Goal

Create stable, typed, versioned AppService contracts for the future JARVIS
desktop UI, AI provider settings UI, installer/product mode, mobile companion,
and future admin/support features.

## Context

- TASK-072 — Warnings Audit is the current stable stage.
- Stable commit: `9e12588`
- Stable commit message: `Fix project warnings audit`
- Previous full pytest result: `1179 passed`
- `health_check` previously passed.
- AppService, desktop shell, and secure key storage foundations already exist.

## User Requirements

- No new user-facing product features.
- No AI Provider Settings UI, installer, mobile app, or admin/support backend.
- No provider request behavior changes.
- No secure key behavior changes.
- No CommandProcessor rewrite.
- No AppService bypass.
- No new dependencies.
- No commit or push.

## Contracts Added

- `APP_CONTRACT_VERSION = "0.1"`
- `APP_CONTRACT_SCHEMA_NAME = "jarvis.app_service.contracts"`
- `AppContractStatus`
- `AppStatusCard`
- `AppCommandCard`
- `AppPreviewContract`
- `AppExecutionContract`
- `AppContractManifest`

## Commands Added

- `статус app contracts`
- `статус app service contracts`
- `статус контрактов приложения`
- `статус контрактов appservice`
- `app contracts status`
- `app contracts manifest`
- `manifest app contracts`
- `манифест контрактов приложения`
- `app service contract manifest`
- `app status cards`
- `карточки статуса приложения`
- `app command cards`
- `карточки команд приложения`

## Files Changed

- `app/app_contracts.py`
- `app/app_service.py`
- `app/__init__.py`
- `app/desktop_shell.py`
- `core/command_registry.py`
- `core/command_processor.py`
- `voice/voice_command_allowlist.py`
- `docs/APPSERVICE_CONTRACTS.md`
- `docs/JARVIS_APP_SERVICE.md`
- `docs/DESKTOP_APP_SHELL.md`
- `docs/COMMAND_REGISTRY.md`
- `docs/SECURE_KEY_STORAGE.md`
- `.ai/CHECKPOINT.md`
- `.ai/tasks/TASK-073-appservice-contracts.md`
- `tests/unit/test_app_contracts.py`
- `tests/unit/test_app_service.py`
- `tests/unit/test_desktop_shell.py`
- `tests/unit/test_command_processor.py`
- `tests/unit/test_command_registry.py`
- `tests/unit/test_voice_command_allowlist.py`

## Safety Boundaries

- Contract/list/status/card methods do not execute commands.
- Preview contracts do not execute commands.
- Execution contracts call the existing AppService execution path only.
- No ActionRouter direct calls from contract methods.
- No provider calls from contract methods.
- No decrypted secret access.
- No raw secrets in contract serialization.
- No response execution as commands.
- No network default.

## Tests

Run:

```powershell
python -m pytest tests/unit/test_app_contracts.py
python -m pytest tests/unit/test_app_service.py
python -m pytest tests/unit/test_desktop_shell.py
python -m pytest tests/unit/test_command_processor.py
python -m pytest tests/unit/test_command_registry.py
python -m pytest tests/unit/test_voice_command_allowlist.py
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

- `статус app contracts`
- `статус app service contracts`
- `статус контрактов приложения`
- `app contracts manifest`
- `app status cards`
- `app command cards`
- `статус app service`
- `статус desktop app`
- `статус secure keys`
- `статус command registry`
- `симулируй распознавание: статус app contracts`
- `симулируй распознавание: app contracts manifest`
- `симулируй распознавание: app command cards`
- `помощь`
- `выход`

Desktop smoke:

```powershell
python run_desktop.py
```

Expected: window opens, status is visible, preview still works, `статус ai`
execution still works, and the window closes normally.

## Expected Result

- Contract commands work.
- AppService contract methods work.
- Contract outputs have no secrets.
- No network is called.
- Provider behavior is unchanged.
- Secure key behavior is unchanged.
- Voice behavior has no regression.
- Full pytest passes with no warnings.
- Strict DeprecationWarning pytest passes.
- Health check succeeds.

## Commit Message Suggestion

`Add AppService contracts`
