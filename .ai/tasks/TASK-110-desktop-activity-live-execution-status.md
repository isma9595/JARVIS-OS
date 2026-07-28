# TASK-110 - Desktop Activity & Live Execution Status

## Objective

Add a centralized application-level activity/status capability for Desktop
without coupling Desktop to workflow, coordinator, journal, provider, planner,
thread, token, or mutable runtime internals.

## Dependency Gate

- Starting branch: `main`
- Starting HEAD: `48f6e03a58b8364cf8abc5d4d111394f51133a71`
- Starting `origin/main`: `48f6e03a58b8364cf8abc5d4d111394f51133a71`
- Starting status: clean
- TASK-109 commit confirmed: `48f6e03 Harden workflow lifecycle`
- TASK-109 task record exists.
- Workflow subsystem milestone closure is documented.
- Future workflow expansion requires a newly approved milestone.

## Scope

- Add immutable activity DTOs.
- Add a narrow `ApplicationActivityTracker` projection owned below AppService.
- Expose `JarvisAppService.application_activity()`.
- Add a compact read-only Desktop Activity Status panel.
- Add focused tracker, AppService, and Desktop tests.
- Update relevant documentation.

## Architecture

The authoritative execution owner remains `ExecutionCoordinator` and its
bounded `ExecutionJournal`. TASK-110 does not create a second coordinator,
workflow history store, execution engine, event bus, telemetry system, or
Desktop execution authority.

Activity projection flow:

```text
DesktopShellState
    -> JarvisAppService.application_activity()
        -> ApplicationActivityTracker
            -> bounded ExecutionCoordinator operation snapshots
```

The selected model is foreground-only. The most recently observed active
user-visible operation is the current activity. Older active operations remain
owned by existing execution infrastructure and are not falsely marked complete.
Terminal outcomes are retained in a bounded recent list.

## Public Activity States

- `idle`
- `starting`
- `running`
- `waiting_for_user`
- `cancellation_requested`
- `succeeded`
- `failed`
- `rejected`
- `cancelled`
- `unknown`

Unknown or malformed internal states project safely and do not leak raw values.

## Safety And Concurrency Policy

- Terminal activity projection cannot regress to active.
- Duplicate terminal notifications are idempotent.
- The first terminal state wins in completion/cancellation races.
- Stale completion for an older operation does not replace a newer current
  activity.
- Launch failure projects a safe terminal outcome and clears busy state.
- Snapshot DTOs are frozen or tuple-backed.
- Tracker locks are not held across arbitrary business logic.
- Desktop refresh is read-only and guarded against overlapping refresh calls.

## Desktop Behavior

Desktop shows an Activity Status panel with current idle/busy state,
user-attention state, current safe title/detail/timestamps, and bounded recent
outcomes. The panel supports manual refresh and refreshes after existing
command, voice, workflow resume, and workflow cancellation actions complete.
No Desktop-owned polling thread is introduced.

## Exclusions

- No workflow live-step progress.
- No workflow subsystem redesign.
- No generic cancellation API.
- No telemetry, analytics, tracing, profiling, provider streaming, or new
  persistence.
- No background polling thread.
- No TASK-111 or future workflow expansion work.

## Files Changed

- `README.md`
- `app/__init__.py`
- `app/activity.py`
- `app/app_contracts.py`
- `app/app_service.py`
- `app/desktop_shell.py`
- `docs/APPSERVICE_CONTRACTS.md`
- `docs/ARCHITECTURE.md`
- `docs/DESKTOP_APP_SHELL.md`
- `tests/unit/test_application_activity.py`
- `tests/unit/test_app_service.py`
- `tests/unit/test_desktop_shell.py`
- `.ai/tasks/TASK-110-desktop-activity-live-execution-status.md`

## Focused Tests

- `python -m pytest -q tests/unit/test_application_activity.py`
  - Result: `8 passed`
- `python -m pytest -q tests/unit/test_app_contracts.py`
  - Result: `10 passed`
- `python -m pytest -q tests/unit/test_app_service.py`
  - Result: `100 passed`
- `python -m pytest -q tests/unit/test_desktop_shell.py`
  - Result: `89 passed`

TASK-110 regression/behavior selections:

- `python -m pytest -q tests/unit/test_application_activity.py::test_terminal_state_cannot_return_to_active tests/unit/test_application_activity.py::test_stale_completion_does_not_replace_newer_current_activity tests/unit/test_application_activity.py::test_launch_failure_clears_busy_state_and_sanitizes_error tests/unit/test_application_activity.py::test_duplicate_terminal_notification_is_idempotent tests/unit/test_application_activity.py::test_cancellation_completion_race_produces_one_terminal_state tests/unit/test_application_activity.py::test_snapshot_detachment_and_immutability tests/unit/test_application_activity.py::test_unknown_malformed_state_fails_safely tests/unit/test_application_activity.py::test_recent_outcomes_are_bounded_newest_first`
  - Result: `8 passed`
- `python -m pytest -q tests/unit/test_desktop_shell.py::test_desktop_activity_renders_current_and_recent_outcome tests/unit/test_desktop_shell.py::test_desktop_activity_idle_transition_clears_stale_current tests/unit/test_desktop_shell.py::test_desktop_activity_refresh_failure_preserves_usability_and_recovers tests/unit/test_desktop_shell.py::test_desktop_activity_refresh_guard_prevents_overlapping_reads tests/unit/test_desktop_shell.py::test_desktop_activity_boundary_uses_appservice_only tests/unit/test_app_service.py::test_application_activity_projects_current_and_recent_operations_safely tests/unit/test_app_service.py::test_application_activity_failure_returns_safe_unavailable_snapshot`
  - Result: `7 passed`

## Final Verification

- Full pytest:
  - Command: `python -m pytest -q`
  - Result: `1798 passed, 2 skipped in 7.72s`
- Health check:
  - Command: `powershell -ExecutionPolicy Bypass -File scripts\health_check.ps1`
  - Result: `Result: SUCCESS`
  - The health script also ran pytest internally and reported
    `1798 passed, 2 skipped in 7.43s`.
- Assistant smoke check:
  - Command: `powershell -ExecutionPolicy Bypass -File scripts\assistant_smoke.ps1`
  - Result: `JARVIS ASSISTANT SMOKE: SUCCESS`
- Key import probe:
  - Command: `python -c "from app.app_service import JarvisAppService; service=JarvisAppService(); snapshot=service.application_activity(); print('IMPORT_OK', snapshot.status_available, snapshot.is_busy, len(snapshot.recent))"`
  - Result: `IMPORT_OK True False 0`
- Source compileall:
  - Command: `python -m compileall app core workflows tests`
  - Result: completed successfully.
- Whitespace check:
  - Command: `git diff --check`
  - Result: exit code 0. Git reported existing line-ending conversion warnings
    for touched tracked files, but no whitespace errors.

## Completion Status

Complete pending pre-commit review, commit approval, commit, and push.
