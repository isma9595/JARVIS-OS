# JARVIS OS Architecture

Status: published TASK-129 agentic roadmap baseline with TASK-130 Golden Agent
Eval audit remediation completed in the unstaged worktree. TASK-130 changes no
production runtime ownership or behavior; TASK-131 remains next.

JARVIS OS is currently a Windows-first assistant application. It includes a CLI,
a Tkinter Desktop Shell prototype, an AppService boundary for application
clients, cognitive conversation sessions with a persistence boundary,
deterministic command handling, local memory, local voice and TTS boundaries,
provider adapters behind explicit gates, a planner, and a safe local TXT
document-review workflow. Standard Desktop cognitive composition is
repository-backed, while direct `JarvisAppService()` construction remains
in-memory unless a repository is explicitly supplied.

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
JarvisAppService -> Cognition session / context / intent / reference /
clarification / response composition
JarvisAppService -> Planner / Workflow Runner / Policy / Journal / Memory /
Voice / Provider Runtime / CommandProcessor where needed
CommandProcessor -> CommandResolutionService / CommandRegistry / subsystem
handlers / ActionRouter fallback
```

The UI is not an execution authority. Desktop Shell code uses
`JarvisAppService` for unified typed/one-shot voice turns, status, command
listing, preview, explicit execution, clarification display, recent execution
history, workflow history inspection, and application activity status. It does
not classify conversation versus command input itself and does not call
`CommandProcessor`, cognition services, `ActionRouter`, provider adapters,
memory storage, or filesystem adapters directly.

## AppService

`JarvisAppService` in `app/app_service.py` is the application-facing boundary
for UI clients. It owns public result projection into DTOs from
`app/app_contracts.py`, safe text rendering, preview behavior, execution
coordination, and composition of the current application subsystems.

TASK-125 makes supported Desktop and CLI composition resolve one immutable
`UserDataPaths` value before constructing ordinary persistence owners. The
canonical layout root is `%LOCALAPPDATA%/JARVIS-OS/data/v1` on Windows or the
`~/.jarvis-os/data/v1` fallback; `JARVIS_USER_DATA_DIR` is an exact-root
override. Explicit per-store overrides remain authoritative.

`UserDataMigrationCoordinator` performs only bounded validate-and-copy adoption
of enumerated legacy candidates, with no-clobber publication, private path-free
receipts, per-store locks, fail-fast ordering, and no deletion or runtime
dual-read. `PersistenceHealthService` independently recomputes a read-only
snapshot and exposes it through AppService DTOs/status cards without paths,
contents, identifiers, exception details, or secrets. Neither boundary owns a
store schema or lifecycle; DPAPI storage remains security-owned.

TASK-120 adds `handle_desktop_turn()` as the single Desktop-turn facade. It
preserves pending cancellation, confirmation, and clarification controls before
routing. Ordinary conversation invokes one full cognitive turn; registered
commands, command-shaped requests, and control turns continue through the
existing safe AppService execution path. A composed assistant response is
presentation output only and is never submitted back to execution.

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
`AppVoiceRequestResult`, `AppDesktopTurnResult`, `AppDesktopChatStatus`,
`AppDesktopTurnDiagnostics`, `AppContractStatus`, `AppStatusCard`,
`AppCommandCard`, and `AppContractManifest`.

Contract objects use deterministic `to_dict()` projection and safe text helpers.
They are the public application-facing shape for Desktop Shell and future UI
clients. Internal Python objects, provider objects, credentials, microphone
streams, and filesystem handles are not public contracts.

`AppDesktopTurnResult` keeps the natural response, cognitive session id,
structured diagnostics, optional execution contract, and one path-free chat
status projection in separate fields.
Desktop renders the natural response as its primary output and retains
diagnostics in a separate state projection; it does not parse operation,
category, risk, network, or cognitive fields from formatted response text.

TASK-128 makes `AppDesktopChatStatus` the application-owned contract for
session state, bounded turn count, resumability, response/source state,
explicit retry eligibility/reason, and persistence state/code. It exposes no
repository path, persisted record, provider object, raw exception, traceback,
or secret. Desktop presents that projection and retains no parallel session
history or persistence health model.

## Cognitive Conversation

The implemented cognition layer lives in `cognition/`. Its current scope is:

- `ConversationSessionService` owns session lifecycle and ordered turns.
- `ConversationSessionRepository` is the TASK-115 persistence boundary for
  bounded safe session records; the session service remains authoritative.
- `LocalConversationSessionRepository` is the local persistence adapter.
- `ConversationContextProjector` creates bounded detached turn context.
- deterministic intent, reference, and clarification services project
  provider-neutral cognitive contracts.
- `CognitiveInteractionService` orchestrates one turn and invokes
  `ResponseComposer` exactly once.

Sequential Desktop typed turns reuse one cognitive session id. Desktop one-shot
voice passes recognized text through the same facade and same session.
TASK-123 makes `launch_desktop_shell()` use a dedicated AppService factory that
connects `LocalConversationSessionRepository`. On startup AppService selects
the latest ACTIVE session by `updated_at`, then `created_at`, then `session_id`;
CLOSED sessions are ignored. The repository retains per-record partial-load
diagnostics for direct repository-backed use. TASK-125 supported composition
adds a strict pre-owner gate, so a corrupt or unsupported authoritative
conversation store blocks that composition attempt rather than becoming a
migration source. Persisted turns contain only bounded, redacted summaries, not
raw user text or secrets. Conversation turns do not
create execution operations, invoke `CommandProcessor`, call policy/workflow
execution, or create a parallel history or memory store.

TASK-127 adds `ProviderBackedResponseComposer` at the app composition boundary.
Standard Desktop construction injects the existing `GroqRequestGate`; direct
`JarvisAppService()` construction retains the compatibility composer. The
provider adapter receives only the bounded safe conversation projection and
owns no session, intent, policy, execution, workflow, persistence, or Desktop
state. Missing credentials, privacy or cost/model refusal, provider failure,
and unexpected provider exceptions fall back to the deterministic compatibility
answer without exposing raw provider errors.

Technical provenance stays in structured diagnostics and is not embedded into
the natural answer. Provider response text is bounded, redacted, untrusted
presentation output and is never submitted to command or workflow execution.
Known commands and control turns retain the existing AppService route. Legacy
`run.py` remains on its separate `CommandProcessor` compatibility path.

TASK-121 adds `MemoryPolicy` as a deterministic stateless policy contract. It
owns eligibility and retention decisions only; it owns no memory records,
pending approvals, repository, or persistence. It is exported but is not
connected to AppService, Desktop, `LocalMemoryManager`, or the existing memory
command routes.

TASK-128 changes presentation, not routing ownership. The primary Desktop flow
uses `Сообщение`, `Отправить`, a prominent response, safe chat status, and an
explicit eligible retry. Retry submits the same bounded input through the same
AppService facade, cognitive session id, and serialized Desktop worker. It is
not automatic, creates no backlog, and is disabled for command/control,
clarification, privacy-blocked, and failed results. Provider output remains
presentation-only and never becomes a retry-time execution instruction.
Gate-level privacy refusal is projected from the configured policy's semantic
decision rather than formatted refusal text. Unknown session ids are omitted
from the path-free DTO, and clearing Desktop output refreshes idle/no-retry
status through the AppService read contract.

TASK-129 sets the future product direction without adding runtime components.
JARVIS is to become a goal-driven, tool-using, verifiable, resumable,
model-independent personal AI agent. Models remain replaceable reasoning
engines; JARVIS retains context, policy, execution, provenance, persistence,
memory, and verification ownership. The normative future sequence is defined in
`docs/AGENTIC_ROADMAP_V1.md` and starts with TASK-130 Golden Agent Evals v1.

Legacy compatibility is explicitly frozen: new user capabilities must not be
implemented primarily by expanding `CommandProcessor` literal phrase routing,
`CommandResolutionService` passthrough tables, or deterministic
`MultiStepPlanner` phrase grammar. Existing routes remain operational and
covered. Future Agent Runtime and Tool Registry work must orchestrate the
current AppService, policy, execution, workflow, persistence, cognition, and
provider gates rather than duplicate or bypass them.

TASK-130 adds a test/evaluation boundary outside production runtime. A versioned
30-case catalog is executed offline through public AppService entry points with
deterministic provider/command fakes. The runner owns only catalog validation,
bounded observations, contract comparison, and aggregate metrics; it owns no
application, cognition, policy, execution, workflow, provider, persistence,
memory, Desktop, or tool state. Behavioral-contract success is reported
separately from actual goal success, and unavailable token/cost/context/verifier
signals remain unavailable rather than becoming invented measurements.
The baseline adapter derives task outcome from bounded AppService DTO state,
retains semantic verifiers only for goal-specific context/cancellation meaning,
counts every recorded registered-command invocation, and blocks external
network/provider/microphone/filesystem boundaries during evaluation. A blocked
callback is a failed task in the total-case denominator; safe reports still
contain no raw callback exception or payload.

TASK-124 adds a Desktop-only scheduling and shutdown boundary. Typed turns,
one-shot voice requests, and workflow resume GUI handlers submit to one lazy,
serialized, non-daemon worker and receive completion through main-thread Tk
polling. The worker does not own AppService, cognition, execution, workflows,
providers, persistence, or presentation state. Cancellation is cooperative;
normal completion of an already-started opaque AppService call is not relabelled
as cancelled and completed side effects are not rolled back. Close waits for a
confirmed safe worker stop, performs no Tk calls after destroy, and keeps the
ACTIVE conversation session resumable. Shutdown can transition the worker to
STOPPED while retaining a pending completion for exactly-once retrieval, so
thread termination never depends on future Tk polling. The post-mainloop
fallback joins first and consumes any retained completion without presentation
apply. Busy close projects the authoritative cancellation snapshot immediately.

## Implementation Status Boundaries

Implemented and default:

- the AppService DTO boundary and unified Desktop facade for typed and one-shot
  voice turns;
- default Desktop repository-backed session continuation, plus in-memory direct
  AppService construction, bounded context, deterministic intent, reference
  resolution, clarification, and compatibility response composition;
- execution safety, confirmation, cancellation, idempotency, privacy/network
  gates, DPAPI key storage, filesystem adapter boundaries, and the existing
  provider adapters and test base.

Implemented composition boundary:

- standard Desktop construction uses the local repository; direct AppService
  construction remains in-memory unless a repository is explicitly supplied.

Implemented contract but not runtime-integrated:

- TASK-121 `MemoryPolicy`; it is stateless, owns no storage, and is not used by
  current memory routes.

Implemented verification boundary:

- TASK-126 pins the Windows Server 2025 / CPython 3.14.6 pytest environment in
  `requirements-ci.txt`, centralizes discovery in `pytest.ini`, and runs the
  same `python -m pytest -q` contract in a read-only bounded GitHub Actions job;
- the CI workflow owns no runtime behavior, secrets, providers, hardware,
  persistence, application state, or release/deployment authority;
- optional `numpy`, `sounddevice`, and `vosk` voice dependencies remain manual
  and are not mandatory test dependencies.

Implemented primary conversation boundary:

- standard Desktop ordinary conversation uses Groq through the existing
  privacy, model/cost, credential, and language gates;
- provider context is capped and derived only from the existing bounded safe
  session projection; memory, profile, files, logs, screen, audio, and raw
  secrets are not packaged automatically;
- deterministic fallback remains available and direct AppService construction
  remains compatibility-based and in-memory;
- cognition stays provider-neutral, Desktop stays AppService-only, and
  provider output never becomes execution input.

Planned:

- TASK-131 Unified Tool Contract & Tool Registry v1, followed only later by
  permissions, durable runs, the Agent Runtime, planner/verifier, context,
  artifacts, and environment-integration stages in `docs/ROADMAP.md` and
  `docs/AGENTIC_ROADMAP_V1.md`.

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
`LocalMemoryManager`. The legacy `memory/conversation_context.py` remains
available to older paths, while Desktop cognitive turns use
`ConversationSessionService` and `ConversationContextProjector`. TASK-120 does
not merge either mechanism into personal memory. TASK-121 adds only the
stateless `MemoryPolicy` decision boundary; it owns no records or persistence
and is not integrated into runtime memory routes.

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
recognition path; recognized text enters `handle_desktop_turn()` like typed
input and uses the current Desktop cognitive session id.

The older CLI and `VoiceInputManager` routes outside Desktop one-shot remain
legacy paths. TASK-120 records their later migration as separate work and does
not redesign them.

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
- Cognitive conversation: `cognition/` session, persistence, bounded context,
  intent, reference, clarification, interaction, and response composition.
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

- follow the normative task sequence in `docs/ROADMAP.md`;
- preserve provider adapters and their tests while deferring complex
  consensus/multi-provider orchestration until a useful primary AI
  conversation exists;
- targeted decomposition of `JarvisAppService` and `CommandProcessor`;
- separately approved migration of the legacy CLI and non-Desktop
  `VoiceInputManager` bypass paths;
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

A new full audit is not required for this documentation alignment. A release
audit is required before public release, unattended automation, automatic
message sending, or other dangerous external actions.
