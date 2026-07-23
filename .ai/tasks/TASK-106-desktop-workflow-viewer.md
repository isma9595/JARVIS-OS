# TASK-106 - Desktop Workflow Viewer

## Objective

Add a read-only Desktop Workflow History panel that lets the user inspect
recent workflow runs and ordered step history through the safe workflow history
foundation from TASK-105.

## Scope

- Desktop presentation and Desktop-facing orchestration only.
- Use `JarvisAppService.recent_workflow_runs()`.
- Use `JarvisAppService.workflow_run_history()`.
- Do not access `WorkflowRunner`, `ExecutionJournal`, workflow runtime objects,
  or mutable workflow collections from Desktop code.
- Do not add resume, retry, replay, cancel, delete, edit, export, workflow
  creation, or step execution controls.

## Inspected Architecture

- `AGENTS.md`
- `app/desktop_shell.py`
- `tests/unit/test_desktop_shell.py`
- `workflows/contracts.py`
- `app/app_service.py`
- `docs/DESKTOP_APP_SHELL.md`
- `docs/ARCHITECTURE.md`
- `docs/JARVIS_APP_SERVICE.md`
- `README.md`

The Desktop Shell uses `DesktopShellViewModel` for deterministic UI state and
Tkinter rendering for the concrete shell. Execution history already uses a
list/detail panel with refresh, selection, safe copy, empty/error states, and
view-model tests. TASK-106 follows that pattern for workflow history.

## Files Changed

- `README.md`
- `app/desktop_shell.py`
- `docs/ARCHITECTURE.md`
- `docs/DESKTOP_APP_SHELL.md`
- `docs/JARVIS_APP_SERVICE.md`
- `tests/unit/test_desktop_shell.py`
- `.ai/tasks/TASK-106-desktop-workflow-viewer.md`

## UI Behavior

- Adds a compact `Workflow History` panel below execution history.
- Displays recent workflow runs from AppService DTOs.
- Selecting a workflow run loads details through AppService.
- Details include safe run summary and ordered step history.
- Manual refresh reloads the recent run list.
- Refresh preserves selection when the selected run still exists.
- Refresh selects the current first run when the previous run disappears from a
  non-empty list.
- Refresh clears selection and shows a neutral detail state when no runs exist.
- Detail loading failure clears stale step details and shows a safe error.
- Copy Selected copies only projected safe run/step details.

## Architecture Boundaries

Desktop dependency direction:

```text
DesktopShellViewModel / Tk UI
    -> JarvisAppService
        -> WorkflowHistoryResult / WorkflowRunHistory / WorkflowStepHistory
```

Desktop code does not import or call `WorkflowRunner`, `ExecutionJournal`,
document-review runner internals, or mutable workflow execution collections.

## Tests Added

Focused Desktop tests cover:

- recent workflow runs rendering through AppService DTOs;
- selected run detail loading;
- ordered step history display;
- safe projected state labels, including `unknown`;
- empty run list;
- no-step run details;
- safe list failure;
- safe detail failure without stale details;
- refresh preserving selection and reloading details;
- refresh clearing selection when no runs remain;
- selection replacing old details;
- safe copy;
- copy unavailable without selection;
- Desktop source avoiding direct workflow runtime/journal dependencies.

TASK-106 regression tests cover:

- stale detail clearing when selecting Run B and detail loading fails;
- refresh selection consistency, including preserved selection, updated detail,
  no duplicate rows/steps, and disappearance handling.

## Focused Test Commands And Results

- `python -m pytest -q tests\unit\test_desktop_shell.py`
  - first run failed because `history_entry()` was accidentally broken while
    adding workflow test helpers, and workflow detail copy remained available
    after detail load failure.
  - Small TASK-106-scoped fixes restored `history_entry()`, disabled workflow
    copy when detail load failed, and added the safe objective line to workflow
    details.
- `python -m pytest -q tests\unit\test_desktop_shell.py`
  -> `72 passed in 0.94s`.
- `python -m pytest -q tests\unit\test_app_service.py tests\unit\test_workflow_runner.py`
  -> `108 passed in 1.64s`.

## Behavior Test Results

Behavior test 1 - Normal workflow inspection:

- Setup: `DesktopShellViewModel` with fake AppService returning two
  `WorkflowRunHistory` DTOs.
- Actions: open Workflow History, select first run, inspect steps, select
  second run, copy selected details.
- Actual runs: `wf-alpha`, `wf-beta`.
- Actual selected run after second selection: `wf-beta`.
- First run steps were visible before switching and absent after selecting the
  second run.
- Copied content began with `Workflow Run`, `run id: wf-beta`, safe workflow
  label, and state.
- Result: PASS.

Behavior test 2 - Empty, error, and refresh transitions:

- Setup: `DesktopShellViewModel` with fake AppService.
- Actions: initial empty load, refresh to populated data, preserve selection
  across refresh, refresh after selected run disappears, clear to empty,
  simulate AppService error, recover on later successful refresh.
- Actual checks: empty state true, populated selection true, preserved updated
  detail true, disappearance transition true, cleared empty state true, safe
  error true, recovery true.
- Result: PASS.

## Final Verification Results

- Final full pytest:
  - `python -m pytest -q` -> `1752 passed, 2 skipped in 12.02s`.
- Health check:
  - `powershell -ExecutionPolicy Bypass -File scripts\health_check.ps1`
    -> embedded pytest `1752 passed, 2 skipped in 13.50s`, `Failures: 0`,
    `Warnings: 0`, `Result: SUCCESS`.
- Assistant smoke:
  - `powershell -ExecutionPolicy Bypass -File scripts\assistant_smoke.ps1`
    -> `1 passed in 0.52s`, `JARVIS ASSISTANT SMOKE: SUCCESS`.
- Key import probe:
  - `python -c "from app import JarvisAppService, DesktopShellViewModel, AppExecutionHistoryEntry, AppExecutionHistoryResult, WorkflowHistoryResult, WorkflowRunHistory, WorkflowStepHistory; from app.desktop_shell import JarvisDesktopShell; from workflows.contracts import WorkflowRunHistoryState, WorkflowStepHistoryState; print('KEY IMPORT PROBE: SUCCESS')"`
    -> `KEY IMPORT PROBE: SUCCESS`.
- Source compilation:
  - `python -m compileall ai app automation brain config core database dialogue ideas integrations interface language memory planner platform_adapters plugins scheduler security services tools users vision voice workflows`
    -> exit 0.
- Whitespace check:
  - `git diff --check` -> exit 0. Git printed LF-to-CRLF working-copy warnings
    for touched files and no whitespace errors.

## Exclusions

- No workflow resume, retry, replay, cancel, delete, edit, reorder, export,
  creation, or mutation controls.
- No Desktop direct access to workflow runner or journal internals.
- No workflow persistence redesign.
- No network, microphone, TTS, or provider behavior changes.

## Commit Hash

Pending explicit approval and commit.

## Push Result

Pending explicit approval and push.

## Final Repository State

Pending final verification, approval, commit, push, and final state checks.
