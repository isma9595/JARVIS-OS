# JARVIS Cognitive Architecture

Status: target architecture report from TASK-112 with a current-state addendum
through TASK-125. Target sections remain design guidance; sections explicitly
labelled current describe the implemented repository state.

## Executive Decision

JARVIS should add a cognitive layer above the completed execution/workflow
platform.

The governing rule is:

```text
Cognitive layer: decides what should be done.
Workflow/execution layer: remains the only authority that performs actions.
```

## Golden Rule

```text
LLM is not the brain.
The cognitive architecture is the brain.
An LLM is an optional, replaceable reasoning component inside it.
```

Deterministic logic must remain available for interpretation, policy,
planning, and response decisions. Provider output is untrusted evidence until
validated against cognitive contracts and policy. Providers do not own session,
intent, goal, plan, memory, policy, workflow, or execution state. Changing,
replacing, or disabling a provider must not invalidate JARVIS domain state, and
provider-specific traces must not become domain contracts.

The cognitive layer may interpret, remember, retrieve, ask, plan, propose,
compose responses, and request execution. It must not execute tools, mutate
runtime state directly, control Desktop widgets, bypass policy, write memories
without memory policy, or let provider output become executable state.

`JarvisAppService` remains the application facade for Desktop and future UI
clients in the first implementation phases. A narrow internal cognitive facade
is justified behind AppService so the cognition work does not further enlarge
`app/app_service.py`.

## Preflight State

Observed before documentation edits:

- Branch: `main`
- Local HEAD: `17953dfb10b50b5359338ef79c71c857e7ded3d1`
- `origin/main` HEAD: `17953dfb10b50b5359338ef79c71c857e7ded3d1`
- `HEAD == origin/main`: yes
- Git status at the original TASK-112 report: `## main...origin/main`
- Working tree at the original TASK-112 report: clean
- TASK-112 clarification pass observed the worktree already containing
  modifications limited to `docs/ROADMAP.md`, `.ai/tasks/TASK-112.md`, and
  `docs/architecture/COGNITIVE_ARCHITECTURE.md`.

Evidence reviewed:

- `AGENTS.md`
- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/JARVIS_APP_SERVICE.md`
- `docs/APPSERVICE_CONTRACTS.md`
- `docs/CONVERSATIONAL_LOOP.md`
- `docs/MEMORY.md`
- `docs/AI_CONTEXT_PRIVACY_BOUNDARY.md`
- `docs/audits/JARVIS_FULL_SYSTEM_AUDIT_2026-07-16.md`
- `docs/audits/JARVIS_REMEDIATION_ROADMAP_2026-07-16.md`
- `docs/architecture/APPSERVICE_PLANNER_BOUNDARY.md`
- `docs/architecture/COMMAND_RESOLUTION_BOUNDARY.md`
- `.ai/tasks/TASK-105-workflow-run-state-and-step-history.md`
- `.ai/tasks/TASK-106-desktop-workflow-viewer.md`
- `.ai/tasks/TASK-107-safe-workflow-resume.md`
- `.ai/tasks/TASK-108-workflow-cancellation-ux.md`
- `.ai/tasks/TASK-109-workflow-lifecycle-hardening.md`
- `.ai/tasks/TASK-110-desktop-activity-live-execution-status.md`
- `app/app_service.py`
- `app/app_contracts.py`
- `app/activity.py`
- `app/conversational_loop.py`
- `app/intent_resolver.py`
- `app/services/planner_command_service.py`
- `core/command_processor.py`
- `core/command_resolution_service.py`
- `core/execution_coordinator.py`
- `core/execution_journal.py`
- `core/policy_boundary.py`
- `planner/`
- `workflows/`
- `ai/`
- `memory/`
- relevant tests under `tests/characterization/`, `tests/integration/`, and
  `tests/unit/`.

TASK-111 history:

- Repository task records contain TASK-110 and then `.ai/tasks/TASK-112.md`;
  no `.ai/tasks/TASK-111*.md` file exists.
- Repository documentation search found no TASK-111 architecture or
  implementation task record.
- Recent git history shows TASK-110 implementation work followed by the
  TASK-112 documentation work. No separate implementation commit for TASK-111
  is visible in the reviewed history.
- Therefore TASK-111 is treated as a completed read-only architecture audit or
  planning checkpoint without its own task file. TASK-112 must not invent
  implementation work for TASK-111.

## Implemented State After TASK-115 Through TASK-128

The first conversational vertical slice is now implemented:

- TASK-115 added `ConversationSessionRepository` and
  `LocalConversationSessionRepository`; `ConversationSessionService` remains
  the sole session lifecycle owner and loads bounded safe persisted summaries.
- TASK-116 through TASK-119 added bounded context projection, one response
  composition pass per turn, deterministic intent interpretation, conservative
  reference resolution, and stateless clarification coordination.
- TASK-119B hardened AppService command/control routing so cancellation,
  confirmation, clarification, unsupported input, and operation identity are
  explicit and fail safely.
- TASK-120 added `JarvisAppService.handle_desktop_turn()` as the single typed
  and Desktop one-shot voice application facade. Only input classified as
  conversation invokes the full `CognitiveInteractionService.handle_turn()`;
  known commands and control turns continue through AppService execution.
- TASK-121 added the stateless `MemoryPolicy` contract; it remains
  runtime-unintegrated and owns no storage.
- TASK-123 connects `LocalConversationSessionRepository` only in standard
  Desktop composition. AppService selects the latest ACTIVE session through
  `ConversationSessionService`; direct AppService construction remains
  in-memory, and session ownership does not change.
- TASK-124 adds one Desktop scheduling/shutdown worker for typed, voice, and
  workflow-resume GUI entry points. It receives no repository or cognitive
  internals; session, cognition, execution, and workflow ownership do not move.
  Shutdown termination is independent of Tk completion consumption, while any
  retained completion remains exactly-once retrievable and the post-mainloop
  fallback discards it without presentation apply.
- TASK-125 adds the supported-composition path/migration/health boundary. It
  passes only canonical or explicit override paths into existing owners;
  `ConversationSessionService` still owns session lifecycle, cognition receives
  no migration or health responsibility, and `DesktopInteractionWorker`
  receives no paths, repositories, or persistence internals.
- TASK-126 adds only the reproducible test-environment and CI verification
  boundary; runtime ownership is unchanged.
- TASK-127 adds an app-owned primary-provider response adapter. Standard
  Desktop composition injects the existing Groq gate, while cognition remains
  provider-neutral and direct AppService construction retains deterministic
  compatibility composition. Only bounded safe session projection is supplied;
  provider output remains untrusted presentation text and never becomes an
  execution input.
- TASK-128 adds a path-free `AppDesktopChatStatus` projection owned by
  AppService. Desktop renders session, response, retry, and persistence state
  without importing cognition, providers, repositories, or persistence health
  internals. Explicit eligible retry re-enters the same AppService Desktop-turn
  facade and serialized worker; it creates no queue or second session/history
  owner.
- TASK-128 audit remediation keeps privacy authority in the configured gate:
  AppService reuses its deterministic semantic decision only for the UI
  projection, never matches refusal prose, never retries blocked context, and
  publishes no unknown external session id through the path-free DTO.
- `DesktopShellState` owns only presentation state and the current cognitive
  session id. Natural response text and structured diagnostics are projected
  separately; Desktop does not parse a formatted execution report to recover
  session or operation metadata.
- Conversation turns do not create execution operations, call
  `CommandProcessor`, enter policy/workflow execution, or route the composed
  assistant response back as command input.

Cognitive memory reads/writes, goals, planning, knowledge, and proactive
behavior remain future work. The implemented `MemoryPolicy` contract is still
not integrated into runtime memory routes.

## Current Request Path

Typed Desktop input currently follows this path:

```text
DesktopShellViewModel / Tk UI
    -> JarvisAppService.handle_desktop_turn(text, source, session_id)
        -> pending cancellation / confirmation / clarification controls first
        -> side-effect-free command preview and deterministic routing metadata
        -> conversation:
             CognitiveInteractionService.handle_turn()
             -> ConversationSessionService
             -> bounded ConversationContextProjector
             -> IntentInterpreter
             -> ReferenceResolver
             -> ClarificationCoordinator
             -> ResponseComposer exactly once
                -> standard Desktop: app-owned Groq gate or deterministic fallback
             -> AppDesktopTurnResult(response, diagnostics, session id)
        -> command or control:
             existing AppService execute_command()
             -> PolicyDecisionBoundary / ExecutionCoordinator where applicable
             -> WorkflowRunner, subsystem handler, or legacy CommandProcessor
             -> AppDesktopTurnResult(response, diagnostics, execution metadata)
        -> Desktop primary response and separate diagnostics projection
```

CLI input through `run.py` remains legacy:

```text
run.py / JARVISKernel
    -> CommandProcessor.process()
        -> CommandResolutionService for extracted deterministic routes
        -> legacy text branches / provider calls / voice managers /
           memory/profile/idea handlers / ActionRouter fallback
        -> dictionary result
```

One-shot voice follows:

```text
Desktop / AppService one-shot request
    -> local capture and Vosk recognition boundary
    -> safe Russian normalization when applicable
    -> handle_desktop_turn() with the same Desktop cognitive session id
```

Workflow and activity inspection follows:

```text
Desktop
    -> JarvisAppService
        -> WorkflowRunner read-only history projection
        -> ExecutionCoordinator recent operation snapshots
        -> ApplicationActivityTracker read-only projection
```

## Current Ownership Map

| Responsibility | Current authoritative owner | Evidence and notes |
| --- | --- | --- |
| Command interpretation | Split between `HybridIntentResolver`, `CommandResolutionService`, planner parser, AppService memory/language parsers, and legacy `CommandProcessor` | No single cognitive owner exists. The resolver modules are deterministic and non-executing; `CommandProcessor` still mixes recognition and execution for legacy paths. |
| AI provider interaction | `ai/` provider contracts, gates, router, fallback/session/runtime modules, called from `CommandProcessor` and surfaced by AppService status | Providers return text only. Provider responses are not execution authority. |
| Cognitive conversation state | `ConversationSessionService` with optional `ConversationSessionRepository` | Owns session lifecycle and ordered turns. Bounded safe summaries may be repository-backed; Desktop stores only the current session id. |
| Cognitive turn orchestration | `CognitiveInteractionService` and stateless context/intent/reference/clarification/composition services | Full orchestration runs only for conversation input and owns no execution state. |
| Command control state | AppService clarification/confirmation fields plus execution operation records | TASK-119B cancellation, confirmation, clarification, unsupported, and operation-id rules remain on the safe command route. |
| Execution lifecycle | `ExecutionCoordinator` and `ExecutionJournal` | Own operation IDs, idempotency, cancellation tokens, lifecycle status, bounded in-memory journal. |
| Workflow lifecycle | `WorkflowRunner` and `workflows/contracts.py` | Own run/step state, resume/cancel eligibility, cooperative cancellation, run history projection. Current state is in-memory. |
| Activity projection | `ApplicationActivityTracker` below AppService | Read-only projection from execution operations, not an execution owner. |
| Persistence | `LocalConversationSessionRepository`, `LocalMemoryManager`, user profile manager, Vosk settings, secure key storage; execution journal and planner/workflow state are mostly in-memory | TASK-123 connects bounded safe conversation records to default Desktop composition; persistence is not MemoryPolicy or a second session owner. |
| Desktop presentation | `app/desktop_shell.py` | Uses AppService DTOs, preserves one cognitive session id, and projects natural response separately from diagnostics; it does not import cognitive/workflow/journal/provider/filesystem/memory internals. |
| Confirmation and safety policy | `PolicyDecisionBoundary`, AppService pending confirmation state, workflow runner policy checks, memory forget-all confirmation, voice allowlist/confirmation | Clarification is explicitly separate from dangerous-action confirmation. |

## Current Gaps And Mixed Responsibilities

Missing cognitive responsibilities:

- goal representation independent of the current deterministic planner;
- general entity model for files, apps, memories, workflow runs, plans, and
  previous answers;
- provider-mediated intent interpretation with schema validation and fallback;
- plan proposal separate from execution workflow definitions;
- plan approval records and stale-plan invalidation;
- knowledge retrieval service for local docs, memory, and external knowledge
  with provenance;
- explicit memory write candidates and user approval rules;
- proactive suggestion state and consent tracking;
- restart recovery for conversation, goals, approved plans, and execution
  linkage.

Responsibilities currently mixed together:

- `JarvisAppService` combines facade, composition root, DTO projection,
  command dispatch, memory parsing, document workflow composition, voice
  projection, provider status projection, direct state-change coordination, and
  legacy wrapping.
- `CommandProcessor` still combines deterministic recognition, legacy handler
  dispatch, state mutation, provider calls, voice manager calls, response
  formatting, confirmation state, and ActionRouter fallback.
- `SafeConversationalLoop` classifies ordinary text and composes explanatory
  responses, but it is a preview foundation, not a full conversation owner.
- `MultiStepPlanner` owns both deterministic parsing and one active
  session-only plan state.

Temporary or legacy paths:

- CLI direct `CommandProcessor.process()` path remains a legacy execution
  facade.
- Old `VoiceInputManager` paths outside Desktop one-shot remain legacy and are
  not migrated by TASK-120.
- `CommandProcessor` imports `app.intent_resolver.ClarificationState`, creating
  an app-to-core dependency concern for future layering.
- AppService direct memory and language command parsing is transitional.
- Planner state is session-only and not a durable cognitive goal model.
- Workflow run history and execution journal are in-memory by design.

Reusable architectural seams:

- AppService DTO boundary in `app/app_contracts.py`.
- `HybridIntentResolver` and `CommandResolutionService` as non-executing
  interpretation precedents.
- `PolicyDecisionBoundary` as metadata-only safety evaluation.
- `ExecutionCoordinator` for operation identity, idempotency, cancellation, and
  status.
- `WorkflowRunner` for action performance, step history, resume, and
  cooperative cancellation.
- `ApplicationActivityTracker` as read-only projection pattern.
- `LocalMemoryManager` validation and JSON persistence as the first durable
  memory store.
- AI privacy/provider gates that block accidental provider calls and sensitive
  context leakage.

Components that must remain unchanged by the cognitive layer:

- Desktop must continue to use AppService-safe DTOs only.
- WorkflowRunner and ExecutionCoordinator remain action authorities.
- ExecutionJournal remains the operation journal until a separately approved
  persistence task changes it.
- Provider adapters remain text-generation adapters and do not own lifecycle.
- Local voice capture remains explicit and one-shot unless separately approved.
- Secure key storage remains separate from conversation/memory records.

## Target Architecture

The target layer is a cognition package composed behind AppService:

```text
Desktop / CLI / Voice input
    -> JarvisAppService
        -> CognitiveInteractionService
            -> ConversationSessionService
            -> IntentInterpreter
            -> ReferenceResolver
            -> ClarificationCoordinator
            -> GoalService
            -> PlannerService
            -> PlanPolicyEvaluator
            -> MemoryPolicy
            -> MemoryService
            -> KnowledgeService
            -> ResponseComposer
            -> ProactiveSuggestionService
        -> existing AppService execution/workflow APIs
        -> ExecutionCoordinator / WorkflowRunner / CommandProcessor narrowed facade
```

`CognitiveInteractionService` is an internal facade, not a UI contract.
CognitiveInteractionService is an orchestration layer, not a domain owner. It
coordinates one interaction and returns `AssistantResponse` plus optional
executable proposal DTOs. AppService remains the public facade and converts
cognitive results into existing or future AppService contracts.

`CognitiveInteractionService` must not become a second `JarvisAppService`, must
not own durable state, and must only coordinate domain services for one
interaction.

The governing cognitive model is:

```text
Conversation produces Goals.
Goals produce Plans.
Plans produce Execution.
```

`UserGoal` is the central durable cognitive domain object for non-trivial work
and continuing intent. Conversation sessions provide context and continuity,
but they are not the primary owner of user intent over time. Simple
informational turns do not have to create durable goals; ephemeral
informational turns may remain goal-less.

### 1. Conversation Sessions

Conversation sessions group turns, active goal, pending plan, and execution
linkage under a stable `session_id`. Cognitive clarification continuity comes
from ordinary assistant/user turns rather than a separate pending store.

The session manager owns creation, lookup, archival, restart loading, and
detached snapshots. It does not parse intent, call providers, run workflows, or
render UI.

### 2. Short-Term Conversational Context

Short-term context is a bounded rolling context for the current session:
recent turns, salient references, current topic, active goal summary, pending
plan summary, and last safe assistant response.

It should extend the current `SessionConversationContext` idea but move
ownership into the cognitive layer and make snapshots durable only where the
persistence model says so.

### 3. Intent Interpretation

Intent interpretation converts raw user text into `UserIntent` using
deterministic rules first, then optionally provider classification behind
privacy and cost gates. Its output is never executable.

It should reuse `HybridIntentResolver`, `CommandResolutionService`, command
registry metadata, and planner parsing during migration.

### 4. Entity And Reference Resolution

Reference resolution converts phrases such as "it", "that file", "the failed
workflow", or "open it again" into explicit entities with provenance and
confidence. It reads only conversation context, activity/workflow history
projections, memory summaries, and approved knowledge sources.

If resolution is ambiguous or unresolved, it reports that typed status instead
of guessing. Clarification coordination decides whether that bounded evidence
should become a user-facing question.

### 5. Clarification Handling

Clarification handling is one stateless coordinator for bounded deterministic
ambiguity such as ambiguous references, unresolved actionable references, and
unclear short confirmation or rejection. It must keep clarification separate
from action approval.

A clarification answer resolves data. It never approves a mutating or risky
action unless there is a distinct `PlanApproval` or existing confirmation
contract.

### 6. Goal Representation

A `UserGoal` is the cognitive representation of what the user is trying to
achieve, not a workflow run. It is the durable center of non-trivial or
continuing work. It may be informational, draft-only, executable, multi-step,
recurring, or background-eligible.

Goals have status, constraints, risk summary, source turn, current plan, and
execution links. They must survive restart only when marked durable.
Ephemeral informational turns may remain goal-less when no continuing intent,
plan, approval, memory decision, or execution linkage is needed.

### 7. Planning

The cognitive planner proposes a `ProposedPlan` from a resolved intent and
goal. It decides steps, dependencies, assumptions, required confirmations, and
which existing execution/workflow contract each executable step would use.

It does not call `WorkflowRunner.start()`, mutate memory, open files, or call
providers except through the interpreter/knowledge/provider boundaries
approved for planning text.

### 8. Plan Approval And Safety Policy

`PlanPolicyEvaluator` validates proposed plans before AppService converts them
to executable contracts. It uses existing `PolicyDecisionBoundary` for
action-level policy and adds cognitive policy for stale plans, external
provider use, proactive actions, and background automation. Memory storage
eligibility is delegated to `MemoryPolicy`.

Executable proposals must be validated and converted into current application
or workflow contracts before execution.

### 9. Personal Memory

Memory becomes two-stage:

- `MemoryCandidate`: a proposed memory write, update, or deletion inferred
  from conversation with provenance and confidence.
- `MemoryRecord`: a durable user-approved or explicit user-command memory
  stored by `MemoryService` using existing `LocalMemoryManager` initially.

No inferred personal memory is written without user consent or an approved
policy for explicit memory commands.

`MemoryPolicy` is a distinct responsibility, implemented either as a dedicated
service or as a clearly separated policy component. It decides what may be
stored, what requires explicit approval, what must never be stored, retention
and expiry, deduplication and supersession, sensitivity classification, and
deletion and forgetting rules. `MemoryService` remains the owner of memory
records and persistence. `MemoryPolicy` must not own storage.

### 10. Knowledge Retrieval

`KnowledgeService` retrieves facts from safe sources: repository docs,
approved local knowledge indexes, personal memory summaries, conversation
snapshots, and optionally external search only with explicit permission. Every
retrieved item carries source, timestamp, sensitivity, freshness, and
confidence.

KnowledgeService does not own truth. It returns sourced, timestamped,
confidence-bearing retrieval results.

It does not execute actions and does not write memory.

Knowledge authorities:

- The user is authoritative for their intent and explicit preferences.
- `MemoryService` is authoritative for accepted personal memory records.
- `ExecutionCoordinator` is authoritative for operation lifecycle.
- `WorkflowRunner` is authoritative for workflow lifecycle.
- External or retrieved knowledge remains non-authoritative evidence with
  provenance and freshness.

### 11. Proactive Suggestions

Proactive suggestions are proposals, not actions. They require an explicit
consent state, have frequency bounds, include why they are shown, and must
route any executable follow-up through normal plan/policy/approval/execution.

No proactive behavior should run at startup except loading pending suggestion
state.

### 12. Background Automation

Background automation is a future capability using durable goals and approved
plans. The cognitive layer may schedule or propose automation only after
explicit user approval. Actual work still runs through workflow/execution
contracts.

Automation must be cancellable, observable, stale-aware, and bounded by
policy.

### 13. Response Composition

`ResponseComposer` builds final assistant responses from cognitive decisions,
retrieved knowledge, plan status, execution status, and safety decisions. It
must distinguish answer, clarification, plan proposal, approval request,
execution status, refusal, and proactive suggestion.

It does not interpret intent, execute actions, or persist state.

### 14. WorkflowRunner And ExecutionCoordinator Interaction

Cognition can only request execution by producing validated proposals:

```text
ResolvedIntent + UserGoal
    -> ProposedPlan
    -> PlanPolicyEvaluator
    -> PlanApproval if required
    -> AppService conversion to existing command/workflow contract
    -> ExecutionCoordinator registration
    -> WorkflowRunner / existing execution owner
```

`WorkflowRunner` remains run/step owner. `ExecutionCoordinator` remains
operation owner. Cognitive goal and plan state link to execution IDs but do
not replace execution state.

## Component Boundaries

### CognitiveInteractionService

- Responsibility: orchestrate one user turn across session, interpretation,
  reference resolution, clarification, planning, memory candidates, knowledge,
  and response composition.
- Inputs: `ConversationTurnInput`, session id, source, optional UI capability
  flags.
- Outputs: `AssistantResponse`, optional `ProposedPlan`, optional
  `ClarificationRequest`, optional execution proposal reference.
- Owned state: none beyond short-lived turn-local orchestration.
- Persistence: none directly.
- Public interfaces: `handle_turn(input)`, `resume_session(session_id)`.
- Forbidden: direct execution, direct UI calls, direct provider adapter calls,
  direct memory writes, direct workflow mutation.
- Dependencies: cognitive services and AppService execution adapter interface.
- Lifecycle: constructed by AppService composition root.
- Failure behavior: return safe response with error code and preserve existing
  session state.
- Concurrency: serializes per session; independent sessions may run in
  parallel.
- Observability: record turn id, session id, decision path, policy result, and
  linked operation ids with safe redaction.

### ConversationSessionService

- Responsibility: create, load, snapshot, archive, and update conversation
  sessions.
- Inputs: user/source identity, session metadata, turn summaries, active goal
  links.
- Outputs: `ConversationSessionSnapshot`.
- Owned state: authoritative session metadata, turn index, active/pending
  cognitive state links.
- Persistence: durable session store for session metadata, selected turn
  summaries, active goal id, pending plan id, execution links, and ordinary
  clarification question turns.
- Public interfaces: `create_session`, `get_snapshot`, `append_turn`,
  `set_active_goal`, `close_session`.
- Forbidden: intent parsing, provider calls, execution, UI rendering.
- Dependencies: persistence adapter, clock/id generator.
- Lifecycle: process singleton per user profile.
- Failure behavior: fail closed with unavailable snapshot; do not invent
  active goals.
- Concurrency: per-session lock; append is ordered by turn sequence.
- Observability: session lifecycle events and state transition reason codes.

### ConversationContextStore

- Responsibility: maintain bounded short-term context for interpretation and
  reference resolution.
- Inputs: recent turn summaries, resolved entities, assistant response summary,
  execution outcome summaries.
- Outputs: context snapshot with salient references.
- Owned state: transient and optionally restart-restored context window.
- Persistence: only bounded summaries needed for restart; raw provider prompts
  and secrets are not stored.
- Public interfaces: `context_for(session_id)`, `record_turn_context`,
  `clear_context`.
- Forbidden: durable personal memory ownership, execution ownership, provider
  calls.
- Dependencies: session service and redaction helpers.
- Lifecycle: per session.
- Failure behavior: continue with empty context and low confidence.
- Concurrency: ordered writes per session.
- Observability: context size, redaction count, dropped-turn count.

### IntentInterpreter

- Responsibility: classify user input into `UserIntent`.
- Inputs: raw text, source, language, context snapshot, command registry,
  provider permission flags.
- Outputs: `UserIntent`.
- Owned state: none.
- Persistence: none.
- Public interfaces: `interpret(turn, context)`.
- Forbidden: execution, state mutation, memory writes, accepting confirmation.
- Dependencies: `HybridIntentResolver`, `CommandResolutionService`, provider
  classification adapter only after policy gates.
- Lifecycle: stateless service.
- Failure behavior: return unsupported or clarification-required intent with
  safe reason.
- Concurrency: fully reentrant if provider classifier dependency is reentrant.
- Observability: interpreter path, confidence, provider-used flag.

### ReferenceResolver

- Responsibility: resolve entities and references across context, memory,
  workflow history, execution history, and knowledge.
- Inputs: `UserIntent`, context snapshot, candidate entity stores.
- Outputs: `ResolvedIntent`.
- Owned state: no durable state; may cache turn-local candidates.
- Persistence: none.
- Public interfaces: `resolve(intent, context)`.
- Forbidden: guessing action targets below confidence threshold, execution,
  memory writes.
- Dependencies: ConversationContextStore, AppService read-only history
  adapters, MemoryService read API, KnowledgeService read API.
- Lifecycle: stateless service.
- Failure behavior: return unresolved or ambiguous typed status.
- Concurrency: reentrant; read-only dependencies must return snapshots.
- Observability: candidate count, selected entity id, confidence, provenance.

### ClarificationCoordinator

- Responsibility: decide whether bounded context, interpreted intent, and
  reference-resolution output require one safe clarification question.
- Inputs: current user turn, bounded context snapshot, `InterpretedIntent`, and
  `ReferenceResolutionResult`.
- Outputs: `ClarificationRequest`.
- Owned state: none.
- Persistence: none; conversation history is the only continuity source.
- Public interfaces: `coordinate(input)`.
- Forbidden: treating clarification as approval, executing selected command,
  broad free-form option execution, reconstructing command arguments,
  inspecting authoritative session objects, or persisting pending
  clarification state.
- Dependencies: immutable cognition contracts only.
- Lifecycle: stateless service.
- Failure behavior: narrow safe assistant error through
  `CognitiveInteractionService`.
- Concurrency: reentrant.
- Observability: clarification status, reason, option count, and rule id.

### GoalService

- Responsibility: create and maintain `UserGoal` records.
- Inputs: resolved intent, user constraints, clarification answers, execution
  outcomes.
- Outputs: `UserGoal` snapshot.
- Owned state: active and historical goals.
- Persistence: durable for active goals and user-approved recurring/background
  goals; session-only for ephemeral informational turns.
- Public interfaces: `create_goal`, `update_goal_status`,
  `link_execution`, `active_goal`.
- Forbidden: executing plan steps, storing secrets, direct provider calls.
- Dependencies: session store, policy evaluator, clock/id generator.
- Lifecycle: per user profile, session-linked.
- Failure behavior: mark goal blocked with safe reason, not failed execution.
- Concurrency: per-goal lock; execution outcome updates are idempotent.
- Observability: goal status transitions and linked plan/execution ids.

### CognitivePlanner

- Responsibility: build `ProposedPlan` for goals.
- Inputs: `ResolvedIntent`, goal, context, retrieved knowledge, capability
  manifest.
- Outputs: `ProposedPlan` with non-executable step descriptions and conversion
  hints to approved app/workflow contracts.
- Owned state: proposed plan drafts, not execution state.
- Persistence: pending and approved plans survive restart when linked to
  durable goals.
- Public interfaces: `propose(goal)`, `revise(plan, clarification)`.
- Forbidden: calling `WorkflowRunner`, registering operations, invoking tools,
  direct provider adapter calls outside planning-gated text generation.
- Dependencies: capability manifest, KnowledgeService, PlanPolicyEvaluator,
  optional provider planning adapter behind gates.
- Lifecycle: stateless plus plan store.
- Failure behavior: produce clarification or blocked plan.
- Concurrency: plan revisions serialized per goal.
- Observability: plan id, source intent id, provider-used flag, capability
  references.

### PlanPolicyEvaluator

- Responsibility: evaluate cognitive and action-level policy for intents,
  proposed plans, approvals, and proactive suggestions; delegate memory storage
  decisions to `MemoryPolicy`.
- Inputs: intent, resolved entities, plan, user approvals, risk metadata,
  privacy classification.
- Outputs: policy decision, required confirmations, blocked reasons.
- Owned state: none except policy configuration snapshots.
- Persistence: approved plan records and policy decisions are stored by session
  or goal services, not by evaluator.
- Public interfaces: `evaluate_intent`, `evaluate_plan`,
  `evaluate_proactive_suggestion`.
- Forbidden: execution, UI rendering, provider calls.
- Dependencies: existing `PolicyDecisionBoundary`, AI privacy policy, command
  registry metadata.
- Lifecycle: stateless service.
- Failure behavior: deny or require clarification when policy input malformed.
- Concurrency: reentrant.
- Observability: decision code, risk class, confirmation requirement,
  stale-plan result.

### MemoryPolicy

- Responsibility: decide memory storage policy for explicit memory commands,
  inferred memory candidates, updates, deletions, retention, expiry,
  deduplication, supersession, sensitivity, and forgetting.
- Inputs: user text classification, explicit memory command metadata,
  `MemoryCandidate`, existing record summaries, user approval state, privacy
  policy.
- Outputs: memory policy decision, required approval, rejection reason,
  retention/expiry, sensitivity class, deduplication/supersession instruction.
- Owned state: policy configuration snapshots only.
- Persistence: none; policy decisions are stored by session, goal, approval, or
  memory services as appropriate.
- Public interfaces: `classify`, `evaluate_candidate`, `evaluate_write`,
  `evaluate_delete`, `retention_for`.
- Forbidden: durable memory storage, execution, provider calls, UI rendering.
- Dependencies: privacy/redaction helpers, project memory rules, optional
  deterministic classifiers.
- Lifecycle: stateless service.
- Failure behavior: fail closed by rejecting or requiring explicit approval.
- Concurrency: reentrant.
- Observability: decision code, sensitivity class, approval requirement,
  retention/expiry rule.

### MemoryService

- Responsibility: manage personal memory reads, candidates, approvals, writes,
  updates, deletions, and recall summaries.
- Inputs: explicit memory commands, memory candidates, approvals, recall
  queries.
- Outputs: `MemoryCandidate`, `MemoryRecord`, memory recall result.
- Owned state: durable personal memory records and pending candidates.
- Persistence: initially `LocalMemoryManager`; later versioned memory store
  with migrations and locking.
- Public interfaces: `propose_memory`, `approve_memory`, `recall`,
  `list_records`, `delete_record`.
- Forbidden: execution ownership, plan ownership, provider prompt storage,
  policy ownership, writing inferred memory without `MemoryPolicy` approval and
  required user consent.
- Dependencies: LocalMemoryManager, MemoryPolicy, redaction helpers.
- Lifecycle: per user profile.
- Failure behavior: safe unavailable result; do not lose pending approvals.
- Concurrency: file/store writes serialized; duplicate candidate suppression.
- Observability: candidate/record ids, action, approval id, redaction result.

### KnowledgeService

- Responsibility: retrieve non-authoritative knowledge evidence with
  provenance.
- Inputs: query, allowed source set, privacy/network permissions, freshness
  requirements.
- Outputs: `RetrievedKnowledge`.
- Owned state: optional indexes/cache, not truth, user intent, or conversation
  authority.
- Persistence: approved local indexes/cache only; external result cache must be
  separate from personal memory.
- Public interfaces: `retrieve(query, constraints)`, `explain_sources`.
- Forbidden: writing memory, executing actions, changing goals, using network
  without explicit permission.
- Dependencies: docs/local search adapters, memory read API, provider/search
  adapters behind gates.
- Lifecycle: app-level service.
- Failure behavior: return partial results with provenance or unavailable
  reason.
- Concurrency: read-only queries parallelizable; cache writes serialized.
- Observability: source ids, retrieval latency, freshness, sensitivity.

### ResponseComposer

- Responsibility: compose user-visible answer from cognitive result.
- Inputs: session snapshot, intent/resolved intent, clarification, knowledge,
  plan, policy, execution status.
- Outputs: `AssistantResponse`.
- Owned state: none.
- Persistence: none directly; session service records summaries.
- Public interfaces: `compose(result)`.
- Forbidden: execution, policy override, provider calls, memory writes.
- Dependencies: localization/language preference, safe text helpers.
- Lifecycle: stateless service.
- Failure behavior: safe fallback response.
- Concurrency: reentrant.
- Observability: response type, linked ids, redaction count.

### ProactiveSuggestionService

- Responsibility: produce and track consent-bound suggestions.
- Inputs: user-approved triggers, goal state, activity summaries, memory
  preferences, time windows.
- Outputs: proactive suggestion DTO or none.
- Owned state: suggestion history, snooze/dismiss/approval state.
- Persistence: durable only for consent, dismissed/snoozed suggestions, and
  approved recurring triggers.
- Public interfaces: `evaluate`, `dismiss`, `approve`, `snooze`.
- Forbidden: running actions, direct UI control, background execution without
  consent, provider calls without gates.
- Dependencies: GoalService, MemoryService read API, KnowledgeService,
  PlanPolicyEvaluator.
- Lifecycle: disabled by default until an approved automation milestone.
- Failure behavior: no suggestion on uncertain state.
- Concurrency: one evaluation per user/session window.
- Observability: suggestion id, trigger reason, consent state.

## Conceptual DTOs

All DTOs below are immutable conceptual contracts. Python-like field names are
for clarity only and are not implementation instructions.

### ConversationSessionSnapshot

- Required: `session_id`, `user_id`, `status`, `created_at`, `updated_at`,
  `turn_count`, `active_goal_id`, `pending_plan_id`, `last_turn_id`.
- Optional: `title`, `locale`, `source_client`, `archived_at`,
  `linked_execution_ids`.
- Identifiers: stable `session_id`.
- Status enum: `active`, `waiting_for_user`, `archived`, `interrupted`,
  `unavailable`.
- Provenance: creation source, restored-from store revision.
- Confidence: not applicable.
- Serialization: JSON object with stable primitive fields and tuple/list
  collections.
- Sensitive data: summaries only; no raw secrets, provider payloads, audio, or
  file contents.

### ConversationTurn

- Required: `turn_id`, `session_id`, `sequence`, `role`, `created_at`,
  `content_summary`, `source`.
- Optional: `raw_content_ref`, `intent_id`, `response_id`, `operation_ids`,
  `memory_candidate_ids`, `knowledge_ids`.
- Status enum: `received`, `interpreted`, `answered`, `clarifying`,
  `proposed_plan`, `executed`, `failed`, `cancelled`.
- Provenance: user typed, voice transcript, system recovery, provider output.
- Confidence: transcript confidence for voice; interpretation confidence link.
- Serialization: summary by default; raw content only in an approved local
  store if needed.
- Sensitive data: redact credentials; raw transcripts are sensitive.

### UserIntent

- Required: `intent_id`, `turn_id`, `kind`, `status`, `summary`,
  `confidence`, `created_at`.
- Optional: `command_id`, `slots`, `requires_network`, `requires_provider`,
  `requires_execution`, `language`.
- Status enum: `resolved`, `requires_clarification`, `unsupported`,
  `blocked`.
- Provenance: deterministic rule ids, provider classifier id if used.
- Confidence: `high`, `medium`, `low` plus numeric optional `score`.
- Serialization: JSON-safe immutable slot map.
- Sensitive data: slots may hold entity references, not raw secret values.

### ResolvedIntent

- Required: `resolved_intent_id`, `intent_id`, `status`, `resolved_entities`,
  `confidence`, `created_at`.
- Optional: `missing_slots`, `clarification_id`, `policy_precheck`.
- Status enum: `resolved`, `needs_clarification`, `ambiguous`, `blocked`,
  `stale`.
- Provenance: context turn ids, memory ids, workflow run ids, knowledge ids.
- Confidence: per entity and aggregate.
- Serialization: entity references by stable id.
- Sensitive data: never inline raw file contents or secret-like entity values.

### ClarificationRequest

- Required: `status`, `reason`, `options`, reference/context counts,
  coordinator identity/version, and deterministic rule id.
- Optional: one bounded `safe_question` when the status needs user guidance.
- Status enum: `not_needed`, `needed`, `unavailable`.
- Provenance: bounded cognitive rule id only.
- Confidence: not represented; clarification is conversational guidance, not
  approval or resolution.
- Serialization: JSON-safe enums, primitive counters, and bounded option DTOs.
- Sensitive data: options must be safe display labels and excerpts; no hidden
  executable payloads.

### UserGoal

- Required: `goal_id`, `session_id`, `source_turn_id`, `goal_type`, `status`,
  `summary`, `created_at`, `updated_at`.
- Optional: `constraints`, `active_plan_id`, `approved_plan_id`,
  `linked_operation_ids`, `durability`, `background_eligible`.
- Status enum: `proposed`, `active`, `waiting_for_user`, `approved`,
  `executing`, `succeeded`, `failed`, `cancelled`, `blocked`, `stale`.
- Provenance: source turn, resolved intent, user edits.
- Confidence: goal extraction confidence.
- Serialization: durable JSON when active or approved.
- Sensitive data: summary redacted; constraints may include sensitivity tags.

### ProposedPlan

- Required: `plan_id`, `goal_id`, `status`, `summary`, `steps`,
  `created_at`, `updated_at`, `risk_summary`.
- Optional: `assumptions`, `required_approvals`, `stale_after`,
  `execution_contract_hints`, `provider_trace_id`.
- Status enum: `draft`, `needs_clarification`, `needs_approval`, `approved`,
  `rejected`, `executing`, `completed`, `failed`, `cancelled`, `stale`.
- Provenance: planner component, knowledge ids, provider model if used.
- Confidence: plan confidence and per-step confidence.
- Serialization: immutable step tuple; execution hints are declarative.
- Sensitive data: no raw provider chain-of-thought, secrets, or file contents.

### PlanStep

- Required: `step_id`, `plan_id`, `position`, `kind`, `summary`, `status`,
  `risk_level`, `requires_approval`.
- Optional: `dependencies`, `target_entity_refs`, `workflow_id_hint`,
  `command_id_hint`, `estimated_side_effect`, `linked_operation_id`,
  `linked_workflow_run_id`.
- Status enum: `proposed`, `approved`, `ready`, `executing`, `completed`,
  `failed`, `cancelled`, `skipped`, `blocked`.
- Provenance: user instruction, planner, retrieved knowledge.
- Confidence: step mapping confidence.
- Serialization: stable ids and primitive metadata.
- Sensitive data: target references rather than raw sensitive values.

### PlanApproval

- Required: `approval_id`, `plan_id`, `session_id`, `status`, `approved_by`,
  `created_at`, `decided_at`.
- Optional: `approved_step_ids`, `rejected_step_ids`, `conditions`,
  `expires_at`, `policy_decision_id`.
- Status enum: `pending`, `approved`, `rejected`, `expired`, `revoked`.
- Provenance: exact user turn id and client source.
- Confidence: not applicable.
- Serialization: durable approval record for executable plans.
- Sensitive data: approval text summary only; no credentials.

### MemoryCandidate

- Required: `candidate_id`, `session_id`, `source_turn_id`, `action`,
  `summary`, `status`, `confidence`, `created_at`.
- Optional: `proposed_key`, `proposed_value_summary`, `existing_record_id`,
  `reason_codes`, `expires_at`.
- Status enum: `proposed`, `needs_approval`, `approved`, `rejected`,
  `expired`, `written`, `failed`.
- Provenance: user explicit command, inferred conversation, imported source.
- Confidence: extraction confidence and sensitivity.
- Serialization: safe summaries; candidate can be discarded.
- Sensitive data: reject or redact credential-like values.

### MemoryRecord

- Required: `memory_id`, `kind`, `normalized_key`, `display_key`,
  `value_summary`, `created_at`, `updated_at`, `source`.
- Optional: `language`, `tags`, `sensitivity`, `expires_at`,
  `supersedes_memory_id`.
- Status enum: `active`, `deleted`, `superseded`, `unavailable`.
- Provenance: explicit user command or approved candidate id.
- Confidence: original candidate confidence when inferred.
- Serialization: durable versioned store, initially compatible with
  `LocalMemoryManager`.
- Sensitive data: no secrets; personal data marked sensitive and locally
  stored.

### RetrievedKnowledge

- Required: `knowledge_id`, `query_id`, `source_type`, `source_ref`,
  `summary`, `retrieved_at`, `confidence`.
- Optional: `freshness`, `citation`, `sensitivity`, `expires_at`,
  `content_ref`.
- Status enum: `available`, `partial`, `stale`, `blocked`, `unavailable`.
- Provenance: file/doc/memory/session/provider/search result identifiers.
- Confidence: source confidence plus freshness confidence.
- Serialization: summary and source metadata; large content by reference.
- Sensitive data: external sources and personal memory kept distinguishable.

### AssistantResponse

- Required: `response_id`, `session_id`, `turn_id`, `response_type`, `status`,
  `text`, `created_at`.
- Optional: `clarification_id`, `plan_id`, `goal_id`, `operation_ids`,
  `memory_candidate_ids`, `knowledge_ids`, `safety_notes`.
- Status enum: `ready`, `streaming`, `waiting_for_user`, `executing`,
  `failed`, `blocked`.
- Provenance: composer inputs and provider id if provider text was used.
- Confidence: answer confidence when applicable.
- Serialization: UI-safe text plus linked ids.
- Sensitive data: redacted output; provider raw output is not an executable
  command.

## End-To-End Flows

### A. Simple Informational Question

1. AppService receives turn and opens current session.
2. IntentInterpreter classifies as informational.
3. ReferenceResolver resolves any context references or returns none.
4. KnowledgeService retrieves non-authoritative approved local/provider
   knowledge evidence if allowed.
5. ResponseComposer returns `AssistantResponse`.
6. SessionService records turn summary.

Authoritative state owner: ConversationSessionService for turn/session;
KnowledgeService only owns retrieval metadata and cache records. No durable
goal is required for ephemeral informational turns.

Persisted state: turn summary if session is durable; no execution state.

User-visible status: answered or clarification-needed.

Failure/recovery: safe "cannot answer from available context" response.

Execution/workflow interaction: none.

### B. Direct Executable Command

1. IntentInterpreter resolves a high-confidence local command.
2. ReferenceResolver fills explicit entities.
3. PlanPolicyEvaluator evaluates command risk.
4. If allowed, AppService converts to existing command or workflow contract.
5. ExecutionCoordinator registers operation.
6. Existing owner executes: narrowed CommandProcessor route, AppService
   handler, or WorkflowRunner.
7. ResponseComposer includes execution status and operation id.

Authoritative state owner: ExecutionCoordinator and target subsystem.

Persisted state: execution journal remains current in-memory owner unless a
future persistence task changes it.

User-visible status: running, waiting for confirmation, succeeded, failed, or
denied.

Failure/recovery: operation fails safely with redacted error; session links
failure to the goal/turn.

Workflow interaction: workflow used only for workflow-backed commands.

### C. Ambiguous Request Requiring Clarification

1. IntentInterpreter or ReferenceResolver marks ambiguity.
2. ClarificationCoordinator creates `ClarificationRequest`.
3. ResponseComposer asks a bounded question.
4. SessionService records the question as an ordinary assistant turn.
5. User answer is interpreted through normal bounded context.
6. Any later resolved intent re-enters policy/planning; action approval remains
   separate.

Authoritative state owner: ConversationSessionService for turn history.

Persisted state: no pending clarification store; only normal conversation
turn summaries.

User-visible status: waiting for user.

Failure/recovery: if bounded context is unavailable, ask a generic safe prompt.

Workflow interaction: none until resolved and approved.

### D. Multi-Turn Reference: "open it again"

1. IntentInterpreter classifies action intent with unresolved reference.
2. ReferenceResolver searches recent entities and execution/workflow history
   projections.
3. If exactly one safe target is found, it returns `ResolvedIntent`.
4. If target is ambiguous or mutating, ClarificationCoordinator asks which
   item.
5. PolicyEvaluator requires approval if opening/repeating has side effects.
6. AppService converts to existing execution contract only after resolution and
   policy pass.

Authoritative state owner: context store for references; execution owner for
action.

Persisted state: reference summaries and linked operation id.

User-visible status: clarification or execution status.

Failure/recovery: ask user to name the target explicitly.

Workflow interaction: may link to a prior workflow run but cannot replay it
without approved workflow API.

### E. Complex Goal Requiring Multi-Step Plan

1. IntentInterpreter classifies as non-trivial or continuing work.
2. GoalService creates `UserGoal`.
3. KnowledgeService retrieves permitted non-authoritative knowledge evidence.
4. CognitivePlanner creates `ProposedPlan`.
5. PolicyEvaluator marks required approvals.
6. ResponseComposer presents plan and waits.

Authoritative state owner: GoalService for goal; planner for proposed plan.

Persisted state: active goal and pending plan.

User-visible status: proposed plan.

Failure/recovery: ask for missing constraints or mark blocked.

Workflow interaction: none until approval and conversion.

### F. Plan Requiring User Approval

1. User approves a specific plan/version.
2. PlanPolicyEvaluator verifies plan is not stale and approval matches current
   plan.
3. AppService converts approved executable steps to current workflow or command
   contracts.
4. ExecutionCoordinator registers operation(s).
5. WorkflowRunner executes action steps.
6. GoalService links plan steps to operation/run ids.

Authoritative state owner: PlanApproval record for approval; execution layer
for running work.

Persisted state: approval record, goal/plan link, execution linkage.

User-visible status: executing, waiting for confirmation, or completed.

Failure/recovery: stale approval is rejected; user sees refreshed plan.

Workflow interaction: workflow owns run/step lifecycle.

### G. Cancelled Or Interrupted Conversation

1. User cancels the current clarification conversation, plan, goal, or active
   execution.
2. Cognitive cancellation updates session/goal/plan state where durable state
   exists.
3. Active execution cancellation is delegated to existing AppService/
   WorkflowRunner/ExecutionCoordinator APIs.
4. ResponseComposer reports what was cancelled and what remains.

Authoritative state owner: cognitive services for conversation state;
execution services for operation cancellation.

Persisted state: cancellation status for durable goal/plan state where those
records exist. Cognitive clarification has no pending store; continuity is
represented only by normal authoritative conversation history.

User-visible status: cancelled or cancellation requested.

Failure/recovery: if operation cannot be cancelled, show central rejection
reason.

Workflow interaction: cooperative cancellation only through WorkflowRunner.

### H. Resume After Restart

1. AppService starts and loads durable sessions/goals.
2. Execution/workflow volatile state is marked unavailable unless future
   execution persistence exists.
3. SessionService restores safe conversation summary.
4. GoalService marks active goals requiring recovery as interrupted or
   awaiting user decision.
5. ResponseComposer can offer safe resume choices.

Authoritative state owner: session/goal stores; execution owner for only
durable execution records that exist.

Persisted state: sessions, active goal, approved plan, execution links, and
ordinary clarification question turns.

User-visible status: interrupted/recovery available.

Failure/recovery: ask user whether to discard, revise, or manually restart.

Workflow interaction: no automatic workflow resume after restart until a
future workflow persistence task exists.

### I. Memory Creation And Later Recall

1. User explicitly asks to remember, or cognition proposes a
   `MemoryCandidate`.
2. MemoryPolicy rejects secrets, classifies sensitivity, handles
   deduplication/supersession, and determines consent, retention, and expiry.
3. Explicit approved write goes through MemoryService to LocalMemoryManager.
4. Later query uses MemoryService recall and ReferenceResolver if needed.
5. ResponseComposer cites that the answer came from memory.

Authoritative state owner: MemoryService/LocalMemoryManager for accepted memory
records; MemoryPolicy for storage eligibility decisions only.

Persisted state: `MemoryRecord`; pending candidate if awaiting approval.

User-visible status: memory saved, rejected, or found/not found.

Failure/recovery: memory store unavailable returns safe error and no guessed
memory.

Workflow interaction: none unless memory action is part of an approved plan.

### J. Proactive Suggestion Requiring Consent

1. ProactiveSuggestionService evaluates approved triggers.
2. PolicyEvaluator checks consent, frequency, sensitivity, and action risk.
3. ResponseComposer presents a suggestion with accept/dismiss choices.
4. Accept creates or resumes a goal/plan.
5. Any executable follow-up follows approval and execution rules.

Authoritative state owner: ProactiveSuggestionService for suggestion state;
GoalService for accepted goals.

Persisted state: consent, suggestion id, dismissed/snoozed status.

User-visible status: suggestion only, never hidden execution.

Failure/recovery: if context is stale, suppress suggestion.

Workflow interaction: none until user accepts and approves executable plan.

## Safety And Trust Model

Read-only actions:

- May answer, inspect safe DTOs, retrieve approved local docs, list memory
  summaries, preview commands, and compose plans.
- Must not register execution operations unless the existing AppService route
  intentionally records read-only execution.

Mutating actions:

- Require explicit intent and policy evaluation.
- Must route through AppService and ExecutionCoordinator before subsystem
  mutation.

Irreversible actions:

- Require explicit approval bound to a current plan/action/version.
- Must fail closed on stale approval, ambiguous target, or malformed provider
  output.

Credential or secret access:

- Cognitive services may receive only safe credential status, never decrypted
  values.
- Secret-like user text is redacted and rejected for memory writes and
  provider context by default.

Personal information:

- Personal memory is local, explicit, consent-bound, and separable from
  transient conversation context.

Memory writes:

- Explicit "remember" commands may write only after MemoryPolicy validation.
- Inferred memories become candidates and require MemoryPolicy evaluation plus
  required user approval.

Proactive behavior:

- Disabled by default until an approved implementation milestone.
- Suggestions require consent and do not execute.

User confirmation:

- Clarification resolves meaning.
- Approval authorizes a specific action/plan.
- Confirmation for dangerous execution remains distinct and centrally checked.

Cancellation:

- Cognitive cancellation changes cognitive state.
- Execution cancellation uses existing coordinator/workflow APIs only.

Retries:

- Retrying provider interpretation or retrieval is allowed only if idempotent.
- Retrying execution requires existing idempotency and policy rules.

Stale plans:

- Plans expire by version/time/context. Stale approvals are invalid.

Conflicting instructions:

- Higher-priority project safety rules win.
- User-visible clarification is required when owner intent conflicts with safe
  execution policy.

Provider hallucination or malformed output:

- Provider output must be parsed as untrusted text against schemas.
- Invalid or low-confidence provider output becomes clarification or safe
  refusal.
- Providers never directly execute tools or mutate authoritative state.
- Provider-specific traces are diagnostics only and must not become session,
  intent, goal, plan, memory, workflow, or execution contracts.

## Persistence Model

Must survive restart:

- conversation session metadata and safe turn summaries for active sessions;
- active durable goal and goal status;
- ordinary clarification question turns as safe conversation summaries;
- approved plan and plan version when execution has not completed;
- execution linkage ids, while accepting that current execution/workflow
  runtime state may not be recoverable until a future persistence task;
- personal memory records and pending approved memory candidates;
- proactive consent, dismissed/snoozed suggestion state, and approved recurring
  trigger definitions.

Transient only:

- raw provider prompts and raw provider responses unless explicitly captured
  as user-visible answer summaries;
- turn-local provider classifier traces;
- raw microphone audio;
- temporary reference candidates;
- unapproved memory candidates after expiry;
- short-term context details beyond safe summaries.

Authoritative stores:

- Conversation sessions: new cognitive session store.
- Personal memories: MemoryService over existing LocalMemoryManager initially.
- Memory policy: MemoryPolicy is authoritative for memory eligibility and
  retention decisions but owns no storage.
- Execution journal: existing ExecutionJournal until redesigned.
- Workflow state: existing WorkflowRunner current in-memory state until a
  separate workflow persistence task.
- UI projection/cache: DesktopShellState only, never authoritative.

Avoid duplicate authority:

- Do not store workflow run status as cognitive truth. Store links and last
  observed safe summary only.
- Do not copy durable memory into conversation context as a second memory
  store.
- Do not make provider session state the conversation session owner.
- Do not treat retrieved knowledge as truth. Store source, timestamp,
  confidence, provenance, and freshness only.

## Integration Strategy

### JarvisAppService

`JarvisAppService` remains the facade. It should construct and call
`CognitiveInteractionService` for conversation turns while keeping existing
methods stable during migration.

Future additions:

- `start_conversation_session(...)`
- `conversation_session_snapshot(session_id)`
- `handle_conversation_turn(session_id, text, source)`
- `approve_plan(plan_id, approval)`
- `cancel_goal(goal_id)`
- `proactive_suggestions(session_id)`

Existing command, workflow, activity, memory, and provider status APIs can be
reused unchanged as execution/read-only adapters.

### CommandProcessor

`CommandProcessor` should be narrowed over time. It remains the legacy CLI/text
execution facade until its remaining routes are extracted.

Target role:

- compatibility adapter for legacy commands;
- execution adapter for command ids not yet migrated;
- no durable conversation/session ownership;
- no provider-output execution.

Long-term, `CommandProcessor` can be deprecated as the primary cognitive
interpreter after AppService plus cognitive services own all command
interpretation.

### WorkflowRunner

Reuse unchanged for workflow execution, workflow history, resume, cancellation,
and central step lifecycle. Cognitive plans should map to workflow definitions
or existing AppService command contracts; they should not manipulate runner
internals.

Future additions may include a converter/adapter from approved `ProposedPlan`
to specific workflow definitions.

### ExecutionCoordinator And ExecutionJournal

Reuse unchanged for operation id, idempotency, cancellation token, and bounded
history projection. Cognitive state stores execution links only.

Future persistence work should define durable execution records before any
restart-persistent workflow recovery is claimed.

### ApplicationActivityTracker

Reuse unchanged as read-only status projection. Cognitive services may read
AppService-projected activity snapshots for context but must not treat them as
execution authority.

### DesktopShellState

Desktop remains presentation-only. As of TASK-128 it calls
`handle_desktop_turn()`, stores the current cognitive session id, renders
natural response text, and keeps structured diagnostics in a separate state
projection. Initial resume selection is requested only through AppService. It
also renders the AppService-owned chat status and keeps only ephemeral retry
input for an explicitly eligible conversational result. It must not import
cognitive, provider, repository, or persistence internals. Future Desktop work may add
plans and suggestions only through AppService DTOs.

### AI Providers

Providers remain adapters returning text. Provider use by cognition must pass
through existing provider runtime, privacy, selection, fallback, and explicit
request gates. Provider output is schema-validated and never executable
without conversion and policy evaluation.

TASK-127 implements the first narrow version of this rule at the app composition
boundary: standard Desktop uses Groq for eligible ordinary conversation through
the existing privacy, cost/model, credential, and language gates. The adapter
owns no cognitive or provider session state, packages no memory/profile/files,
and falls back deterministically. Legacy CLI conversation remains on the
documented `CommandProcessor` path until the later semantic-router
consolidation.

The LLM/provider golden rule applies here: providers are optional replaceable
reasoning components, not the brain. Deterministic logic remains available;
provider output is untrusted; providers do not own session, intent, goal, plan,
memory, policy, workflow, or execution state; changing or disabling the
provider must not invalidate JARVIS domain state; provider-specific traces must
not become domain contracts.

## Dependency Rules

Allowed directions:

```text
app/desktop_shell.py
    -> app/app_service.py
        -> app/app_contracts.py
        -> cognition/
        -> existing app/core/planner/workflows/ai/memory services

cognition/
    -> app/app_contracts.py only for public projection if needed
    -> core command metadata, policy, execution adapter interfaces
    -> planner/workflow/memory/ai read or adapter interfaces
    -> persistence adapters

workflows/
    -> core execution/policy contracts
    -> platform adapters for concrete workflow needs

ai/
    -> security/config/provider runtime

memory/
    -> core time/safe helpers
```

Prohibited dependencies:

- Desktop importing cognitive internals.
- Cognitive services directly controlling UI widgets.
- Providers owning session, intent, goal, plan, memory, policy, workflow, or
  execution lifecycle.
- MemoryService becoming an execution owner.
- MemoryPolicy owning memory storage.
- Planners calling tools or workflow runner directly.
- Workflows depending on Desktop.
- Duplicate conversation state in AppService, CommandProcessor, and cognition.
- Circular imports between `app`, `core`, `ai`, `workflows`, `planner`, and
  persistence modules.
- Core importing AppService cognitive classes; current
  `CommandProcessor -> app.intent_resolver` dependency should be removed in a
  future cleanup.

## Proposed Package Map

```text
cognition/
    __init__.py
    contracts.py
    interaction_service.py
    sessions.py
    context.py
    intent_interpreter.py
    reference_resolver.py
    clarification_coordinator.py
    goals.py
    planning.py
    plan_policy.py
    memory_policy.py
    memory_service.py
    knowledge_service.py
    response_composer.py
    proactive.py
    execution_adapter.py
    persistence.py

tests/unit/test_cognitive_*.py
tests/integration/test_cognitive_*_appservice.py
```

`cognition/execution_adapter.py` should expose only proposal-to-AppService
conversion interfaces, not workflow or coordinator internals. AppService is the
composition root that binds those adapters to current implementation.

## Roadmap 2.0 Summary

Implementation after TASK-112 remains small and reviewable. Completed
TASK-113 through TASK-121 stages are historical records and are not renumbered
or rewritten by later planning.

The former future TASK-122 through TASK-139 numbering was projected design work
and was not implemented. TASK-122 supersedes only that unimplemented sequence.
The current normative task sequence is maintained in `docs/ROADMAP.md`.

Current sequencing implications:

- TASK-123 establishes default conversation persistence, TASK-124 adds the
  Desktop worker/shutdown boundary, TASK-125 adds unified user-data paths,
  bounded migration, and read-only health, TASK-126 adds reproducible
  environment/CI, and TASK-127 adds the first real Desktop AI conversation
  path. TASK-128 adds the chat-first Desktop projection and explicit eligible
  retry without changing session, provider, execution, persistence, or worker
  ownership. TASK-129 document intake is the next product-runtime stage,
  followed by drafting/report workflows through TASK-131.
- `MemoryService` read integration is TASK-132.
- Existing memory command migration is TASK-133.
- Memory candidates and explicit approval are TASK-134.
- Goal and planning services remain deferred design work until proven user
  scenarios establish their requirements.
- Automation requires TASK-137 durable operation/workflow summaries and
  TASK-138 restart recovery before unattended behavior can be considered.
- Provider adapters and their tests remain; complex multi-provider
  orchestration is not a near-term priority.

## Open Architectural Questions

- TASK-115 resolved the first persistence boundary in favor of bounded safe
  persisted summaries rather than raw sensitive text by default.
- Should cognitive planning initially remain deterministic, provider-assisted,
  or hybrid? The safer first milestone is deterministic with provider support
  added behind explicit gates later.
- Should restart-persistent workflow recovery be designed before background
  automation? Yes, if automation requires unattended long-running workflows.
- Should `CommandProcessor` stay as CLI facade long term? It can, but it should
  stop being a cognitive owner.
- Which storage backend should versioned cognitive sessions use after the JSON
  prototype? A separate persistence task should decide after schemas stabilize.
