# TASK-072 - Warnings Audit

## Goal

Audit and fix current project warnings so JARVIS stays clean, maintainable, and
ready for AppService, Desktop, and UI growth.

## Context

- TASK-071 - Secure Settings & API Key Storage is completed and pushed.
- Current stable commit: `fe0cde1`
- Commit message: `Add secure API key storage foundation`
- Previous full pytest result: `1172 passed, 44 warnings`

## Files Changed

- `core/time_utils.py`
- `ideas/idea_manager.py`
- `memory/memory_manager.py`
- `tests/unit/test_warning_audit.py`
- `docs/WARNINGS_AUDIT.md`
- `.ai/tasks/TASK-072-warnings-audit.md`
- `.ai/CHECKPOINT.md`

## Warnings Found

- Project-owned `datetime.utcnow()` deprecation warnings in
  `ideas/idea_manager.py`.
- Project-owned `datetime.utcnow()` deprecation warnings in
  `memory/memory_manager.py`.
- Local pytest cache warnings may appear if `.pytest_cache` permissions are
  broken; these are not production-code warnings.

## Warnings Fixed

- Added `core.time_utils.utc_now_iso_z()` using timezone-aware UTC.
- Updated idea timestamps to use the helper.
- Updated memory timestamps to use the helper.
- Preserved serialized timestamp format: `YYYY-MM-DDTHH:MM:SSZ`.

## Tests

- Added timestamp helper format tests.
- Added deprecation-warning checks for idea and memory timestamp creation.
- Added production-source scan preventing `datetime.utcnow()` regressions.
- Added audit-document existence/content test.

## Manual Verification

Run:

```powershell
python -m pytest tests/unit/test_warning_audit.py
python -m pytest tests/unit/test_idea_manager.py
python -m pytest tests/unit/test_memory_manager.py
python -m pytest tests/unit/test_command_processor.py
python -m pytest

python -W error::DeprecationWarning -m pytest tests/unit/test_warning_audit.py
python -W error::DeprecationWarning -m pytest tests/unit/test_idea_manager.py
python -W error::DeprecationWarning -m pytest tests/unit/test_memory_manager.py
python -W error::DeprecationWarning -m pytest tests/unit/test_command_processor.py
python -W error::DeprecationWarning -m pytest

.\scripts\health_check.ps1
git diff --check
git status
```

Manual `run.py` commands:

```text
статус
статус app service
статус desktop app
статус secure keys
статус command registry
помощь
выход
```

## Expected Result

- `run.py` still works.
- No user-visible behavior regression.
- Timestamps serialize in safe UTC trailing-`Z` format.
- Normal full pytest should ideally show zero warnings.
- Any remaining warnings must be documented and not project-owned if possible.
- Health check succeeds.
- `git diff --check` has only CRLF warnings if any.
- No secrets, network calls, provider behavior changes, voice behavior changes,
  GUI changes, installer changes, or new dependencies.

## Commit Message Suggestion

```text
Fix project warnings audit
```
