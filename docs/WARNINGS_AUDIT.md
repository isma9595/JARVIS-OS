# Warnings Audit

Warnings matter because they show compatibility drift before it becomes a runtime
failure. JARVIS should keep project-owned warnings visible, fixed when safe, and
covered by tests so AppService, Desktop, and UI work can grow on a clean base.

## Current Warnings Fixed

- Replaced project-owned `datetime.utcnow()` usage in `ideas/idea_manager.py`.
- Replaced project-owned `datetime.utcnow()` usage in `memory/memory_manager.py`.
- Added focused regression coverage in `tests/unit/test_warning_audit.py`.

## Timestamp Policy

UTC timestamps must use timezone-aware `datetime` values. Do not use
`datetime.utcnow()` in production code.

Use `core.time_utils.utc_now_iso_z()` for new serialized UTC timestamps. It
returns the existing JARVIS storage shape:

```text
YYYY-MM-DDTHH:MM:SSZ
```

The helper intentionally removes microseconds and converts the `+00:00` UTC
offset to trailing `Z` to preserve existing data compatibility as much as
possible.

## Warning Policy

- Fix project-owned warnings instead of hiding them.
- Do not silence warnings globally just to make test output clean.
- Warning filters are acceptable only when the warning source is third-party,
  cannot be fixed inside JARVIS, and the filter is narrow, documented, and
  covered by verification.
- If strict warning checks fail, record the exact warning source before deciding
  whether it is project-owned or external.

## Verification Commands

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
