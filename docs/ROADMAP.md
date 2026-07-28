# JARVIS Roadmap

Status: updated by TASK-114. This roadmap begins after the completed
execution/workflow platform milestone and the TASK-112 cognitive architecture
report, then accounts for the TASK-113 cognitive skeleton implementation.

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
context, and route typed/voice turns through the existing cognitive facade
without changing command execution behavior. These tasks establish completed
minimal contracts, in-memory session ownership, AppService integration,
persistence boundaries, and response composition without execution.

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

### TASK-114 - Conversation Session Persistence

- Purpose: introduce a safe persistence boundary for conversation session
  metadata and bounded/redacted turn summaries; load safe sessions after
  restart; preserve per-session ordering and isolation; keep
  `ConversationSessionService` as the sole session lifecycle owner.
- Main architectural risks: persisting raw sensitive text by default; turning
  the persistence adapter into a second session owner; corrupt or partial
  persisted state breaking application startup; schema evolution without
  explicit handling.
- Expected production areas may include: `cognition/persistence.py`; focused
  extensions to `cognition/sessions.py`; composition/AppService wiring only if
  required.
- Expected test areas: restart load, corruption handling, redaction, bounded
  summaries, per-session isolation, schema/version handling, and unchanged
  command behavior.
- Dependencies: TASK-113.
- Completion criteria: safe session summaries survive restart; raw sensitive
  text is not persisted by default; corrupt records fail safely and do not make
  the application unusable; no command or execution behavior changes; no
  provider/network behavior; `ConversationSessionService` remains
  authoritative.

### TASK-115 - Conversation Context & Response Composition

- Purpose: introduce bounded context projection from stored session turns; add
  a narrow response composer or compatibility response boundary; preserve the
  existing orchestration-only `CognitiveInteractionService`; return safe
  conversational responses without execution.
- Main architectural risks: unbounded context growth; cognition becoming a
  second AppService; response composition executing actions; leaking raw
  sensitive history; provider behavior being introduced prematurely.
- Expected production files: `cognition/context.py`,
  `cognition/response_composer.py`, focused extensions to
  `cognition/interaction_service.py` only if required.
- Expected test areas: bounded context snapshots, redaction, no durable state
  in interaction orchestration, no provider/network/execution, and unchanged
  command behavior.
- Dependencies: TASK-114.
- Completion criteria: interaction service can obtain a bounded context
  snapshot; response composition remains non-executing; no durable state is
  owned by `CognitiveInteractionService`; existing command behavior remains
  unchanged; no provider/network dependency unless a later approved task
  explicitly adds it.

## Milestone 2: Intent and Clarification

Completion criteria: cognitive interpretation owns non-executing user intent
for conversation turns, and clarification state is durable-safe and distinct
from approval.

### TASK-116 - IntentInterpreter Adapter

- Purpose: wrap current `HybridIntentResolver`, `CommandResolutionService`, and
  command registry evidence behind cognitive `UserIntent`.
- Main architectural risk: changing command recognition semantics during
  migration.
- Expected production files: `cognition/intent_interpreter.py`.
- Expected test areas: parity with current AppService/CommandProcessor
  characterization tests, confidence/provenance, unsupported inputs.
- Dependencies: TASK-115, after bounded context and non-executing response
  composition exist.
- Completion criteria: existing command and ordinary-conversation
  classifications project into cognitive DTOs without execution.

### TASK-117 - ClarificationCoordinator

- Purpose: centralize pending clarification records for ambiguous intent and
  missing slots.
- Main architectural risk: conflating clarification with risky-action
  confirmation.
- Expected production files: `cognition/clarification.py`,
  session-store extensions.
- Expected test areas: option matching, expiry, restart recovery,
  cancellation, no approval side effects.
- Dependencies: TASK-116.
- Completion criteria: ambiguous turns produce a persisted pending
  clarification and a later answer resolves only meaning.

### TASK-118 - ReferenceResolver Phase 1

- Purpose: resolve references from recent conversation context and read-only
  AppService history projections.
- Main architectural risk: guessing unsafe targets for action requests.
- Expected production files: `cognition/reference_resolver.py`,
  `cognition/context.py`.
- Expected test areas: "it/again" references, ambiguous candidates,
  workflow-run references, low-confidence clarification.
- Dependencies: TASK-117.
- Completion criteria: simple read-only references resolve; mutating ambiguous
  references ask clarification.

## Milestone 3: Personal Memory

Completion criteria: personal memory is explicit, policy-checked, candidate
based for inferred writes, and integrated with conversation recall without
becoming an execution owner. `MemoryPolicy` must be introduced before inferred
memory writes are represented.

### TASK-119 - MemoryPolicy Foundation

- Purpose: add a distinct memory policy component that decides what may be
  stored, what needs explicit approval, what must never be stored, retention,
  expiry, deduplication, supersession, sensitivity, deletion, and forgetting.
- Main architectural risk: mixing storage ownership into policy or allowing
  inferred writes before policy exists.
- Expected production files: `cognition/memory_policy.py`.
- Expected test areas: secret rejection, approval requirement decisions,
  retention/expiry, deduplication/supersession, sensitivity classification,
  deletion/forgetting decisions.
- Dependencies: TASK-118.
- Completion criteria: policy decisions are deterministic, serializable, and
  own no memory storage.

### TASK-120 - MemoryService Read Adapter

- Purpose: expose existing `LocalMemoryManager` through cognitive memory read
  and recall contracts while keeping MemoryService as the memory record and
  persistence owner.
- Main architectural risk: creating a second memory store.
- Expected production files: `cognition/memory_service.py`.
- Expected test areas: exact recall, aliases, unavailable store, redaction,
  provenance.
- Dependencies: TASK-119.
- Completion criteria: cognitive responses can cite memory records by id using
  current storage; MemoryPolicy owns no storage.

### TASK-121 - MemoryCandidate Approval Flow

- Purpose: represent inferred memory writes as candidates requiring explicit
  user consent after MemoryPolicy evaluation.
- Main architectural risk: silently writing inferred personal data.
- Expected production files: `cognition/memory_service.py`,
  `cognition/memory_policy.py`, `cognition/plan_policy.py`.
- Expected test areas: candidate creation, rejection, approval, expiry,
  secret-like rejection.
- Dependencies: TASK-120.
- Completion criteria: inferred memory never persists until approved.

### TASK-122 - Explicit Memory Command Migration

- Purpose: route explicit remember/recall/list/forget cognitive turns through
  MemoryService while preserving existing AppService behavior.
- Main architectural risk: breaking Preview/Execute parity and current memory
  metadata.
- Expected production files: AppService memory adapter, cognitive memory
  service updates.
- Expected test areas: existing characterization tests, operation metadata,
  forget-all confirmation, session context update.
- Dependencies: TASK-121.
- Completion criteria: memory commands keep current visible behavior with a
  clearer cognitive owner.

## Milestone 4: Goal and Planning

Completion criteria: cognitive goals and proposed plans exist above current
  planner/workflow execution, with approval and stale-plan rules.

### TASK-123 - GoalService Foundation

- Purpose: create durable-safe `UserGoal` records linked to sessions and
  source turns for non-trivial or continuing work.
- Main architectural risk: treating workflow status as goal truth.
- Expected production files: `cognition/goals.py`, persistence extensions.
- Expected test areas: goal lifecycle, restart recovery, cancellation,
  execution-link summaries.
- Dependencies: TASK-118.
- Completion criteria: active goals can be created, inspected, blocked, and
  cancelled without executing anything; simple informational turns may remain
  goal-less.

### TASK-124 - CognitivePlanner Draft Plans

- Purpose: produce `ProposedPlan` drafts for complex goals using existing
  command/planner capability metadata.
- Main architectural risk: planners executing tools or calling WorkflowRunner.
- Expected production files: `cognition/planning.py`,
  `cognition/execution_adapter.py`.
- Expected test areas: read-only plan drafts, step conversion hints, malformed
  plan refusal, no execution.
- Dependencies: TASK-123.
- Completion criteria: complex goals produce safe proposed plans only.

### TASK-125 - PlanPolicyEvaluator and Approval Records

- Purpose: add stale-plan, risk, privacy, and approval evaluation before any
  plan can be converted to execution.
- Main architectural risk: approvals applying to the wrong plan version.
- Expected production files: `cognition/plan_policy.py`,
  approval persistence updates.
- Expected test areas: stale approval, risky step approval, clarification vs
  approval separation, conflicting instructions.
- Dependencies: TASK-124.
- Completion criteria: approval is explicit, version-bound, and policy-gated.

### TASK-126 - Approved Plan To Existing Execution Contracts

- Purpose: convert approved cognitive plan steps into current AppService
  command/workflow contracts without changing WorkflowRunner ownership.
- Main architectural risk: duplicating execution lifecycle in cognition.
- Expected production files: `cognition/execution_adapter.py`, AppService
  integration.
- Expected test areas: operation registration, workflow run linkage,
  cancellation, failure projection, idempotency.
- Dependencies: TASK-125.
- Completion criteria: approved simple plans can execute through existing
  execution/workflow owners and link back to goals.

## Milestone 5: Knowledge

Completion criteria: retrieval is provenance-based, permission-aware, and
separate from memory and execution.

### TASK-127 - KnowledgeService Local Sources

- Purpose: retrieve from approved local repository/docs indexes and session
  summaries as non-authoritative, sourced, timestamped, confidence-bearing
  evidence.
- Main architectural risk: scanning unrelated private files.
- Expected production files: `cognition/knowledge_service.py`.
- Expected test areas: allowed source constraints, provenance, freshness,
  unavailable source handling.
- Dependencies: TASK-115.
- Completion criteria: informational answers can include local-source
  provenance without network; KnowledgeService does not own truth.

### TASK-128 - Memory-Backed Knowledge Retrieval

- Purpose: allow KnowledgeService to use MemoryService read summaries as a
  source while preserving memory ownership.
- Main architectural risk: duplicating memory contents in knowledge cache.
- Expected production files: `cognition/knowledge_service.py`.
- Expected test areas: memory provenance, sensitivity tags, cache separation.
- Dependencies: TASK-120 and TASK-127.
- Completion criteria: memory-derived knowledge cites memory ids and stores no
  duplicate durable memory.

### TASK-129 - External Knowledge Gate Design Implementation

- Purpose: add explicit permission and privacy-gated external retrieval
  proposal path.
- Main architectural risk: hidden network access.
- Expected production files: knowledge permission adapter and policy updates.
- Expected test areas: blocked-by-default network, consent, stale knowledge,
  provider/search failure.
- Dependencies: TASK-125 and TASK-127.
- Completion criteria: external retrieval can be proposed and approved, but no
  hidden network is used.

## Milestone 6: Automation

Completion criteria: durable workflow/execution recovery boundaries are
addressed before unattended background automation is claimed.

### TASK-130 - Durable Workflow/Execution Recovery Boundary

- Purpose: define what can and cannot be recovered for execution operations and
  workflow runs after restart before any unattended background behavior.
- Main architectural risk: falsely claiming durable workflow recovery from
  cognitive links alone.
- Expected production files: execution/workflow persistence design adapters or
  status projection contracts.
- Expected test areas: interrupted state, unavailable execution links, safe
  resume messaging, cancellation/revise options.
- Dependencies: TASK-126.
- Completion criteria: restart behavior is explicit and no unattended
  automation is claimed without durable execution/workflow recovery semantics.

### TASK-131 - Background Goal Model

- Purpose: extend goals with approved background eligibility, schedule intent,
  and cancellation expectations.
- Main architectural risk: enabling autonomous work without explicit consent.
- Expected production files: `cognition/goals.py`, policy updates.
- Expected test areas: disabled-by-default behavior, consent records, restart
  recovery.
- Dependencies: TASK-130.
- Completion criteria: background goals can be represented but not yet run.

### TASK-132 - Automation Policy and Scheduler Adapter

- Purpose: define policy checks and a narrow scheduler adapter for approved
  background proposals.
- Main architectural risk: scheduler becoming execution authority.
- Expected production files: `cognition/automation_policy.py` or policy
  extension, scheduler adapter.
- Expected test areas: stale plans, cancellation, frequency bounds,
  no direct action execution.
- Dependencies: TASK-131.
- Completion criteria: approved automation can be queued as a proposal only.

### TASK-133 - Restart-Safe Automation Observation

- Purpose: show background goal and linked execution status after restart using
  durable cognitive state and available execution projections.
- Main architectural risk: falsely claiming workflow recovery that does not
  exist.
- Expected production files: cognitive status projection, AppService DTO
  extension.
- Expected test areas: interrupted state, missing execution links, safe resume
  messaging.
- Dependencies: TASK-132.
- Completion criteria: user can see and cancel/revise interrupted automation
  state safely.

## Milestone 7: Proactive Assistant

Completion criteria: suggestions are consent-bound proposals with dismissal
state and no hidden execution.

### TASK-134 - ProactiveSuggestionService Foundation

- Purpose: represent proactive suggestions, dismiss/snooze state, and consent
  records.
- Main architectural risk: suggestions appearing without a user-approved
  trigger.
- Expected production files: `cognition/proactive.py`.
- Expected test areas: disabled default, consent, snooze/dismiss, persistence.
- Dependencies: TASK-123.
- Completion criteria: service can return no suggestion or a consent-bound
  suggestion DTO.

### TASK-135 - Proactive Policy Evaluation

- Purpose: enforce sensitivity, frequency, stale context, and approval rules
  for suggestions.
- Main architectural risk: suggesting actions based on stale or private
  context.
- Expected production files: `cognition/proactive.py`,
  `cognition/plan_policy.py`.
- Expected test areas: stale suppression, sensitive memory suppression,
  user-dismissed suppression.
- Dependencies: TASK-134.
- Completion criteria: unsafe or stale suggestions are suppressed with
  observable reason codes.

### TASK-136 - Suggestion To Goal Flow

- Purpose: accepted suggestions create normal goals or plans through the
  existing cognitive path.
- Main architectural risk: accepted suggestion bypassing approval/execution
  conversion.
- Expected production files: proactive/AppService integration.
- Expected test areas: accept/dismiss, goal creation, no direct execution,
  approval-required follow-up.
- Dependencies: TASK-135 and TASK-125.
- Completion criteria: accepted suggestions enter the same goal/planning
  pipeline as user requests.

## Milestone 8: Desktop 2.0 Integration

Completion criteria: Desktop presents sessions, clarifications, goals, plans,
and suggestions through AppService DTOs only.

### TASK-137 - Desktop Conversation Sessions, Decisions, And Suggestions UX

- Purpose: show current session, recent turn summaries, restart recovery
  status, clarification options, plan approvals, and consent-bound proactive
  suggestions through AppService DTOs only.
- Main architectural risk: Desktop importing cognitive internals.
- Expected production files: `app/desktop_shell.py`, AppService DTOs.
- Expected test areas: AppService-only boundary, disabled default, accept to
  goal, dismiss/snooze persistence, clarification answer, approve/reject, stale
  approval, disabled unsafe buttons, empty/unavailable states.
- Dependencies: TASK-115, TASK-117, TASK-125, and TASK-136.
- Completion criteria: Desktop can inspect session status through AppService,
  separates "answer a question" from "approve action", shows suggestions as
  visible proposals only, and routes accepted work through cognitive
  goal/planning.
