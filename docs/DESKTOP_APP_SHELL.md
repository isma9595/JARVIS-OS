# Desktop App Shell

TASK-077 adds read-only provider runtime status execution through the existing
AppService/CommandProcessor path. No provider settings UI, raw key input, live
validation, microphone, TTS, or network behavior is added.

## Why This Exists

TASK-070 adds the first safe desktop application shell prototype for JARVIS.
It prepares the project for a future Windows desktop app, dashboard UI,
command preview, command execution through AppService, registry/category
browsing, AI provider settings, secure key storage, installer/product mode,
and a future visual design system.

This is not the final UI, installer, or AI settings screen. TASK-071 adds the
secure key storage foundation, but this shell still has no key input fields.

## Relationship To AppService

The desktop shell uses `JarvisAppService` as its app-facing boundary.
The shell can show service status, list registry commands, preview command
risk, execute explicit user commands, show recent execution history, and show
application activity status, and show workflow run/step history only through
AppService. Workflow resume, when available, is also invoked only through
AppService. Workflow cancellation, when available for an active run, is also
invoked only through AppService.

TASK-073 adds versioned AppService contracts. The shell may read contract
status/cards through AppService, but TASK-073 adds no new screens or key input.

TASK-080 keeps intent resolution inside AppService. The shell does not call the
hybrid resolver directly; it only displays structured clarification questions
and options returned by AppService.

## Relationship To CommandRegistry

`CommandRegistry` remains the metadata source for categories, command lists,
risk levels, network flags, privacy flags, and app readiness.

## Why UI Must Not Call CommandProcessor Directly

The UI is not an execution authority. It must not bypass AppService or call
`ActionRouter` directly. AppService delegates execution to `CommandProcessor`
so the existing safety boundaries remain in charge.

## How To Run

```powershell
python run_desktop.py
```

`run.py` remains unchanged and is still the CLI entry point.

## Current Shell Can Do

- Show desktop/app service status.
- List command registry categories and commands.
- Preview command risk without execution.
- Execute explicit command text through AppService.
- Display a compact Activity Status panel with current idle/busy state,
  user-attention state, and bounded recent outcomes from AppService.
- Display a bounded, newest-first execution history list from AppService.
- Search the currently loaded safe history entries by plain text.
- Filter the currently loaded safe history entries by supported execution
  status categories.
- Refresh the execution history without restarting the shell.
- Show safe details for the selected history entry.
- Copy the selected history entry's safe user-facing summary/details.
- Display a read-only Workflow History panel from AppService workflow DTOs.
- Refresh the workflow run list manually.
- Select a workflow run and inspect its ordered step history.
- Copy selected workflow run details built from safe projected DTO fields.
- Resume an eligible selected workflow run after explicit confirmation through
  AppService.
- Cancel an eligible active workflow run after explicit confirmation through
  AppService.
- Display Russian clarification questions and options returned by AppService.
- Start one explicit one-shot voice request through AppService with the
  `Микрофон` button.
- Execute `диалог: <text>` through AppService/CommandProcessor as a safe
  conversational preview/plan.

## Current Shell Does Not Do

- No installer.
- No key input UI.
- No automatic provider use of secure key storage.
- No AI settings UI yet.
- No file reading.
- No screen capture.
- No automation.
- No network by default.
- No continuous listening or wake-word service.
- No history deletion, editing, replay, re-execution, file export, cloud sync,
  or remote history access.
- No workflow retry, replay, deletion, editing, export, workflow creation,
  arbitrary start-step selection, per-step cancellation, force-stop, rollback,
  or step execution controls.

## Safety

- No auto execution on startup.
- No secrets are stored or printed by the shell.
- No network by default.
- AI responses are not executed as commands.
- Preview does not execute target commands.
- Activity Status is read-only and uses `JarvisAppService.application_activity()`.
  The shell stores safe activity DTOs and formatted text only. Manual refresh
  and existing UI action completions update the panel; no Desktop-owned polling
  thread or execution orchestration is introduced.
- Execution history is read-only and uses the existing Execution Journal
  through AppService-safe DTOs.
- History search and status filtering run locally over the safe bounded DTOs
  already returned by AppService; they do not query journal internals.
- Copied history text is built from projected user-facing fields, not raw
  journal objects or tracebacks.
- Workflow history is read-only and uses
  `JarvisAppService.recent_workflow_runs()` and
  `JarvisAppService.workflow_run_history()`. The shell does not import
  `WorkflowRunner`, `ExecutionJournal`, workflow runtime objects, or mutable
  workflow collections.
- Workflow History supports empty, no-selection, no-steps, and safe error
  states. Manual refresh preserves the selected run when it still exists and
  clears stale details when it does not.
- Copied workflow text is built from projected run/step DTO fields only.
- Workflow resume availability comes from AppService/domain policy projection.
  The shell asks for explicit confirmation, calls
  `JarvisAppService.resume_workflow_run()`, prevents duplicate clicks while the
  request is in progress, refreshes history after the result, and never calls
  `WorkflowRunner` or `ExecutionJournal` directly.
- Workflow cancellation availability comes from AppService/domain policy
  projection. The shell asks for explicit confirmation, calls
  `JarvisAppService.cancel_workflow_run()`, prevents duplicate clicks while the
  request is in progress, refreshes history after the result, and never calls
  `WorkflowRunner`, `ExecutionCoordinator`, `ExecutionJournal`, cancellation
  tokens, or mutable workflow runtime state directly. Cancellation is
  cooperative; it does not promise immediate force termination or rollback.
  Non-cancellable active workflow steps are rejected by the AppService/domain
  projection, not by Desktop-specific step interpretation.
- Risky/network commands require explicit command text and Execute.
- Typed turns, explicit one-shot voice requests, and workflow resume use one
  lazy serialized non-daemon `DesktopInteractionWorker`; there is no separate
  voice thread and no backlog.
- Accepted work projects a busy state, disables Execute/microphone/resume, and
  enables one general cooperative-cancel control. Domain workflow cancellation
  remains a separate AppService-mediated action.
- Completion is published to one thread-safe slot and polled through
  main-thread `root.after` callbacks. The worker never calls Tk or mutates
  `DesktopShellState`.
- Early or explicitly acknowledged cooperative cancellation may be CANCELLED.
  If an already-started opaque AppService call returns normally after a late
  request, its completion remains COMPLETED and is presented once unless the
  window is closing.
- Close rejects new work, requests cooperative cancellation, waits without a
  long Tk-thread join, consumes any late completion without updating the user
  result, stops the worker safely, then destroys once. No forced thread/process
  termination is used, and ACTIVE conversation sessions remain resumable.
- Worker shutdown reaches STOPPED independently of Tk completion consumption;
  a pending completion remains available exactly once. If mainloop has already
  exited, the fallback joins the non-daemon worker and consumes that completion
  without state, refresh, render, or widget apply. Busy close immediately
  projects the worker snapshot so the general cancel button is disabled after
  cancellation has already been requested.
- The shell does not construct Vosk, microphone, provider, credential, or
  command-processing internals.
- TASK-078 shell messages are Russian-first by default and preserve recognized
  Cyrillic text.
- TASK-079 shell messages keep the original recognition visible and, when a
  safe voice normalization changes the command candidate, also show
  `Нормализовано: ...`.
- Raw microphone audio stays inside the local capture/recognition boundary;
  only recognized text can continue through AppService.
- Conversational preview does not call providers, network, browser, audio, or
  file/OS automation.
- Clarification does not count as confirmation for risky actions; selected
  clarification options still go through AppService and existing safety checks.

## Future

- AI Provider Settings UI.
- Secure Settings & API Key Storage.
- Windows Installer Foundation.
- Visual Design System.
- Future user-selected language settings through the application language
  boundary. Full multilingual UI is not implemented yet.
# Audio Lifecycle

The desktop shell can consume the AppService audio lifecycle status card for future voice status UI. TASK-074 does not add microphone buttons, TTS controls, new windows, or real audio actions.
## Vertical Integration

TASK-075 verifies that `DesktopShellViewModel` can build and preview safe
commands through AppService without opening a GUI, starting audio, or using
network.
