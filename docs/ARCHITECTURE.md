# JARVIS OS Architecture

Status: current implementation after TASK-101, aligned by TASK-102.

JARVIS OS is currently a Windows-first assistant application. It includes a CLI,
a Tkinter Desktop Shell prototype, an AppService boundary for application
clients, deterministic command handling, local memory, local voice and TTS
boundaries, provider adapters behind explicit gates, a planner, and a safe local
TXT document-review workflow.

This document describes the architecture that exists now. It does not describe
future installer, mobile, admin/support, wake-word, always-on listening, or
portable OS-like capabilities as implemented.

## Current Architecture

Primary entry points:

- `run.py`: CLI runtime entry point using `JARVISKernel` and
  `CommandProcessor`.
- `run_desktop.py`: Desktop Shell launcher.
- `app/desktop_shell.py`: Tkinter UI shell and `DesktopShellViewModel`.

Primary dependency direction:

```text
Desktop Shell -> JarvisAppService -> application DTOs and boundaries
JarvisAppService -> Planner / Workflow Runner / Policy / Journal / Memory /
Voice / Provider Runtime / CommandProcessor where needed
CommandProcessor -> CommandResolutionService / CommandRegistry / subsystem
handlers / ActionRouter fallback
```

The UI is not an execution authority. Desktop Shell code uses
`JarvisAppService` for status, command listing, preview, explicit execution,
clarification display, recent execution history, workflow history inspection,
application activity status, and one-shot voice requests. It does not call
`CommandProcessor`, `ActionRouter`, provider adapters, memory storage, or
filesystem adapters directly.

## AppService

`JarvisAppService` in `app/app_service.py` is the application-facing boundary
for UI clients. It owns public result projection into DTOs from
`app/app_contracts.py`, safe text rendering, preview behavior, execution
coordination, and composition of the current application subsystems.

Major responsibilities already extracted from AppService include planner
orchestration in `app/services/planner_command_service.py`, reusable workflow
execution in `workflows/runner.py`, policy decisions in
`core/policy_boundary.py`, operation coordination in
`core/execution_coordinator.py`, journal storage in `core/execution_journal.py`,
and platform filesystem access through `platform_adapters/`.

AppService still retains significant responsibilities, including status and
contract projection, memory command handling, language preference commands,
document-review workflow composition, direct state-change coordination, voice
request projection, local TTS metadata projection, provider runtime status, and
legacy execution delegation. This is intentional current state, not completed
decomposition.

## Public DTO and Projection Boundary

`app/app_contracts.py` contains versioned UI-safe contract dataclasses such as
`AppCommandPreview`, `AppCommandResult`, `AppExecutionContract`,
`AppVoiceRequestResult`, `AppContractStatus`, `AppStatusCard`,
`AppCommandCard`, and `AppContractManifest`.

Contract objects use deterministic `to_dict()` projection and safe text helpers.
They are the public application-facing shape for Desktop Shell and future UI
clients. Internal Python objects, provider objects, credentials, microphone
streams, and filesystem handles are not public contracts.

## Preview Versus Execution

Preview is side-effect free. AppService preview paths inspect registry,
planner, document, and memory metadata as supported by the current code. Preview
does not execute commands, register operations, mutate memory/profile/language,
start microphone capture, synthesize speech, call providers, use network, or
write files.

Execution is explicit. `execute_command()` and `execute_contract()` route
through AppService, resolve intent, evaluate policy where applicable, coordinate
operations where applicable, and either execute, deny, fail safely, or pause for
clarification or confirmation.

## Confirmation and Denial Flow

`PolicyDecisionBoundary` in `core/policy_boundary.py` evaluates metadata-only
`PolicyRequest` objects and returns `PolicyDecision` values such as allow,
deny, or confirmation-required. It does not execute commands and does not call
providers, audio, GUI, or credential stores.

`ExecutionCoordinator` creates operation IDs, idempotency keys, request
fingerprints, cancellation tokens, and operation lifecycle transitions.
`ExecutionJournal` stores bounded in-memory `ExecutionOperation` records with
safe metadata. AppService exposes recent history through detached
`AppExecutionHistoryEntry` DTOs. Desktop Shell reads those projections only; it
does not mutate, replay, delete, or inspect journal storage internals. Desktop
history search and status filtering are local presentation behavior over the
bounded DTO collection already loaded from AppService.

Workflow run history uses the existing in-memory workflow runner state and safe
journal metadata as its source. `WorkflowRunner` projects read-only
`WorkflowRunHistory` and `WorkflowStepHistory` DTOs with stable public states,
ordered step history, progress counts, timestamps where the runtime has them,
and safe result or failure summaries. This is a runtime/service contract for
inspection; TASK-105 does not add workflow persistence, replay, retry,
deletion, export, or Desktop workflow UI.

Desktop Shell now renders a read-only Workflow History panel through
`JarvisAppService.recent_workflow_runs()` and
`JarvisAppService.workflow_run_history()`. The panel stores only safe DTOs for
rendering, supports manual refresh, selection, ordered step inspection, empty
and safe error states, and safe copy. It does not import runner/journal
internals.

TASK-107 adds an explicit safe workflow resume action for eligible selected
runs. Desktop still does not control `WorkflowRunner` or mutable runtime state;
it reads AppService-projected eligibility, asks for user confirmation, then
calls `JarvisAppService.resume_workflow_run(run_id)`. Resume eligibility is
centralized in the workflow/AppService boundary, not inferred by the UI.
Eligible resume creates a distinct linked attempt, validates the current
workflow definition fingerprint against the recorded run, starts at the first
safe unfinished step, and preserves completed steps without replaying them.
Ineligible, duplicate, incompatible, malformed, or launch-failure cases return
safe typed rejection results.

TASK-108 adds explicit safe workflow cancellation for eligible active selected
runs. Desktop reads AppService-projected cancellation eligibility, asks for user
confirmation, then calls `JarvisAppService.cancel_workflow_run(run_id)`.
Cancellation eligibility and duplicate-request protection live in the
workflow/AppService boundary, not in the UI. Cancellation is cooperative: it
signals the existing operation cancellation token where supported, preserves
completed steps, does not roll back side effects, and prevents later workflow
steps from starting after the request is accepted. Completed, inactive failed,
already-cancelled, malformed, unknown, or ownership-missing runs return safe
typed rejection results.

TASK-109 hardens the same workflow lifecycle boundary. The central
`WorkflowRunner` cancellation policy now honors
`WorkflowStepDefinition.cancellable`; a non-cancellable active step rejects
cancellation safely before any coordinator signal, cancellation reservation, or
cancellation journal metadata is written. Resume duplicate protection is covered
under true concurrency, and cancellation targets the active resumed attempt
rather than its historical source run.

TASK-110 adds application-level activity status without reopening the workflow
subsystem. `ApplicationActivityTracker` in `app/activity.py` is a projection
tracker below AppService; it consumes bounded immutable `ExecutionOperation`
snapshots from `ExecutionCoordinator` and returns safe
`ApplicationActivitySnapshotDto` DTOs. It is not a second coordinator, event
bus, telemetry system, or execution authority. The current model is
foreground-only: the most recently observed active user-visible operation is
`current`, while completed, failed, rejected, and cancelled operations are kept
as bounded recent outcomes.

Activity states are stable public values: `idle`, `starting`, `running`,
`waiting_for_user`, `cancellation_requested`, `succeeded`, `failed`,
`rejected`, `cancelled`, and `unknown`. Terminal states do not regress to
active in the projection; duplicate terminal updates are idempotent; stale
completion for an older operation does not replace a newer current operation.
Desktop reads this through `JarvisAppService.application_activity()` and never
imports coordinator, journal, workflow, planner, provider, token, thread, or
mutable runtime objects for activity status.

Confirmation-required operations pause before side effects. Repeated execution
is not treated as confirmation. Cancellation and idempotency are tracked through
the same operation boundary.

## Planner

The planner lives in `planner/`:

- `MultiStepPlanner` parses bounded deterministic plans and maintains a
  session-only active plan.
- `PlanExecutor` executes registered capabilities through workflow-style
  progression.
- `PlannerCapabilityRegistry` stores explicit `PlanCapability` registrations.
- `planner/contracts.py` defines public immutable planner DTOs and status
  enums.

Planner snapshots expose safe plan and step metadata, including active step
risk, side effect, and confirmation requirement. Planner state is session-only
and is not persisted across process restarts.

AppService delegates planner command orchestration to
`PlannerCommandService`. Planner capabilities remain explicit and bounded; the
planner does not execute arbitrary reflected AppService methods.

## Workflow Runner and Document Workflow

`workflows/runner.py` provides a reusable linear `WorkflowRunner` with
workflow-step status, cancellation, confirmation pauses, operation lifecycle,
safe snapshots, and read-only run/step history projection. The history model
normalizes current internal statuses into stable public states such as
`pending`, `running`, `waiting_for_confirmation`, `completed`, `failed`,
`cancelled`, and `blocked`; step history similarly exposes `pending`,
`running`, `waiting_for_confirmation`, `completed`, `failed`, `cancelled`,
`skipped`, and `blocked` where supported by current runtime behavior.

The runner keeps this history in memory alongside the active workflow run and
projects detached DTOs rather than returning mutable runner objects. It mirrors
safe workflow state metadata to the existing `ExecutionJournal` where possible,
without changing journal storage or requiring Desktop history to understand
workflow internals.

The runner also owns the TASK-107 resume safety model for the current in-memory
workflow runs. Resume does not redesign workflow storage, does not persist
recovery across application restarts, and does not expose arbitrary replay or
user-selected step execution. Compatibility is checked using stable workflow
step identity/order metadata captured with the run. A resumed attempt has its
own operation/run id and safe metadata linking it to the source run.

The runner also owns the TASK-108 cancellation safety model for current active
workflow runs. Cancellation does not introduce forced thread/process
termination, rollback, arbitrary step cancellation, or workflow deletion.
Accepted cancellation records safe cancellation metadata through the existing
journal/history projection and leaves source/resumed run identities distinct.
TASK-109 closes the current workflow subsystem milestone after bounded lifecycle
hardening. The current runner invariant is that workflow state is serialized by
the runner lock during `step.action(...)`; history and eligibility reads may
wait for an active step boundary. That lock behavior is documented as an
accepted current invariant, not a new workflow feature. Future workflow
expansion requires a new explicitly approved milestone.

`workflows/document_review.py` implements the current local TXT document-review
workflow. The workflow validates a source file, reads bounded bytes, analyzes
text, prepares a reviewed output, writes a new sibling output only after
confirmation, verifies output, and verifies that the source remains unchanged.

The document workflow uses the local filesystem adapter boundary rather than
directly exposing raw filesystem operations to the UI.

## Command Resolution and CommandProcessor

`CommandResolutionService` in `core/command_resolution_service.py` owns
deterministic recognition for extracted command families. It normalizes input,
matches exact and prefix groups supplied by `CommandProcessor`, projects safe
arguments, and returns immutable `CommandResolution` data. It is read-only and
does not execute handlers.

`CommandProcessor` in `core/command_processor.py` remains the public legacy text
execution facade. It owns `process()`, command-id dispatch, handler invocation,
state mutation for legacy paths, provider and voice manager calls, response
construction, response history, confirmation state, policy checks, and
`ActionRouter` fallback behavior.

After TASK-094 and TASK-095, many recognition branches were moved out of
`process()`, but `CommandProcessor` is still a large transitional orchestrator.
Further decomposition is future work.

## Memory

`memory/memory_manager.py` provides local JSON-backed memory through
`LocalMemoryManager`. `memory/conversation_context.py` provides bounded
session-only conversation context.

AppService supports direct memory remember, recall, list, forget, and
confirmation-protected forget-all flows. Preview recognition for supported
memory commands is non-mutating. Direct memory state changes are coordinated
through operation metadata and journal boundaries where supported by the current
AppService route.

Russian recall includes a narrow recall-only alias for the audited inflection
case. This does not rename stored keys, broaden deletion, or add fuzzy matching.

## Voice and TTS

Voice input is explicit and one-shot by default for the Desktop Shell path.
`voice/one_shot_microphone_capture.py`,
`voice/one_shot_vosk_recognition_bridge.py`, and
`voice/one_shot_vosk_real_recognition.py` define local capture and Vosk
recognition boundaries. Raw microphone audio stays inside the local capture and
recognition path; recognized text enters AppService like typed input.

The project does not implement always-on microphone listening or a wake-word
service as current behavior.

Voice output uses `voice/voice_output_manager.py`,
`voice/speech_synthesis_backend.py`, `voice/voice_output_safety.py`, and
`voice/windows_local_tts_backend.py`. Local Windows TTS is a local adapter
boundary. AppService projects local TTS execution metadata for diagnostics,
enablement, disabled tests, and actual local synthesis results.

TASK-101 hardened user-facing one-shot microphone/Vosk error messages so raw
PortAudio/MME/backend/path details are not shown in AppService/Desktop text.

## Platform Adapters

`platform_adapters/contracts.py` defines filesystem ports and safe DTOs.
`platform_adapters/local_filesystem.py` contains the current
`WindowsLocalFileSystemAdapter`. It validates local paths, blocks unsupported
network/UNC-style access where applicable, performs bounded reads, and writes
new files atomically where supported by the adapter.

The current implementation is Windows-first. Broader portability is future
work, not a current support claim.

## Providers and Secure Runtime

Provider code in `ai/` is behind explicit request gates, provider selection,
fallback, privacy, and secure runtime status boundaries. AppService status and
contract methods do not decrypt or print secrets and do not call providers.

External provider requests are not default behavior. They require explicit
commands, configured credentials, and user acceptance of network, cost, and
privacy implications.

## Layer Separation

Current separation:

- UI: `app/desktop_shell.py`.
- Application boundary: `app/app_service.py` and `app/app_contracts.py`.
- Application services: `app/services/`, planner command service, workflow
  runner, vertical integration, intent resolver, startup profiler.
- Domain logic: planner, memory manager, command registry/resolution, policy,
  execution journal/coordinator, document review.
- Platform-specific operations: Windows local filesystem adapter, Windows local
  TTS backend, local microphone/Vosk integration.

The separation is functional and tested, but not final. AppService and
CommandProcessor remain transitional aggregation points.

## Future Work

Future work should stay focused and evidence-based:

- targeted decomposition of `JarvisAppService` and `CommandProcessor`;
- normal documentation maintenance for new architecture changes;
- optional coverage tooling and policy;
- repository line-ending normalization in a separate maintenance task;
- Desktop Shell action clarity and copy/export UX;
- future history export, deletion, replay, or persistent journal storage only
  after separately approved design work;
- workflow retry, replay, deletion, editing, export, persistence redesign,
  restart-persistent recovery, and analytics remain separate future work;
- installer, mobile, admin/support, and broader portability only after
  separately approved architecture work.
