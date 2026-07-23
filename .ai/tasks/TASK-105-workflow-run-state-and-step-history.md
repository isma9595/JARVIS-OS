# TASK-105 - Workflow Run State and Step History

## Context

TASK-103 and TASK-104 added a Desktop execution history viewer over
AppService-safe execution-history DTOs. TASK-105 adds a runtime/service
foundation for workflow run and step inspection without adding Desktop UI.

## Objective

Introduce stable, safe, read-only workflow run state and ordered step history
for current workflow executions.

## Starting Baseline

- Expected baseline: `3ec191b667a37b6f508bde84c8043f68344b4587`
- Actual starting branch: `main`
- Actual starting HEAD: `3ec191b667a37b6f508bde84c8043f68344b4587`
- Actual starting `origin/main`: `3ec191b667a37b6f508bde84c8043f68344b4587`
- Starting working tree: clean

## Repository Evidence Reviewed

- `workflows/contracts.py`
- `workflows/runner.py`
- `workflows/document_review.py`
- `planner/contracts.py`
- `planner/multi_step_planner.py`
- `planner/plan_executor.py`
- `core/execution_coordinator.py`
- `core/execution_journal.py`
- `app/app_service.py`
- `app/app_contracts.py`
- `tests/unit/test_workflow_runner.py`
- `tests/unit/test_app_service.py`
- workflow-related integration tests under `tests/integration/`
- TASK-103 and TASK-104 documentation and AppService history conventions
- `docs/ARCHITECTURE.md`
- `docs/JARVIS_APP_SERVICE.md`
- `docs/APPSERVICE_CONTRACTS.md`

## Existing Workflow Behavior

The current reusable `WorkflowRunner` executes a declared linear sequence of
`WorkflowExecutableStep` objects. It already tracks aggregate run status,
current step, completed step IDs, confirmation pauses, cancellation, policy
denial, and operation lifecycle through `ExecutionCoordinator` and
`ExecutionJournal`. It did not previously expose a stable detached run/step
history DTO suitable for future UI inspection.

## Implemented Run-State Model

TASK-105 adds `WorkflowRunHistory` and `WorkflowRunHistoryState` in
`workflows/contracts.py`.

Supported projected run states:

- `pending`
- `running`
- `waiting_for_confirmation`
- `completed`
- `failed`
- `cancelled`
- `blocked`
- `unknown`

The run DTO includes stable run/operation identifiers, workflow id/name,
safe objective summary, created/started/completed timestamps where available,
total/completed step counts, active step, safe result/failure summaries,
cancellation and confirmation flags, safe metadata, and detached step history.

## Implemented Step-State Model

TASK-105 adds `WorkflowStepHistory` and `WorkflowStepHistoryState`.

Supported projected step states:

- `pending`
- `running`
- `waiting_for_confirmation`
- `completed`
- `failed`
- `cancelled`
- `skipped`
- `blocked`
- `unknown`

Step DTOs include stable step id, index, safe display name, operation type,
timestamps where available, safe result/error summaries, confirmation and
preview flags, and safe metadata.

## Source of Truth

The source of truth remains the existing in-memory `WorkflowRunner` state and
existing `ExecutionJournal` operation metadata. No second unrelated workflow
history store, database, schema migration, or persistence redesign was added.

## Journal Integration

The runner mirrors safe workflow metadata into the existing journal operation
metadata where cleanly available:

- `workflow_run_id`
- `workflow_id`
- `workflow_state`
- `workflow_current_step_id`
- `workflow_total_steps`
- `workflow_completed_steps`

This preserves existing journal compatibility and does not require Desktop
execution history to understand workflow internals.

## Safe Projection Boundary

The new read-only projection boundary is:

- `WorkflowRunner.run_history(operation_id)`
- `WorkflowRunner.recent_run_histories(limit)`
- `JarvisAppService.workflow_run_history(run_id)`
- `JarvisAppService.recent_workflow_runs(limit)`

AppService enforces a default recent-run limit of 25 and a maximum of 100.

DTOs are frozen dataclasses and step collections are tuples. Metadata is
sanitized and mapping-protected. Raw exceptions, tracebacks, internal runner
objects, mutable planner structures, secrets, local paths, and policy internals
are not returned.

## Lifecycle Transitions

Covered lifecycle behavior:

- created/pending to running
- running to completed
- running to failed
- running to cancelled
- running to waiting_for_confirmation
- waiting_for_confirmation to running and completed
- policy denial projected as blocked

Pending later steps remain pending after failure, cancellation, or confirmation
pause. No resume/retry/replay behavior was added beyond the pre-existing
confirmation resume behavior.

## Limitations

- Workflow history is in-memory and process-local.
- No Desktop workflow viewer exists in TASK-105.
- No workflow persistence, resume, retry, replay, deletion, editing, or export
  was added.
- Empty executable workflow definitions remain rejected by `WorkflowRunner`;
  the DTO model itself safely represents empty step history.

## Out Of Scope

- Desktop Workflow Viewer
- workflow resume beyond existing confirmation resume
- retry, replay, deletion, editing, export, persistence redesign
- planner redesign
- CommandProcessor refactoring
- policy redesign
- voice, microphone, or TTS changes

## Changed Files

- `README.md`
- `app/__init__.py`
- `app/app_service.py`
- `docs/APPSERVICE_CONTRACTS.md`
- `docs/ARCHITECTURE.md`
- `docs/JARVIS_APP_SERVICE.md`
- `tests/unit/test_app_service.py`
- `tests/unit/test_workflow_runner.py`
- `workflows/contracts.py`
- `workflows/runner.py`
- `.ai/tasks/TASK-105-workflow-run-state-and-step-history.md`

## Focused Tests

- `python -m pytest -q tests\unit\test_workflow_runner.py tests\unit\test_app_service.py`
  -> `105 passed in 1.55s`.
- `python -m pytest -q tests\unit\test_workflow_runner.py tests\unit\test_app_service.py tests\unit\test_execution_journal.py tests\unit\test_execution_coordinator.py tests\integration\test_task_084_workflow_runner.py tests\integration\test_task_083_document_review_workflow`
  -> `131 passed in 1.33s`.
- After the running-state characterization and safe text renderer were added:
  `python -m pytest -q tests\unit\test_workflow_runner.py tests\unit\test_app_service.py tests\unit\test_execution_journal.py tests\unit\test_execution_coordinator.py tests\integration\test_task_084_workflow_runner.py tests\integration\test_task_083_document_review_workflow`
  -> `132 passed in 1.23s`.
- Additional focused TASK-105 regression tests requested before commit:
  - unknown or malformed workflow/step state maps to safe fallback and does not
    expose raw internals;
  - previously returned workflow history DTOs remain detached from later
    runtime mutation.
  - `python -m pytest -q tests\unit\test_workflow_runner.py`
    -> `17 passed in 0.14s`.

## Behavior Tests

Behavior test 1 - successful multi-step workflow:

- Setup: three deterministic workflow steps through `WorkflowRunner`.
- Actual run id: `op-8f84828778c1411fa4d2eca421555d5f`
- Actual state: `completed`
- Actual step order: `one`, `two`, `three`
- Actual count: `3/3`
- Result: PASS

Behavior test 2 - failure in middle step:

- Setup: three deterministic workflow steps through `WorkflowRunner`; step two
  raised an internal exception containing `Traceback`, `RuntimeError`, a local
  path, and a mock secret.
- Actual state: `failed`
- Actual step states: `completed`, `failed`, `pending`
- Actual safe error summary: `Шаг workflow безопасно завершился ошибкой.`
- Sanitization: traceback, raw exception text, local path, and mock secret were
  absent from the projected DTO text.
- Result: PASS

## Final Verification Results

- Full pytest:
  - `python -m pytest -q` -> `1737 passed, 2 skipped in 11.50s`.
- Final full pytest after the two additional TASK-105 regression tests:
  - `python -m pytest -q` -> `1739 passed, 2 skipped in 9.46s`.
- Strict deprecation-warning pytest:
  - `python -W error::DeprecationWarning -m pytest -q`
    -> `1737 passed, 2 skipped in 9.24s`.
- Health check:
  - `powershell -ExecutionPolicy Bypass -File scripts\health_check.ps1`
    -> `Result: SUCCESS`, `Failures: 0`, `Warnings: 0`, embedded pytest
    `1737 passed, 2 skipped in 8.80s`.
- Assistant smoke:
  - `powershell -ExecutionPolicy Bypass -File scripts\assistant_smoke.ps1`
    -> `1 passed in 0.30s`, `JARVIS ASSISTANT SMOKE: SUCCESS`.
- Key import probe:
  - `python -c "from app import JarvisAppService, DesktopShellViewModel, AppExecutionHistoryEntry, AppExecutionHistoryResult, WorkflowHistoryResult, WorkflowRunHistory, WorkflowStepHistory; from core.execution_journal import ExecutionJournal, ExecutionOperation, ExecutionStatus; from core.execution_coordinator import ExecutionCoordinator; from core.command_processor import CommandProcessor; from core.command_resolution_service import CommandResolutionService; from core.policy_boundary import PolicyDecisionBoundary; from planner import MultiStepPlanner; from workflows.runner import WorkflowRunner; from workflows.contracts import WorkflowRunHistoryState, WorkflowStepHistoryState; from platform_adapters.local_filesystem import WindowsLocalFileSystemAdapter; from memory import LocalMemoryManager; from voice.one_shot_vosk_real_recognition import OneShotVoskRealRecognition; from voice.windows_local_tts_backend import WindowsLocalSpeechSynthesisBackend; print('KEY IMPORT PROBE: SUCCESS')"`
    -> `KEY IMPORT PROBE: SUCCESS`.
- Source compilation:
  - `python -m compileall ai app automation brain config core database dialogue ideas integrations interface language memory planner platform_adapters plugins scheduler security services tools users vision voice workflows`
    -> exit 0.
- Whitespace check:
  - `git diff --check` -> exit 0. Git printed LF-to-CRLF working-copy warnings
    for touched files and no whitespace errors.

## Completion Status

Implementation and verification passed. The task is complete after the
documentation/code commit is created, pushed to `origin/main`, and final clean
repository checks pass.
