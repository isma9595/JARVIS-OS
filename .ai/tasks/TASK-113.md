# TASK-113 - Cognitive Contracts & Interaction Skeleton

## Objective

Introduce the smallest production-ready cognitive layer skeleton behind
`JarvisAppService` without changing existing user-visible command, workflow,
voice, memory, provider, activity, confirmation, or clarification behavior.

## Scope

- Add minimal `cognition/` package modules required for TASK-113 only:
  contracts, in-memory sessions, and interaction orchestration.
- Add immutable, typed, JSON-safe cognitive contracts for conversation turn
  input, session snapshots, turns, assistant responses, and interaction
  results.
- Add an in-memory `ConversationSessionService` as the sole cognitive session
  lifecycle and turn-order owner.
- Add a narrow `CognitiveInteractionService` that coordinates one interaction
  through the session service and an AppService-owned compatibility delegate.
- Add minimal `JarvisAppService` public methods for starting, inspecting,
  handling, and closing cognitive conversation sessions.
- Add focused unit, integration-style AppService, and architecture regression
  tests.

## Non-Goals

- No intent interpretation migration.
- No `UserGoal`, `GoalService`, `ProposedPlan`, or planner work.
- No reference resolver, clarification migration, memory inference,
  `MemoryPolicy`, `MemoryService`, `KnowledgeService`, provider-assisted
  cognition, persistence, restart recovery, workflow conversion, automation,
  proactive suggestions, Desktop UI changes, CLI migration, CommandProcessor
  refactoring, streaming responses, or background work.

## Architectural Ownership

- `ConversationSessionService` owns in-memory cognitive session records and
  turn sequence.
- `CognitiveInteractionService` is orchestration-only. It owns no durable
  state, keeps no duplicate session dictionary, and does not execute commands
  or workflows.
- `JarvisAppService` remains the public application facade and composition
  root. It injects the compatibility response delegate into cognition.
- Existing execution and workflow owners remain unchanged:
  `ExecutionCoordinator` owns operation lifecycle and `WorkflowRunner` owns
  workflow lifecycle.
- Cognition does not import Desktop modules, provider implementations,
  `ExecutionCoordinator`, `WorkflowRunner`, `LocalMemoryManager`, or platform
  adapters.

## Contracts Introduced

- `ConversationTurnInput`
- `ConversationSessionSnapshot`
- `ConversationTurn`
- `AssistantResponse`
- `CognitiveInteractionResult`
- Narrow enums for session status, turn role, and TASK-113 response type.
- Narrow domain errors for invalid turns, unknown sessions, and closed
  sessions.

The contracts are frozen dataclasses, sanitize obvious secret-like text in
their JSON-safe `to_dict()` projection, and do not expose generic mutable
metadata dictionaries.

## Integration Boundary

`JarvisAppService.handle_conversation_turn(...)` creates a
`ConversationTurnInput` and delegates to `CognitiveInteractionService`.
The interaction service records the user turn, calls the injected
AppService-owned compatibility delegate exactly once, records the assistant
turn, and returns `CognitiveInteractionResult`.

The compatibility delegate uses the existing side-effect-free
`SafeConversationalLoop` path. It does not call `execute_command`,
`execute_contract`, `CommandProcessor.process`, providers, workflows, memory
persistence, Desktop widgets, or platform adapters.

## Failure Semantics

- Empty text or source raises `InvalidConversationTurnError`.
- Unknown session ids raise `ConversationSessionNotFoundError`.
- Closed sessions reject new turns with `ConversationSessionClosedError`.
- If the compatibility delegate fails after the user turn is accepted, the
  interaction service records a deterministic safe assistant error turn and
  returns an `AssistantResponse` with response type `error`.
- Failed assistant generation does not remove or reorder accepted turns.

## In-Memory Limitation

TASK-113 sessions are process-local and in-memory only. No filesystem,
database, restart recovery, migration, or durable persistence behavior is
introduced in this task.

## Test Evidence

- `python -m pytest -q tests/unit/test_cognitive_contracts.py tests/unit/test_cognitive_interaction_service.py tests/unit/test_cognitive_app_service_integration.py tests/unit/test_cognitive_architecture.py`
  - Result: 22 passed.
- `python -m pytest -q tests/unit/test_app_service.py tests/unit/test_app_contracts.py tests/unit/test_conversational_loop.py`
  - Result: 116 passed.
- `python -m pytest -q`
  - Result: 1820 passed, 2 skipped.
- `git diff --check`
  - Result: passed with only Git line-ending warnings for changed files.

## Acceptance Criteria

- `cognition/` contains only the minimal TASK-113 skeleton modules.
- Cognitive contracts are immutable, typed, JSON-safe, and provider-neutral.
- `ConversationSessionService` is the sole cognitive session-state owner.
- `CognitiveInteractionService` is orchestration-only and owns no durable
  state.
- `JarvisAppService` remains the public facade.
- No cognitive component executes actions or imports forbidden runtime owners.
- Existing AppService behavior remains unchanged.
- Focused tests pass.
- Exactly one final `python -m pytest -q` passes.
- `git diff --check` passes.
