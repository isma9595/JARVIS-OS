# TASK-109 - Workflow Lifecycle Hardening

## Objective

Resolve the bounded workflow milestone audit findings after TASK-105 through
TASK-108 and close the current workflow subsystem milestone.

## Starting Baseline

- Branch: `main`
- Starting HEAD: `14dd035f7b49fe5dd57dc8e801361d6f846d76f2`
- Starting `origin/main`: `14dd035f7b49fe5dd57dc8e801361d6f846d76f2`
- Starting status: clean
- Latest workflow feature commit: `14dd035 Add workflow cancellation UX`

## Scope

- Enforce `WorkflowStepDefinition.cancellable` in central cancellation
  eligibility and mutation paths.
- Add focused regression coverage for non-cancellable active steps, malformed
  active-step cancellation, true concurrent resume requests, resume launch
  cleanup, and resume-vs-cancel ownership.
- Document the current `WorkflowRunner` lock-held step execution invariant.
- Mark the workflow subsystem milestone closed.

## Exclusions

- No new workflow feature.
- No live status or progress UI.
- No persistence recovery.
- No workflow execution redesign.
- No new cancellation engine.
- No provider, planner, voice, microphone, TTS, or unrelated subsystem changes.
- No TASK-110 implementation.

## Architecture Inspected

- `AGENTS.md`
- `workflows/contracts.py`
- `workflows/runner.py`
- `core/execution_coordinator.py`
- `core/execution_journal.py`
- `app/app_service.py`
- `app/desktop_shell.py`
- workflow runner, AppService, Desktop Shell, coordinator, and journal tests
- TASK-105 through TASK-108 task records and architecture documentation

## Implemented Hardening

- Added a typed `non_cancellable_step` cancellation rejection reason.
- Central cancellation eligibility now safely identifies the active step and
  rejects cancellation when `WorkflowStepDefinition.cancellable=False`.
- Malformed active-step state fails closed without signalling cancellation.
- The cancellation mutation path reuses the same central eligibility check
  before reservation, coordinator signalling, or journal metadata writes.
- Desktop remains AppService-driven and does not interpret step cancellability.

## Resume And Cancellation Ownership

Resume duplicate protection remains owned by `WorkflowRunner` under its runner
lock. The new true-concurrency regression proves concurrent resume requests for
the same failed source create at most one resumed attempt and leave no active
resume reservation.

Cancellation continues to target only an active run id. A failed historical
source run is not a cancellation target after a resumed attempt exists; the
active resumed attempt is the cancellable target and its history remains
distinct from the source run.

## Locking Decision

TASK-109 accepts the current `WorkflowRunner` invariant: runner state is
serialized by the runner lock during `step.action(...)`. History and eligibility
reads may wait for the active step boundary. This is documented as a current
invariant rather than refactored in this task because narrowing the lock would
change concurrency semantics and requires a separate approved hardening task.

## Files Changed

- `README.md`
- `docs/APPSERVICE_CONTRACTS.md`
- `docs/ARCHITECTURE.md`
- `docs/DESKTOP_APP_SHELL.md`
- `docs/JARVIS_APP_SERVICE.md`
- `tests/unit/test_app_service.py`
- `tests/unit/test_desktop_shell.py`
- `tests/unit/test_workflow_runner.py`
- `workflows/contracts.py`
- `workflows/runner.py`
- `.ai/tasks/TASK-109-workflow-lifecycle-hardening.md`

## Focused Tests

- `python -m pytest -q tests/unit/test_workflow_runner.py -k "non_cancellable or malformed_active_step or concurrent_resume or launch_failure or resume_attempt_is_cancel_target"`
  - Result: `5 passed, 24 deselected`
- `python -m pytest -q tests/unit/test_app_service.py -k "workflow_cancellation"`
  - Result: `2 passed, 96 deselected`
- `python -m pytest -q tests/unit/test_desktop_shell.py -k "workflow_cancellation"`
  - Result: `6 passed, 78 deselected`
- `python -m pytest -q tests/unit/test_workflow_runner.py`
  - Result: `29 passed`
- `python -m pytest -q tests/unit/test_workflow_runner.py`
  - Result after removing an unused test import: `29 passed`
- `python -m pytest -q tests/unit/test_app_service.py`
  - Result: `98 passed`
- `python -m pytest -q tests/unit/test_desktop_shell.py`
  - Result: `84 passed`
- `python -m pytest -q tests/unit/test_execution_coordinator.py tests/unit/test_execution_journal.py`
  - Result: `8 passed`

TASK-109 behavior/regression selections:

- `python -m pytest -q tests/unit/test_workflow_runner.py::test_non_cancellable_active_step_rejects_cancellation_without_side_effects tests/unit/test_workflow_runner.py::test_malformed_active_step_state_rejects_cancellation_without_signal tests/unit/test_app_service.py::test_workflow_cancellation_non_cancellable_reason_stays_typed_and_safe tests/unit/test_desktop_shell.py::test_workflow_cancellation_non_cancellable_projection_disables_cancel`
  - Result: `4 passed`
- `python -m pytest -q tests/unit/test_workflow_runner.py::test_concurrent_resume_requests_create_one_resumed_attempt_and_cleanup tests/unit/test_workflow_runner.py::test_resume_launch_failure_releases_reservation_for_later_attempt tests/unit/test_workflow_runner.py::test_resume_attempt_is_cancel_target_and_source_history_stays_distinct`
  - Result: `3 passed`

## Final Verification

- Full pytest:
  - Command: `python -m pytest -q`
  - Result: `1783 passed, 2 skipped in 8.76s`
- Final full pytest after the last test-file edit:
  - Command: `python -m pytest -q`
  - Result: `1783 passed, 2 skipped in 7.71s`
- Health check:
  - Command: `powershell -ExecutionPolicy Bypass -File scripts\health_check.ps1`
  - Result: `Result: SUCCESS`
  - The health script also ran pytest internally and reported
    `1783 passed, 2 skipped in 7.66s`.
- Assistant smoke check:
  - Command: `powershell -ExecutionPolicy Bypass -File scripts\assistant_smoke.ps1`
  - Result: `JARVIS ASSISTANT SMOKE: SUCCESS`
- Key import probe:
  - Command: `python -c "from app.app_service import JarvisAppService; from app.desktop_shell import DesktopShellViewModel; from workflows.runner import WorkflowRunner; from workflows.contracts import WorkflowCancellationRejectionReason, WorkflowResumeResult, WorkflowRunHistory; print('IMPORT_OK')"`
  - Result: `IMPORT_OK`
- Source compileall:
  - Command: `python -m compileall ai app automation brain config core database dialogue ideas integrations interface language memory planner platform_adapters plugins scheduler security services tools users vision voice workflows`
  - Result: completed successfully.
- Whitespace check:
  - Command: `git diff --check`
  - Result: exit code 0. Git reported existing line-ending conversion warnings
    for touched text/source files, but no whitespace errors.

## Milestone Closure

The current workflow subsystem milestone includes:

- TASK-105 - Workflow Run State & Step History
- TASK-106 - Desktop Workflow History Viewer
- TASK-107 - Safe Workflow Resume
- TASK-108 - Workflow Cancellation UX
- TASK-109 - Workflow Lifecycle Hardening
- milestone audit completed

TASK-109 formally closes this workflow subsystem milestone. Future workflow
expansion requires a new explicitly approved milestone.

## Completion Status

Complete pending commit and push approval.
