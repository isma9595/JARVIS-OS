# TASK-114 - Roadmap Alignment & Session Persistence Definition

## Objective

Align the cognitive roadmap with the repository state after TASK-113 and
define the next implementation task as conversation session persistence.

This is a documentation-only task.

## Why Roadmap Alignment Is Necessary

`docs/ROADMAP.md` still described TASK-113, TASK-114, and TASK-115 as separate
contract, session-store, and interaction-skeleton tasks. TASK-113 already
delivered the minimal production skeleton across those areas, so the roadmap
must not schedule duplicate implementation of existing capabilities.

The corrected roadmap keeps the first cognitive milestone small while moving
the next work to a safe persistence boundary and bounded response context.

## Repository Evidence From TASK-113

- `.ai/tasks/TASK-113.md` records the delivered scope as minimal contracts,
  in-memory sessions, interaction orchestration, and AppService integration.
- `cognition/contracts.py` defines immutable, JSON-safe conversation DTOs:
  `ConversationTurnInput`, `ConversationSessionSnapshot`,
  `ConversationTurn`, `AssistantResponse`, and
  `CognitiveInteractionResult`.
- `cognition/sessions.py` defines `ConversationSessionService` as the
  in-memory owner of session lifecycle and ordered turns, and explicitly
  states restart-safe persistence belongs to a later task.
- `cognition/interaction_service.py` defines orchestration-only
  `CognitiveInteractionService`, which coordinates one turn through the
  session service and an injected response delegate.
- `app/app_service.py` constructs the cognitive session and interaction
  services, exposes `start_conversation_session(...)`,
  `conversation_session_snapshot(...)`, `handle_conversation_turn(...)`, and
  `close_conversation_session(...)`, and uses an AppService-owned
  compatibility response delegate.

## Corrected TASK-113 Scope

TASK-113 is completed and delivered:

- minimal immutable conversation contracts;
- in-memory session lifecycle and ordered turns;
- orchestration-only `CognitiveInteractionService`;
- `JarvisAppService` facade integration;
- no persistence;
- no intent, planning, memory, knowledge, provider, or execution ownership.

TASK-113 did not implement the full speculative cognitive contract set from
the original roadmap. It did not add `UserGoal`, proposed plans, memory
candidates, memory policy decisions, knowledge contracts, intent migration, or
durable cognitive persistence.

## New TASK-114 Definition

Title: Conversation Session Persistence.

Purpose:

- introduce a safe persistence boundary for conversation session metadata and
  bounded/redacted turn summaries;
- load safe sessions after restart;
- preserve per-session ordering and isolation;
- keep `ConversationSessionService` as the sole session lifecycle owner.

Expected production areas may include:

- `cognition/persistence.py`;
- focused extensions to `cognition/sessions.py`;
- composition/AppService wiring only if required.

Main architectural risks:

- persisting raw sensitive text by default;
- turning the persistence adapter into a second session owner;
- corrupt or partial persisted state breaking application startup;
- schema evolution without explicit handling.

Completion criteria:

- safe session summaries survive restart;
- raw sensitive text is not persisted by default;
- corrupt records fail safely and do not make the application unusable;
- no command or execution behavior changes;
- no provider/network behavior;
- `ConversationSessionService` remains authoritative.

## New TASK-115 Definition

Title: Conversation Context & Response Composition.

Purpose:

- introduce bounded context projection from stored session turns;
- add a narrow response composer or compatibility response boundary;
- preserve orchestration-only `CognitiveInteractionService`;
- return safe conversational responses without execution.

Main architectural risks:

- unbounded context growth;
- cognition becoming a second AppService;
- response composition executing actions;
- leaking raw sensitive history;
- provider behavior being introduced prematurely.

Completion criteria:

- interaction service can obtain a bounded context snapshot;
- response composition remains non-executing;
- no durable state is owned by `CognitiveInteractionService`;
- existing command behavior remains unchanged;
- no provider/network dependency unless a later approved task explicitly adds
  it.

## Non-Goals

- No persistence implementation.
- No cognition production code changes.
- No AppService changes.
- No tests added or modified.
- No pytest run.
- No `IntentInterpreter`.
- No response composer implementation.
- No providers.
- No memory, goals, planning, knowledge, or automation.
- No later task renumbering.
- No commit or push.

## Architectural Invariants

- Cognition decides and coordinates; execution owners execute.
- `CognitiveInteractionService` is orchestration only.
- `ConversationSessionService` is the sole cognitive session-state owner.
- Persistence adapters store and load records but do not own session
  lifecycle.
- `JarvisAppService` remains the public application facade.
- Existing execution, workflow, confirmation, clarification, memory, provider,
  voice, activity, and Desktop ownership remains unchanged.
- The LLM is a replaceable reasoning component, not the cognitive
  architecture.
- No raw sensitive text persistence by default.
- No hidden network access.

## Acceptance Criteria

- `docs/ROADMAP.md` marks TASK-113 completed and describes the actual delivered
  scope without claiming speculative cognitive contracts were implemented.
- `docs/ROADMAP.md` redefines TASK-114 as Conversation Session Persistence.
- `docs/ROADMAP.md` redefines TASK-115 as Conversation Context & Response
  Composition and does not recreate `CognitiveInteractionService`.
- TASK-116 through TASK-137 are not renumbered.
- Later dependencies and wording are changed only for direct inconsistencies
  caused by the corrected TASK-113/TASK-114/TASK-115 definitions.
- The architectural invariants above remain explicit.
- Only documentation files are changed.
- `git diff --check` passes.

## Validation Evidence

- Required files reviewed:
  `AGENTS.md`, `docs/ROADMAP.md`,
  `docs/architecture/COGNITIVE_ARCHITECTURE.md`, `.ai/tasks/TASK-112.md`,
  `.ai/tasks/TASK-113.md`, `cognition/contracts.py`,
  `cognition/sessions.py`, `cognition/interaction_service.py`, and
  `app/app_service.py`.
- TASK-113 implementation evidence confirmed in `cognition/contracts.py`,
  `cognition/sessions.py`, `cognition/interaction_service.py`, and
  `app/app_service.py`.
- `docs/ROADMAP.md` reviewed for TASK-113/TASK-114/TASK-115 consistency and
  direct later dependency wording.
- `git diff --check` completed with exit code 0. Git reported Windows
  line-ending conversion warnings for `docs/ROADMAP.md` and
  `.ai/tasks/TASK-114.md`, but no whitespace errors.
- Final git status should be checked before commit.
