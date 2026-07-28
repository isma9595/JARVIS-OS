# TASK-112 - Design the JARVIS Cognitive Architecture

## Objective

Define the final fundamental architecture for JARVIS cognition and
conversation on top of the completed execution/workflow platform.

## Scope

- Current-state architecture mapping from user input to execution.
- Target cognitive architecture and ownership model.
- Component boundaries, DTO concepts, end-to-end flows, safety model,
  persistence model, integration strategy, dependency rules, and roadmap.
- Documentation-only changes.

## Non-Goals

- No production code.
- No placeholder classes.
- No refactors.
- No runtime behavior changes.
- No dependency changes.
- No commits or pushes.

## Architecture Decisions

- `JarvisAppService` remains the public facade for Desktop and future clients
  during initial cognitive implementation.
- A new internal `CognitiveInteractionService` facade is justified behind
  AppService to prevent further AppService growth.
- CognitiveInteractionService is an orchestration layer, not a domain owner. It
  must not become a second `JarvisAppService`, must not own durable state, and
  must only coordinate domain services for one interaction.
- The governing cognitive model is: Conversation produces Goals. Goals produce
  Plans. Plans produce Execution.
- `UserGoal` is the central durable cognitive domain object for non-trivial or
  continuing work. Conversation sessions provide context and continuity but do
  not primarily own user intent over time. Simple informational turns may
  remain goal-less.
- The cognitive layer decides intent, context, goals, plans, memory
  candidates, knowledge use, clarification, and responses.
- `WorkflowRunner` and `ExecutionCoordinator` remain the only action/execution
  authorities.
- KnowledgeService does not own truth. It returns sourced, timestamped,
  confidence-bearing retrieval results.
- Authority is intentionally separated: the user owns their intent and explicit
  preferences, MemoryService owns accepted personal memory records,
  ExecutionCoordinator owns operation lifecycle, WorkflowRunner owns workflow
  lifecycle, and retrieved knowledge remains non-authoritative evidence.
- `MemoryPolicy` is a distinct responsibility for what may be stored, approval
  requirements, never-store rules, retention/expiry,
  deduplication/supersession, sensitivity classification, deletion, and
  forgetting. MemoryService remains the owner of memory records and
  persistence; MemoryPolicy owns no storage.
- Golden rule: LLM is not the brain. The cognitive architecture is the brain.
  An LLM is an optional, replaceable reasoning component inside it.
- Provider output is untrusted text and must never directly execute tools,
  mutate authoritative state, own domain state, or become a domain contract.
- Clarification is separate from action approval.
- Personal memory writes are explicit or candidate-and-approval based.
- Proactive behavior is disabled by default and consent-bound.

## Risks

- Duplicating workflow/execution state in cognitive stores.
- Letting provider planning bypass deterministic policy and execution
  contracts.
- Allowing provider-specific traces to become domain contracts.
- Persisting raw sensitive conversation text unnecessarily.
- Continuing to grow `JarvisAppService` instead of adding a narrow internal
  cognitive facade.
- Letting `CognitiveInteractionService` become a durable domain owner.
- Letting KnowledgeService become a truth owner instead of a provenance-bearing
  retrieval service.
- Mixing MemoryPolicy storage eligibility with MemoryService persistence.
- Allowing Desktop to import cognitive internals.
- Claiming restart-persistent workflow recovery before workflow persistence is
  designed.

## Acceptance Criteria

- `docs/architecture/COGNITIVE_ARCHITECTURE.md` exists and covers current
  state, target architecture, component boundaries, conceptual DTOs, flows,
  safety, persistence, integration, dependency rules, package map, roadmap
  linkage, and open questions.
- `docs/ROADMAP.md` contains a sequenced Roadmap 2.0 beginning after TASK-112.
- `.ai/tasks/TASK-112.md` records objective, scope, non-goals, decisions,
  risks, acceptance criteria, validation, and proposed next task.
- Only documentation files are changed.
- Referenced current modules and APIs are verified to exist.
- Task numbering is checked for conflicts.
- TASK-111 numbering gap is documented from repository evidence without
  inventing implementation work.
- Roadmap TASK-113 through TASK-137 sequencing introduces cognitive contracts,
  session/context ownership, goal ownership, persistence boundaries, and
  orchestration without execution before execution-facing work.
- MemoryPolicy is introduced before inferred memory writes.
- Durable workflow/execution recovery boundaries are addressed before
  unattended background automation is claimed.
- Git diff and status are inspected.

## Validation Performed

- Read required preflight files, recent task records TASK-105 through TASK-110,
  architecture/audit docs, AppService, contracts, command processor,
  workflow/execution, provider, memory, conversation, planner, and relevant
  test references.
- Verified current branch and HEAD alignment before edits:
  `main` at `17953dfb10b50b5359338ef79c71c857e7ded3d1`, matching
  `origin/main`.
- Verified `.ai/tasks/` contains TASK-110 as latest tracked numbered task and
  no TASK-112 conflict before adding this record.
- Verified `.ai/tasks/` contains no `.ai/tasks/TASK-111*.md` record and
  repository documentation search found no TASK-111 task record.
- Reviewed recent git history and found no visible separate TASK-111
  implementation commit in the reviewed range; TASK-111 is documented as a
  completed read-only architecture audit or planning checkpoint without its own
  task file.
- Verified `docs/architecture/` exists and is the established location for
  detailed architecture notes.
- Reviewed TASK-113 through TASK-137 roadmap sequencing after clarifications:
  early tasks establish cognitive contracts, session/context ownership,
  durable `UserGoal` ownership contracts, persistence boundaries, and
  orchestration without execution; MemoryPolicy precedes inferred memory
  writes; durable workflow/execution recovery boundary work precedes unattended
  automation claims.
- `git diff --check` completed with exit code 0. Git reported the existing
  Windows line-ending conversion warning for `docs/ROADMAP.md`, but no
  whitespace errors.
- Final review should use `git status --short --branch` before commit.

## Proposed Next Task

TASK-113 - Cognitive Contracts Foundation.
