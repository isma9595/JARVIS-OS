# JARVIS Roadmap

Status: updated by TASK-120. This roadmap begins after the completed
execution/workflow platform milestone and the TASK-112 cognitive architecture
report and records the completed TASK-113 through TASK-119B work plus the
current TASK-120 Desktop conversation vertical slice.

Task numbering note: repository evidence shows no `.ai/tasks/TASK-111*.md`
record and no separate TASK-111 implementation commit in the reviewed history.
TASK-111 is treated as a completed read-only architecture audit or planning
checkpoint without its own task file. This roadmap does not invent
implementation work for TASK-111.

The sequence is intentionally small. Do not combine architecture, persistence,
provider behavior, UI, and execution changes in a single task unless a later
approved task explicitly changes this rule.

## Milestone 1: Conversational Core

Completion criteria: AppService can create and inspect cognitive conversation
sessions, persist safe session summaries, project bounded conversation
context, interpret broad descriptive intent, resolve simple conversational
references, and route typed/voice turns through the AppService-owned cognitive
facade without changing command execution behavior. These tasks establish
completed contracts, repository-backed session persistence, bounded context,
response composition, intent interpretation, reference resolution,
clarification, and the Desktop conversation vertical slice without making
cognition an execution owner.

### TASK-113 - Cognitive Contracts & Interaction Skeleton - Completed

- Delivered scope: minimal immutable conversation contracts; in-memory session
  lifecycle and ordered turns; orchestration-only
  `CognitiveInteractionService`; `JarvisAppService` facade integration.
- Explicit limits: no persistence; no intent, planning, memory, knowledge,
  provider, or execution ownership.
- Main architectural risk: duplicating existing AppService/workflow DTO
  authority instead of creating cognitive-only contracts.
- Production files: `cognition/contracts.py`, `cognition/sessions.py`,
  `cognition/interaction_service.py`, `cognition/__init__.py`, focused
  `JarvisAppService` wiring.
- Expected test areas: contract immutability, serialization, redaction,
  timestamp/id field presence, session ordering, interaction orchestration,
  AppService integration, and architecture boundaries.
- Dependencies: TASK-112.
- Completion criteria: completed by TASK-113; contracts import cleanly,
  serialize safely, expose no execution handles, sessions remain in memory
  only, `ConversationSessionService` is the sole cognitive session-state
  owner, and `CognitiveInteractionService` coordinates without owning durable
  state or executing actions.

### TASK-114 - Roadmap Alignment & Session Persistence Definition - Completed

- Delivered scope: documentation-only alignment of this roadmap after
  TASK-113, preserving TASK-113 as completed and defining persistence and
  context/composition as the next implementation steps.
- Explicit limits: no production code, tests, persistence implementation,
  AppService behavior changes, provider behavior, execution behavior, or
  command behavior changes.
- Production files: `.ai/tasks/TASK-114.md`, `docs/ROADMAP.md`.
- Dependencies: TASK-113.
- Completion criteria: completed by TASK-114; the roadmap no longer schedules
  duplicate implementation of TASK-113 contracts, in-memory sessions,
  interaction orchestration, or AppService integration.

### TASK-115 - Conversation Session Persistence - Completed

- Delivered scope: safe persistence boundary for conversation session
  metadata and bounded/redacted turn summaries; load safe sessions after
  restart; preserve per-session ordering and isolation; keep
  `ConversationSessionService` as the sole session lifecycle owner.
- Main architectural risks: persisting raw sensitive text by default; turning
  the persistence adapter into a second session owner; corrupt or partial
  persisted state breaking application startup; schema evolution without
  explicit handling.
- Production areas: `cognition/persistence.py`; focused
  extensions to `cognition/sessions.py`; composition/AppService wiring only if
  required.
- Test areas completed: restart load, corruption handling, redaction, bounded
  summaries, per-session isolation, schema/version handling, and unchanged
  command behavior.
- Dependencies: TASK-113 and TASK-114.
- Completion criteria: completed by TASK-115; safe session summaries survive
  restart; raw sensitive text is not persisted by default; corrupt records
  fail safely and do not make
  the application unusable; no command or execution behavior changes; no
  provider/network behavior; `ConversationSessionService` remains
  authoritative.

### TASK-116 - Conversation Context & Response Composition - Completed

- Delivered scope: bounded immutable context projection from stored session
  turns; stateless `ConversationContextProjector`; narrow non-executing
  `ResponseComposer` protocol; compatibility composer around the existing
  AppService-owned safe conversational delegate; context-aware interaction
  orchestration.
- Explicit limits: no intent interpretation, reference resolution,
  clarification migration, goals, planning, memory, knowledge, providers,
  network, execution, workflows, Desktop UI, CLI migration, semantic
  summarization, embeddings, or provider-specific token budgeting.
- Production files: `cognition/context.py`, `cognition/response_composer.py`,
  focused extensions to cognition contracts, sessions, interaction
  orchestration, package exports, and AppService composition wiring.
- Expected test areas: completed by TASK-116 with contract, context projector,
  response composer, interaction service, AppService integration, architecture
  boundary, and existing AppService/conversational-loop compatibility tests.
- Dependencies: TASK-115.
- Completion criteria: completed by TASK-116; interaction service obtains a
  bounded context snapshot after accepting the user turn, response composition
  remains non-executing and provider-neutral, no durable state is owned by
  `CognitiveInteractionService`, and existing command behavior remains
  unchanged.

## Milestone 2: Intent, References, and Clarification

Completion criteria: cognitive interpretation owns non-executing user intent
for conversation turns, simple conversational references are resolved
conservatively from bounded context, and clarification guidance is stateless,
durable-safe, and distinct from approval.

### TASK-117 - IntentInterpreter Adapter - Completed

- Delivered scope: immutable provider-neutral intent contracts; stateless
  deterministic `IntentInterpreter` protocol and `RuleBasedIntentInterpreter`;
  context-aware intent interpretation between context projection and response
  composition; observable intent diagnostics in response composition; AppService
  composition wiring.
- Explicit limits: no command authorization, execution routing, workflow
  selection, reference resolution, clarification migration, memory, knowledge,
  providers, network, Desktop UI, embeddings, semantic classifiers, or
  provider-assisted interpretation.
- Production files: `cognition/intent_interpreter.py`, focused extensions to
  cognition contracts, interaction orchestration, response composition, package
  exports, and AppService composition wiring.
- Expected test areas: completed by TASK-117 with contract, interpreter,
  response composer, interaction service, AppService integration, architecture
  boundary, and existing AppService/conversational-loop compatibility tests.
- Dependencies: TASK-116, after bounded context and non-executing response
  composition exist.
- Completion criteria: completed by TASK-117; broad intent categories project
  into cognitive DTOs without execution, bounded context is used only for
  conservative conversational disambiguation, interpretation is invoked exactly
  once before response composition, and existing command behavior remains
  unchanged.

### TASK-118 - Reference Resolution - Completed

- Delivered scope: immutable provider-neutral reference contracts; stateless
  deterministic `ReferenceResolver` protocol and `RuleBasedReferenceResolver`;
  conservative resolution from bounded detached context; observable
  reference-resolution diagnostics in response composition; AppService
  composition wiring.
- Explicit limits: no comprehensive coreference, entity extraction, filesystem
  resolution, application-object lookup, command argument reconstruction,
  workflow selection, execution routing, clarification coordination, memory,
  knowledge, providers, network, Desktop UI, NLP frameworks, embeddings, or
  vector databases.
- Production files: `cognition/reference_resolver.py`, focused extensions to
  cognition contracts, interaction orchestration, response composition, package
  exports, and AppService composition wiring.
- Expected test areas: completed by TASK-118 with contract, resolver,
  response composer, interaction service, AppService integration, architecture
  boundary, and existing AppService/conversational-loop compatibility tests.
- Dependencies: TASK-117.
- Completion criteria: completed by TASK-118; simple conversational references
  resolve only when deterministic bounded-context rules find a unique safe
  candidate, ambiguous and unresolved states are explicit, no resolved
  reference authorizes execution, and existing command behavior remains
  unchanged.

### TASK-119 - ClarificationCoordinator - Completed

- Delivered scope: immutable provider-neutral clarification contracts;
  stateless deterministic `ClarificationCoordinator` protocol and
  `RuleBasedClarificationCoordinator`; safe bounded option construction for
  ambiguous references; explicit `not_needed`, `needed`, and `unavailable`
  outcomes; response-composer integration for clarification questions; and
  AppService composition-root wiring.
- Non-goals preserved: no pending clarification store, no state machine, no
  command or workflow reconstruction, no execution approval, no provider calls,
  no memory or knowledge lookup, and no broad missing-slot extraction.
- Expected test areas: completed by TASK-119 with contracts, coordinator,
  response composer, interaction service, AppService integration, architecture
  boundary, and existing cognitive compatibility tests.
- Dependencies: TASK-118.
- Completion criteria: completed by TASK-119; clarification is conversational
  guidance only, coordinator decisions use bounded context/intent/reference
  DTOs, questions are deterministic and safe, `unavailable` is explicit, and
  existing command/workflow/confirmation APIs remain unchanged.

### TASK-120 - Desktop Cognitive Conversation Vertical Slice & Response Presentation Boundary - Current

- Delivered scope: one AppService-owned Desktop-turn facade for typed and
  Desktop one-shot voice input; full cognitive conversation turns only after
  conversation routing; one reusable cognitive session id across typed and
  one-shot voice turns; repository-backed reopening through the TASK-115
  session repository; structured separation of natural response, diagnostics,
  session id, and optional execution metadata.
- Safety preserved: cancellation precedes confirmation; confirmation without a
  target executes nothing; confirmation does not select a clarification
  option; clarification keeps one operation id for its lifecycle; cancellation
  marks the pending operation cancelled; vague and destructive references fail
  safely; assistant response text is never routed back as a command.
- Explicit limits: no MemoryPolicy, CLI migration, VoiceInputManager redesign,
  execution-permission expansion, new history/memory subsystem, provider
  enablement, or broad Desktop redesign.
- Production areas: `app/app_service.py`, `app/app_contracts.py`,
  `app/desktop_shell.py`, and focused package exports.
- Test areas completed: clean greeting presentation without execution,
  sequential bounded context, shared typed/voice session, persisted session
  reopening, known command execution, TASK-119B control regressions,
  unsupported destructive input, response/diagnostics separation, and
  response-never-executed invariants.
- Dependencies: TASK-115 through TASK-119B.
- Automated implementation criteria: Desktop ordinary conversation uses the cognitive
  session path without creating an execution operation; known commands and
  control turns retain the safe execution route; the main Desktop output is
  natural user-facing text while technical diagnostics remain available in a
  separate state projection. Final task acceptance remains pending the required
  manual Desktop smoke.

## Milestone 3: Personal Memory

Completion criteria: personal memory is explicit, policy-checked, candidate
based for inferred writes, and integrated with conversation recall without
becoming an execution owner. `MemoryPolicy` must be introduced before inferred
memory writes are represented.

### TASK-121 - MemoryPolicy Foundation

- Purpose: add a distinct memory policy component that decides what may be
  stored, what needs explicit approval, what must never be stored, retention,
  expiry, deduplication, supersession, sensitivity, deletion, and forgetting.
- Main architectural risk: mixing storage ownership into policy or allowing
  inferred writes before policy exists.
- Expected production files: `cognition/memory_policy.py`.
- Expected test areas: secret rejection, approval requirement decisions,
  retention/expiry, deduplication/supersession, sensitivity classification,
  deletion/forgetting decisions.
- Dependencies: TASK-120.
- Completion criteria: policy decisions are deterministic, serializable, and
  own no memory storage.

### TASK-122 - MemoryService Read Adapter

- Purpose: expose existing `LocalMemoryManager` through cognitive memory read
  and recall contracts while keeping MemoryService as the memory record and
  persistence owner.
- Main architectural risk: creating a second memory store.
- Expected production files: `cognition/memory_service.py`.
- Expected test areas: exact recall, aliases, unavailable store, redaction,
  provenance.
- Dependencies: TASK-121.
- Completion criteria: cognitive responses can cite memory records by id using
  current storage; MemoryPolicy owns no storage.

### TASK-123 - MemoryCandidate Approval Flow

- Purpose: represent inferred memory writes as candidates requiring explicit
  user consent after MemoryPolicy evaluation.
- Main architectural risk: silently writing inferred personal data.
- Expected production files: `cognition/memory_service.py`,
  `cognition/memory_policy.py`, `cognition/plan_policy.py`.
- Expected test areas: candidate creation, rejection, approval, expiry,
  secret-like rejection.
- Dependencies: TASK-122.
- Completion criteria: inferred memory never persists until approved.

### TASK-124 - Explicit Memory Command Migration

- Purpose: route explicit remember/recall/list/forget cognitive turns through
  MemoryService while preserving existing AppService behavior.
- Main architectural risk: breaking Preview/Execute parity and current memory
  metadata.
- Expected production files: AppService memory adapter, cognitive memory
  service updates.
- Expected test areas: existing characterization tests, operation metadata,
  forget-all confirmation, session context update.
- Dependencies: TASK-123.
- Completion criteria: memory commands keep current visible behavior with a
  clearer cognitive owner.

## Milestone 4: Goal and Planning

Completion criteria: cognitive goals and proposed plans exist above current
  planner/workflow execution, with approval and stale-plan rules.

### TASK-125 - GoalService Foundation

- Purpose: create durable-safe `UserGoal` records linked to sessions and
  source turns for non-trivial or continuing work.
- Main architectural risk: treating workflow status as goal truth.
- Expected production files: `cognition/goals.py`, persistence extensions.
- Expected test areas: goal lifecycle, restart recovery, cancellation,
  execution-link summaries.
- Dependencies: TASK-119.
- Completion criteria: active goals can be created, inspected, blocked, and
  cancelled without executing anything; simple informational turns may remain
  goal-less.

### TASK-126 - CognitivePlanner Draft Plans

- Purpose: produce `ProposedPlan` drafts for complex goals using existing
  command/planner capability metadata.
- Main architectural risk: planners executing tools or calling WorkflowRunner.
- Expected production files: `cognition/planning.py`,
  `cognition/execution_adapter.py`.
- Expected test areas: read-only plan drafts, step conversion hints, malformed
  plan refusal, no execution.
- Dependencies: TASK-125.
- Completion criteria: complex goals produce safe proposed plans only.

### TASK-127 - PlanPolicyEvaluator and Approval Records

- Purpose: add stale-plan, risk, privacy, and approval evaluation before any
  plan can be converted to execution.
- Main architectural risk: approvals applying to the wrong plan version.
- Expected production files: `cognition/plan_policy.py`,
  approval persistence updates.
- Expected test areas: stale approval, risky step approval, clarification vs
  approval separation, conflicting instructions.
- Dependencies: TASK-126.
- Completion criteria: approval is explicit, version-bound, and policy-gated.

### TASK-128 - Approved Plan To Existing Execution Contracts

- Purpose: convert approved cognitive plan steps into current AppService
  command/workflow contracts without changing WorkflowRunner ownership.
- Main architectural risk: duplicating execution lifecycle in cognition.
- Expected production files: `cognition/execution_adapter.py`, AppService
  integration.
- Expected test areas: operation registration, workflow run linkage,
  cancellation, failure projection, idempotency.
- Dependencies: TASK-127.
- Completion criteria: approved simple plans can execute through existing
  execution/workflow owners and link back to goals.

## Milestone 5: Knowledge

Completion criteria: retrieval is provenance-based, permission-aware, and
separate from memory and execution.

### TASK-129 - KnowledgeService Local Sources

- Purpose: retrieve from approved local repository/docs indexes and session
  summaries as non-authoritative, sourced, timestamped, confidence-bearing
  evidence.
- Main architectural risk: scanning unrelated private files.
- Expected production files: `cognition/knowledge_service.py`.
- Expected test areas: allowed source constraints, provenance, freshness,
  unavailable source handling.
- Dependencies: TASK-116.
- Completion criteria: informational answers can include local-source
  provenance without network; KnowledgeService does not own truth.

### TASK-130 - Memory-Backed Knowledge Retrieval

- Purpose: allow KnowledgeService to use MemoryService read summaries as a
  source while preserving memory ownership.
- Main architectural risk: duplicating memory contents in knowledge cache.
- Expected production files: `cognition/knowledge_service.py`.
- Expected test areas: memory provenance, sensitivity tags, cache separation.
- Dependencies: TASK-122 and TASK-129.
- Completion criteria: memory-derived knowledge cites memory ids and stores no
  duplicate durable memory.

### TASK-131 - External Knowledge Gate Design Implementation

- Purpose: add explicit permission and privacy-gated external retrieval
  proposal path.
- Main architectural risk: hidden network access.
- Expected production files: knowledge permission adapter and policy updates.
- Expected test areas: blocked-by-default network, consent, stale knowledge,
  provider/search failure.
- Dependencies: TASK-127 and TASK-129.
- Completion criteria: external retrieval can be proposed and approved, but no
  hidden network is used.

## Milestone 6: Automation

Completion criteria: durable workflow/execution recovery boundaries are
addressed before unattended background automation is claimed.

### TASK-132 - Durable Workflow/Execution Recovery Boundary

- Purpose: define what can and cannot be recovered for execution operations and
  workflow runs after restart before any unattended background behavior.
- Main architectural risk: falsely claiming durable workflow recovery from
  cognitive links alone.
- Expected production files: execution/workflow persistence design adapters or
  status projection contracts.
- Expected test areas: interrupted state, unavailable execution links, safe
  resume messaging, cancellation/revise options.
- Dependencies: TASK-128.
- Completion criteria: restart behavior is explicit and no unattended
  automation is claimed without durable execution/workflow recovery semantics.

### TASK-133 - Background Goal Model

- Purpose: extend goals with approved background eligibility, schedule intent,
  and cancellation expectations.
- Main architectural risk: enabling autonomous work without explicit consent.
- Expected production files: `cognition/goals.py`, policy updates.
- Expected test areas: disabled-by-default behavior, consent records, restart
  recovery.
- Dependencies: TASK-132.
- Completion criteria: background goals can be represented but not yet run.

### TASK-134 - Automation Policy and Scheduler Adapter

- Purpose: define policy checks and a narrow scheduler adapter for approved
  background proposals.
- Main architectural risk: scheduler becoming execution authority.
- Expected production files: `cognition/automation_policy.py` or policy
  extension, scheduler adapter.
- Expected test areas: stale plans, cancellation, frequency bounds,
  no direct action execution.
- Dependencies: TASK-133.
- Completion criteria: approved automation can be queued as a proposal only.

### TASK-135 - Restart-Safe Automation Observation

- Purpose: show background goal and linked execution status after restart using
  durable cognitive state and available execution projections.
- Main architectural risk: falsely claiming workflow recovery that does not
  exist.
- Expected production files: cognitive status projection, AppService DTO
  extension.
- Expected test areas: interrupted state, missing execution links, safe resume
  messaging.
- Dependencies: TASK-134.
- Completion criteria: user can see and cancel/revise interrupted automation
  state safely.

## Milestone 7: Proactive Assistant

Completion criteria: suggestions are consent-bound proposals with dismissal
state and no hidden execution.

### TASK-136 - ProactiveSuggestionService Foundation

- Purpose: represent proactive suggestions, dismiss/snooze state, and consent
  records.
- Main architectural risk: suggestions appearing without a user-approved
  trigger.
- Expected production files: `cognition/proactive.py`.
- Expected test areas: disabled default, consent, snooze/dismiss, persistence.
- Dependencies: TASK-125.
- Completion criteria: service can return no suggestion or a consent-bound
  suggestion DTO.

### TASK-137 - Proactive Policy Evaluation

- Purpose: enforce sensitivity, frequency, stale context, and approval rules
  for suggestions.
- Main architectural risk: suggesting actions based on stale or private
  context.
- Expected production files: `cognition/proactive.py`,
  `cognition/plan_policy.py`.
- Expected test areas: stale suppression, sensitive memory suppression,
  user-dismissed suppression.
- Dependencies: TASK-136.
- Completion criteria: unsafe or stale suggestions are suppressed with
  observable reason codes.

### TASK-138 - Suggestion To Goal Flow

- Purpose: accepted suggestions create normal goals or plans through the
  existing cognitive path.
- Main architectural risk: accepted suggestion bypassing approval/execution
  conversion.
- Expected production files: proactive/AppService integration.
- Expected test areas: accept/dismiss, goal creation, no direct execution,
  approval-required follow-up.
- Dependencies: TASK-137 and TASK-127.
- Completion criteria: accepted suggestions enter the same goal/planning
  pipeline as user requests.

## Milestone 8: Desktop 2.0 Integration

Completion criteria: Desktop presents sessions, clarifications, goals, plans,
and suggestions through AppService DTOs only.

### TASK-139 - Desktop Conversation Sessions, Decisions, And Suggestions UX

- Purpose: show current session, recent turn summaries, restart recovery
  status, clarification options, plan approvals, and consent-bound proactive
  suggestions through AppService DTOs only.
- Main architectural risk: Desktop importing cognitive internals.
- Expected production files: `app/desktop_shell.py`, AppService DTOs.
- Expected test areas: AppService-only boundary, disabled default, accept to
  goal, dismiss/snooze persistence, clarification answer, approve/reject, stale
  approval, disabled unsafe buttons, empty/unavailable states.
- Dependencies: TASK-120, TASK-127, and TASK-138.
- Completion criteria: Desktop can inspect session status through AppService,
  separates "answer a question" from "approve action", shows suggestions as
  visible proposals only, and routes accepted work through cognitive
  goal/planning.
