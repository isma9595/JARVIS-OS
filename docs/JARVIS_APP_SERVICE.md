# JARVIS AppService

Status: current implementation after TASK-101, aligned by TASK-102.

`JarvisAppService` in `app/app_service.py` is the current application-facing
boundary for Desktop Shell and future UI clients. It is a facade over the
assistant's command, planning, workflow, memory, voice, provider-runtime, policy,
and projection boundaries.

The service is not a general operating-system API. It is a Python application
boundary for the current assistant.

## Role

AppService provides UI-safe access to:

- status snapshots and status text;
- versioned contract objects;
- command cards and command lists from `CommandRegistry`;
- command preview;
- explicit command execution;
- hybrid intent clarification results;
- planner creation, preview, execution, cancellation, and status projection;
- local TXT document-review workflow orchestration;
- memory and language preference operations;
- one-shot local voice request projection;
- local TTS execution metadata projection;
- recent execution history projection;
- read-only workflow run and step history projection;
- provider runtime status metadata.

Desktop Shell uses AppService and should not bypass it.

## Public Methods

Current public methods include these groups:

- Status and startup: `status_snapshot()`, `status_text_ru()`,
  `get_startup_profile()`, `startup_profile_text_ru()`.
- Language: `language_settings()`, `get_language_preference()`,
  `set_language_preference()`, `reset_language_preference()`.
- Contracts: `contract_status()`, `contract_status_text_ru()`,
  `status_cards()`, `status_cards_text_ru()`, `command_cards()`,
  `command_cards_text_ru()`, `contract_manifest()`,
  `contract_manifest_text_ru()`, `preview_contract()`,
  `execute_contract()`.
- Audio metadata: `audio_lifecycle_status()`,
  `audio_lifecycle_status_text_ru()`, `audio_status_card()`.
- Conversation: `conversational_status()`,
  `conversational_status_text_ru()`, `conversational_preview()`,
  `conversational_preview_text_ru()`, `conversational_handle()`,
  `conversational_handle_text_ru()`,
  `conversational_capabilities_text_ru()`.
- Provider runtime metadata: `provider_runtime_status()`,
  `provider_runtime_status_text_ru()`,
  `provider_runtime_credentials_text_ru()`,
  `provider_runtime_provider_text_ru()`.
- Vertical integration metadata: `vertical_integration_report()`,
  `vertical_integration_report_text_ru()`,
  `vertical_integration_checklist_text_ru()`,
  `vertical_integration_summary_text_ru()`.
- Command registry and execution: `list_commands()`,
  `categories_text_ru()`, `search_commands()`, `preview_command()`,
  `preview_text_ru()`, `execute_command()`, `execute_command_text_ru()`.
- One-shot voice: `process_one_shot_voice_request()`,
  `process_one_shot_voice_request_text_ru()`.
- Execution journal projection: `recent_execution_operations()`,
  `execution_history()`, `execution_history_text_ru()`.
- Workflow history projection: `recent_workflow_runs()`,
  `workflow_run_history()`.
- Workflow resume: `workflow_resume_eligibility()`,
  `resume_workflow_run()`.
- Workflow cancellation: `workflow_cancellation_eligibility()`,
  `cancel_workflow_run()`.
- Memory helpers: `remember_user_fact()`, `recall_user_fact()`,
  `list_user_memories()`, `forget_user_fact()`,
  `request_forget_all_memories()`, `confirm_forget_all_memories()`,
  `get_conversation_context_snapshot()`.

This list documents the current implementation surface. DTO field additions or
behavioral contract changes still require tests and an approved implementation
task.

## DTO and Serialization Boundary

AppService returns and projects DTOs from `app/app_contracts.py`, including:

- `AppCommandSource`
- `AppCommandPreview`
- `AppCommandResult`
- `AppExecutionContract`
- `AppPreviewContract`
- `AppVoiceRequestResult`
- `AppExecutionHistoryEntry`
- `AppExecutionHistoryResult`
- `WorkflowRunHistory`
- `WorkflowStepHistory`
- `WorkflowHistoryResult`
- `AppContractStatus`
- `AppStatusCard`
- `AppCommandCard`
- `AppContractManifest`
- `AppLanguagePreferenceContract`

Contract dataclasses support deterministic `to_dict()` where defined and use
safe text helpers to avoid exposing obvious secrets. DTOs should be treated as
UI-facing projection objects, not as permission to depend on AppService private
helpers or subsystem internals.

## Desktop Shell Interaction

`app/desktop_shell.py` uses AppService for:

- initial status;
- command list and category rendering;
- Preview button behavior;
- Execute button behavior;
- clarification option display;
- one explicit one-shot voice request through the microphone button;
- safe formatting of output text.

The Desktop Shell does not call `CommandProcessor`, `ActionRouter`, provider
adapters, memory storage, Vosk objects, TTS backends, or filesystem adapters
directly.

TASK-103 adds Desktop history access through `execution_history()`. The shell
receives bounded, newest-first `AppExecutionHistoryEntry` DTOs and never reads
or mutates `ExecutionJournal` internals.

TASK-105 adds a read-only workflow history foundation through
`recent_workflow_runs()` and `workflow_run_history()`. These methods return
safe, detached workflow DTOs. TASK-106 adds Desktop Shell rendering for those
DTOs without allowing the shell to inspect `WorkflowRunner`, `ExecutionJournal`,
or mutable workflow runtime state directly.

TASK-107 adds explicit safe workflow resume through AppService. The Desktop
Shell reads projected eligibility from workflow history DTOs and calls
`resume_workflow_run(run_id)` only after explicit confirmation. AppService
evaluates policy, registers a normal operation, and delegates to the central
workflow resume boundary. Desktop does not pass a step index, runtime object,
or mutable workflow state.

TASK-108 adds explicit safe workflow cancellation through AppService. The
Desktop Shell reads projected cancellation eligibility from workflow history
DTOs and calls `cancel_workflow_run(run_id)` only after explicit confirmation.
AppService evaluates policy and delegates to the central workflow cancellation
boundary. Desktop does not pass a step id, cancellation token, runtime object,
or mutable workflow state.

TASK-109 keeps that AppService contract unchanged while hardening the central
workflow policy. Non-cancellable active workflow steps now project a typed,
safe cancellation rejection through the existing eligibility/result DTOs, and
AppService still delegates policy decisions to the workflow runner rather than
duplicating them.

TASK-110 adds `application_activity()` as a read-only AppService projection for
Desktop activity status. It consumes bounded `ExecutionCoordinator` operation
snapshots through `ApplicationActivityTracker` and returns an
`ApplicationActivitySnapshotDto`. AppService does not expose coordinator,
journal, workflow runner, thread, token, exception, provider, or mutable runtime
objects through this method.

## Planner Interaction

Planner-specific AppService orchestration is delegated to
`app/services/planner_command_service.py`. AppService still composes the
planner, capability registry, policy boundary, execution coordinator, and
localized result projection.

Planner preview projects active plan and active step metadata without
execution. Planner execution uses existing operation IDs, idempotency,
confirmation pauses, cancellation, and safe snapshots.

## CommandProcessor Interaction

AppService still delegates legacy execution to `CommandProcessor.process()` for
routes that remain owned by the legacy command facade. AppService does not
directly call `ActionRouter` and does not execute provider responses as
commands.

`CommandResolutionService` now owns deterministic recognition for many
CommandProcessor routes, but `CommandProcessor` still owns handler dispatch,
state mutation, response formatting, confirmation state, provider/voice manager
calls, and fallback behavior.

## Workflow Execution

AppService composes the current local TXT document-review workflow using:

- `LocalTextDocumentReviewWorkflow`;
- `WorkflowRunner`;
- `WindowsLocalFileSystemAdapter`;
- `PolicyDecisionBoundary`;
- `ExecutionCoordinator`;
- `ExecutionJournal`.

Preview and initial execution do not write reviewed output before confirmation.
Confirmed execution writes a new sibling reviewed file and verifies both output
and source preservation.

## Preview Behavior

`preview_command(text)` and `preview_contract(text)` are read-only projection
paths. Supported preview routes include registry metadata, planner commands,
document-review command shape, and supported memory parser routes.

Preview does not call `CommandProcessor`, providers, network, microphone, Vosk,
TTS, filesystem write paths, or domain mutation handlers. It does not create
operation IDs or pending confirmations.

## Execution Behavior

`execute_command(text, source)` is the main AppService execution path. It
normalizes source information, handles clarification responses, resolves intent,
coordinates direct state-changing routes where supported, delegates planner
commands to `PlannerCommandService`, handles workflow commands, and delegates
legacy routes to `CommandProcessor`.

Execution result projection includes safe fields such as command id, category,
risk, confirmation requirement, execution status, operation id/status,
duplicate suppression, network possibility, workflow and planner metadata,
local TTS metadata, and safe user-facing error text where applicable.

`execution_history(limit)` is a read-only projection over the existing
Execution Journal. It enforces a bounded limit, defaults to the current
AppService history limit, caps oversized requests, preserves deterministic
newest-first rendering order, handles an empty journal, and returns a safe
failure result if the journal cannot be loaded. It does not create a second
history store and does not expose mutable `ExecutionOperation` objects.

`recent_workflow_runs(limit)` and `workflow_run_history(run_id)` are read-only
projections over current workflow runner state. They enforce bounded recent-run
access, return newest runs first for recent history, expose ordered immutable
step history, and return `workflow_history_unavailable` on safe access failure.
They do not retry failed steps, replay commands, delete runs, export data, or
add persistence.

`workflow_resume_eligibility(run_id)` and `resume_workflow_run(run_id)` expose
the narrow TASK-107 resume contract. Resume is allowed only for centrally
eligible workflow runs, starts at the first safe unfinished step, does not rerun
completed steps by default, validates workflow definition compatibility,
creates a distinct linked resumed attempt, and returns `WorkflowResumeResult`
with safe status/rejection fields. It does not support arbitrary replay,
user-selected start steps, retry of completed steps, workflow editing,
deletion, export, or restart-persistent recovery.

`workflow_cancellation_eligibility(run_id)` and `cancel_workflow_run(run_id)`
expose the narrow TASK-108 cancellation contract. Cancellation is allowed only
for centrally eligible active workflow runs, is policy-gated, signals the
existing cooperative cancellation boundary where supported, preserves completed
steps, prevents later steps after accepted cancellation, and returns
`WorkflowCancellationResult` with safe status/rejection fields. It does not
force-kill work, roll back side effects, cancel arbitrary steps, delete runs,
export data, or redesign persistence.

Desktop Shell consumes these methods for its Workflow History panel. The panel
performs presentation-only selection, refresh, ordered step display, and safe
copy over the returned DTOs.

## Confirmation-Required Behavior

Confirmation-required operations pause before side effects. AppService tracks
pending application confirmations, document-review confirmations, planner
confirmations, and memory forget-all confirmations through scoped state and the
execution boundary.

Repeated execution is not confirmation. Clarification answers do not approve
risky actions. Denied operations return safe user-facing results and update
operation metadata where the route is coordinated.

## Safe Error Projection

AppService catches and projects expected boundary failures into safe
user-facing text. TASK-101 hardened one-shot microphone/Vosk error projection so
raw PortAudio/MME/backend/path details are not shown through
`AppVoiceRequestResult`, Desktop output, or text one-shot Vosk command output.

Technical diagnostics may still exist inside controlled test fakes or internal
objects, but user-facing AppService projection must stay sanitized.

TASK-103 applies the same user-facing principle to execution history. History
DTO projection omits blocked internal metadata keys and sanitizes details that
look like tracebacks, backend/device failures, local filesystem paths, tokens,
or raw exception text. A malformed optional journal field is projected with a
safe fallback or omitted instead of failing the whole history request.

TASK-105 applies the same principle to workflow run and step history. Workflow
DTOs omit raw exceptions, tracebacks, internal runner objects, mutable planner
structures, local paths, and secrets. Malformed or missing optional fields are
projected with stable fallback values where possible.

TASK-108 applies the same principle to workflow cancellation results and
eligibility. Cancellation DTOs expose stable status and rejection codes plus
safe messages only; they do not expose cancellation token objects, thread
identifiers, raw exceptions, tracebacks, local paths, secrets, or arbitrary
runtime metadata.

## Local TTS Projection

Local TTS execution remains owned by voice output managers and backends.
AppService projects corrected metadata for local TTS diagnostics, Windows local
enablement, local test when not enabled, and local synthesis results. It does
not synthesize speech during Preview.

## Microphone Boundary

One-shot voice requests are explicit. AppService obtains recognition through the
configured one-shot recognition boundary, applies safe Russian voice
normalization where applicable, and sends recognized text through the same
application route as typed input.

The service does not implement always-on listening or wake-word activation.
Raw microphone audio is not sent to providers by the AppService path.

## Responsibilities Extracted

The current implementation has extracted these responsibilities:

- planner command orchestration:
  `app/services/planner_command_service.py`;
- command recognition:
  `core/command_resolution_service.py`;
- policy decisions:
  `core/policy_boundary.py`;
- execution lifecycle, cancellation, and idempotency:
  `core/execution_coordinator.py`;
- operation journal:
  `core/execution_journal.py`;
- workflow execution:
  `workflows/runner.py`;
- workflow history projection:
  `workflows/contracts.py` and `workflows/runner.py`;
- workflow resume eligibility and attempt creation:
  `workflows/contracts.py` and `workflows/runner.py`;
- local filesystem boundary:
  `platform_adapters/local_filesystem.py`;
- AppService DTOs:
  `app/app_contracts.py`;
- startup profiling and lazy optional components:
  `app/startup_profiler.py` and `core/lazy_component.py`.

## Responsibilities Still Inside AppService

AppService still owns a broad set of responsibilities:

- service composition;
- status and contract card projection;
- direct memory command parsing and execution projection;
- language command handling;
- document-review workflow composition and result projection;
- direct state-change operation coordination;
- planner service construction and result integration;
- local TTS metadata correction;
- one-shot voice result projection and sanitization;
- provider runtime status projection;
- safe text rendering for multiple result types;
- legacy command execution wrapping.

This is current transitional architecture. Do not describe AppService
decomposition as complete.

## Future Decomposition Opportunities

Future implementation tasks may extract focused services for:

- memory command parsing and projection;
- language preference command projection;
- document-review workflow composition;
- voice request projection;
- local TTS metadata projection;
- provider runtime status projection;
- recent execution history projection;
- workflow history projection;
- workflow resume projection and AppService command registration;
- status/card assembly.

These are future opportunities, not current implementation claims. Any
extraction must preserve DTOs, safety behavior, tests, confirmation semantics,
and user-visible behavior unless an approved task explicitly changes them.
