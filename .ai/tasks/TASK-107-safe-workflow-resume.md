# TASK-107 - Safe Workflow Resume

## Objective

Implement explicit safe workflow resume using the TASK-105 workflow history
foundation and TASK-106 Desktop Workflow Viewer.

## Scope

- Add central workflow resume eligibility and typed resume result contracts.
- Resume only eligible failed/interrupted in-memory workflow runs.
- Preserve completed steps and never rerun them by default.
- Create a distinct resumed attempt linked to the source run.
- Expose resume through `JarvisAppService`.
- Add a Desktop Resume action driven only by AppService-projected eligibility.
- Keep replay, retry of completed steps, editing, deletion, export, and
  restart-persistent recovery out of scope.

## Architecture Inspected

- `workflows/contracts.py`
- `workflows/runner.py`
- `core/execution_coordinator.py`
- `core/execution_journal.py`
- `core/policy_boundary.py`
- `app/app_service.py`
- `app/app_contracts.py`
- `app/desktop_shell.py`
- `tests/unit/test_workflow_runner.py`
- `tests/unit/test_app_service.py`
- `tests/unit/test_desktop_shell.py`
- `docs/ARCHITECTURE.md`
- `docs/JARVIS_APP_SERVICE.md`
- `docs/DESKTOP_APP_SHELL.md`
- `docs/APPSERVICE_CONTRACTS.md`

## Resume Model

The implementation uses the existing in-memory `WorkflowRunner` as the source
of truth. A resume request creates a new operation/run attempt and links it to
the source run through safe metadata. Completed source steps are copied as
preserved completed context and skipped by the runner. Execution begins at the
first safe unfinished step.

The source run remains queryable. Its step history is not rewritten as if the
original run had completed successfully.

## Eligibility Rules

Eligibility is centralized in the workflow runner/AppService boundary, not in
Desktop. The current implementation rejects missing runs, completed runs,
active runs, cancelled/denied runs, malformed run state, malformed step state,
missing or incompatible workflow definition metadata, no unfinished steps,
non-resumable steps, duplicate/already-resumed runs, and concurrent resume
conflicts.

## Compatibility Mechanism

The runner records a stable workflow definition fingerprint based on workflow
id, ordered step ids, confirmation requirement, and resumability. Resume is
rejected when the current definition fingerprint no longer matches the recorded
run.

## Concurrency And Idempotency

The runner protects eligibility and attempt creation with its existing lock,
tracks sources currently resuming, and records source-to-attempt mappings to
prevent duplicate resumed executions. AppService also registers resume through
`ExecutionCoordinator` using deterministic resume idempotency metadata.

## Files Changed

- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/APPSERVICE_CONTRACTS.md`
- `docs/DESKTOP_APP_SHELL.md`
- `docs/JARVIS_APP_SERVICE.md`
- `workflows/contracts.py`
- `workflows/runner.py`
- `app/app_service.py`
- `app/desktop_shell.py`
- `tests/unit/test_workflow_runner.py`
- `tests/unit/test_app_service.py`
- `tests/unit/test_desktop_shell.py`
- `.ai/tasks/TASK-107-safe-workflow-resume.md`

## Tests Added

- Workflow runner resume success from first unfinished step.
- Completed-step non-replay regression.
- Rejection for completed, malformed, unknown, incompatible, and
  non-resumable states.
- Duplicate resume protection.
- AppService typed resume result and safe failure projection.
- Desktop eligibility display, confirmation cancellation, confirmed resume,
  rejection safety, no-selection behavior, and double-click guard.

## Focused Test Commands And Results

- `python -m pytest -q tests\unit\test_workflow_runner.py` - `21 passed`
- `python -m pytest -q tests\unit\test_app_service.py -q` - passed
- `python -m pytest -q tests\unit\test_desktop_shell.py` - `77 passed`

## Behavior Test Results

- Behavior test 1 - successful safe resume:
  - Command:
    `python -m pytest -q tests\unit\test_workflow_runner.py::test_failed_run_resumes_from_first_unfinished_step_without_replaying_completed tests\unit\test_desktop_shell.py::test_workflow_resume_confirmation_acceptance_calls_appservice_once_and_refreshes`
  - Result: `2 passed in 0.40s`
  - Actual behavior: failed source run resumed from `three`/`write`, completed
    prior steps were not rerun, a distinct resumed run was selected in Desktop,
    source history remained visible, and copied/rendered output stayed safe.
- Behavior test 2 - rejection and recovery:
  - Command:
    `python -m pytest -q tests\unit\test_workflow_runner.py::test_resume_rejects_completed_malformed_unknown_and_incompatible_runs_safely tests\unit\test_workflow_runner.py::test_duplicate_resume_requests_create_at_most_one_resumed_attempt tests\unit\test_desktop_shell.py::test_workflow_resume_rejection_and_exceptions_are_safe_and_keep_view_usable`
  - Result: `3 passed in 0.40s`
  - Actual behavior: completed/malformed/incompatible runs were rejected
    safely, duplicate resume produced one started attempt and one safe conflict,
    and Desktop remained usable after a safe rejection.

## Final Verification

- Focused combined TASK-107 tests:
  - Command:
    `python -m pytest -q tests\unit\test_workflow_runner.py tests\unit\test_app_service.py tests\unit\test_desktop_shell.py`
  - Result: `192 passed in 1.01s`
- Final full pytest:
  - Command: `python -m pytest -q`
  - Result: `1764 passed, 2 skipped in 7.41s`
- Health check:
  - Command: `powershell -ExecutionPolicy Bypass -File scripts\health_check.ps1`
  - Result: `SUCCESS` with nested pytest `1764 passed, 2 skipped in 7.29s`
- Assistant smoke:
  - Command: `powershell -ExecutionPolicy Bypass -File scripts\assistant_smoke.ps1`
  - Result: `JARVIS ASSISTANT SMOKE: SUCCESS`
- Import probe:
  - Command:
    `python -c "from app.app_service import JarvisAppService; from app.desktop_shell import DesktopShellViewModel; from workflows.runner import WorkflowRunner; from workflows.contracts import WorkflowResumeResult; print('IMPORT_OK')"`
  - Result: `IMPORT_OK`
- Compileall:
  - Command:
    `python -m compileall ai app automation brain config core database dialogue ideas integrations interface language memory planner platform_adapters plugins scheduler security services tools users vision voice workflows`
  - Result: completed successfully.
- Whitespace check:
  - Command: `git diff --check`
  - Result: exit code 0, no whitespace errors. Git printed LF-to-CRLF
    working-copy warnings for touched files.

## Exclusions

- No workflow replay.
- No retry of completed steps.
- No arbitrary user-selected resume step.
- No workflow editing, deletion, export, or persistence redesign.
- No restart-persistent recovery.
- No voice command support for resume.

## Known Limitations

Resume is supported for the current in-memory workflow runner state. It does
not restore runs after application restart unless a future task adds and tests a
safe persistence model.

## Commit Hash

Pending user approval and commit.

## Push Result

Pending user approval and push.

## Final Repository State

Pre-commit state: working tree contains only TASK-107 scoped changes and the
TASK-107 task record. Commit and push are pending explicit approval.
