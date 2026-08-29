# JARVIS Roadmap

Status: verified and published implementation history through TASK-128; the
normative future sequence is rebaselined by TASK-129 around the approved
full-personal-agent product goal. This roadmap preserves completed TASK-113
through TASK-128 history and defines one future sequence from TASK-129 onward.

Task numbering note: repository evidence shows no `.ai/tasks/TASK-111*.md`
record and no separate TASK-111 implementation commit in the reviewed history.
TASK-111 is treated as a completed read-only architecture audit or planning
checkpoint without its own task file. This roadmap does not invent
implementation work for TASK-111.

The detailed architecture principles and progress gates for the new sequence are
recorded in `docs/AGENTIC_ROADMAP_V1.md`. Future capability work must preserve
existing policy, confirmation, cancellation, idempotency, workflow, execution,
persistence, provider-privacy, and application-facade ownership.

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

### TASK-120 - Desktop Cognitive Conversation Vertical Slice & Response Presentation Boundary - Completed

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
- Completion criteria: completed by TASK-120; Desktop ordinary conversation
  uses the cognitive session path without creating an execution operation;
  known commands and control turns retain the safe execution route; the main
  Desktop output is natural user-facing text while technical diagnostics remain
  in a separate state projection.
- Published commit:
  `db21ed45ba35d9a97db42bd27a6dd60de33b2658`.

## Completed Foundation After The Desktop Slice

### TASK-121 - MemoryPolicy Foundation - Completed

- Delivered scope: deterministic, stateless, immutable, and exported
  `MemoryPolicy` contracts and decisions for memory eligibility, approval,
  retention, deduplication, supersession, sensitivity, and deletion.
- Boundary preserved: policy owns no records, candidates, approvals, storage,
  repository, or persistence and is not integrated with AppService, Desktop,
  `LocalMemoryManager`, or existing memory commands.
- Dependencies: TASK-120.
- Completion criteria: completed by TASK-121; decisions are deterministic and
  serializable, secret-like inputs fail closed, and existing runtime behavior
  is unchanged.
- Published commit:
  `3336e4cac2595ba09313c7bde51692f0bd2c667f`.
- Last confirmed full suite: `2458 passed, 2 skipped in 8.76s`.

## Superseded Future Planning

The former unimplemented future sequence TASK-122 through TASK-139 was a
projected design sequence. None of those future task numbers was implemented
before this realignment. TASK-122 supersedes that numbering without rewriting
the completed TASK-113 through TASK-121 history. Historical task documents,
including the `Next Stages` section in `TASK-121.md`, remain records of the plan
at the time they were created; this document is the normative current sequence.

Provider adapters and their tests remain part of the project. Complex
consensus or multi-provider orchestration is frozen as a secondary capability
until a useful primary AI conversation exists. Earlier goal and planning ideas
are not cancelled; they move to an unnumbered deferred backlog until complete
user scenarios establish their requirements.

## Stage I - Truthful And Durable Core

### TASK-122 - Project Truth Baseline

- Purpose: align central documentation with the verified TASK-121 runtime and
  replace only the unimplemented future sequence.
- Main risk: presenting planned or injected behavior as default runtime truth.
- Dependencies: completed TASK-121 baseline.
- Completion criteria: exactly the approved documents state the current
  boundaries, the roadmap has one normative sequence, validation passes, and
  no runtime behavior changes.
- Explicit non-goals: runtime code, tests, dependencies, behavior, TASK-123
  implementation, commit, or push.

### TASK-123 - Default Conversation Persistence - Completed

- Purpose: wire the existing conversation repository into standard
  `launch_desktop_shell()` composition so bounded safe Desktop sessions can be
  reopened across launches.
- Main risk: persisting sensitive or corrupt turn data, or creating a second
  session owner.
- Dependencies: TASK-122 and existing TASK-115 persistence contracts.
- Completion criteria: default Desktop composition uses the approved local
  repository, restart/reopening behavior is tested, corruption fails safely,
  and `ConversationSessionService` remains authoritative.
- Validation: corrective full acceptance passed with
  `2476 passed, 2 skipped in 9.23s`; published as commit `88e7a4d`.
- Explicit non-goals: new memory storage, provider conversation, Desktop
  redesign, or execution behavior changes.

### TASK-124 - Desktop Interaction Worker and Shutdown - Completed

- Purpose: give long AI, document, and TTS operations one bounded Desktop
  worker lifecycle with clear cancellation and shutdown behavior.
- Main risk: UI freezes, orphaned workers, duplicate completion, or unsafe
  cancellation during side effects.
- Dependencies: TASK-123 and existing execution/cancellation boundaries.
- Completion criteria: Desktop remains responsive, operation identity is
  stable, shutdown is deterministic, and no work is silently abandoned or
  executed twice.
- Explicit non-goals: unattended background automation or forced process/thread
  termination.
- Historical pre-audit validation: full acceptance passed with
  `2500 passed, 2 skipped in 10.41s`.
- First audit remediation validation: the single post-remediation full acceptance
  passed with `2504 passed, 2 skipped in 20.64s`.
- Second audit remediation rejects cancellation after completion publication,
  distinguishes retained active metadata from cancellation availability, and
  makes non-daemon worker-test cleanup failure-safe. Its single full acceptance
  passed with `2506 passed, 2 skipped in 24.68s`.

### TASK-125 - Unified User Data and Persistence Health - Completed

- Purpose: define one authoritative user-data root and expose safe health for
  conversation, memory, configuration, and other local persistence.
- Main risk: current-working-directory dependence, accidental migration loss,
  or leaking private paths and data.
- Dependencies: TASK-123 and TASK-124.
- Completion criteria: supported launches resolve the same bounded user-data
  locations, migration/fallback behavior is explicit, DPAPI and filesystem
  adapter boundaries remain intact, and failures are safely observable.
- Validation: the single full acceptance passed with
  `2669 passed, 4 skipped in 13.41s` before the post-audit remediation; the
  single post-audit full acceptance passed with
  `2677 passed, 4 skipped in 18.42s`.
- Explicit non-goals: cloud sync, broad storage redesign, or deleting legacy
  user data.

### TASK-126 - Reproducible Environment and CI - Completed

- Purpose: add an approved dependency manifest, pytest configuration, and CI
  that reproduce the supported test baseline.
- Main risk: dependency drift or CI passing a materially different environment.
- Dependencies: TASK-125.
- Completion criteria: a clean supported environment can install declared
  dependencies and run the same required suite locally and in CI.
- Validation: controlled configuration RED `6 failed in 0.32s`; focused
  contract GREEN `6 passed in 0.07s`; clean-environment related regression
  `123 passed in 1.15s`; single clean-environment full acceptance
  `2683 passed, 4 skipped in 40.35s`.
- Explicit non-goals: automatic runtime downloads/installs, release packaging,
  or broad platform support claims.

## Stage II - Daily User Value

Real primary-provider-backed AI conversation begins only after default
persistence, the Desktop worker lifecycle, unified user-data paths, and a
reproducible environment are complete.

### TASK-127 - Real AI Conversation Vertical Slice - Completed

- Purpose: replace the ordinary compatibility-only answer path with one useful,
  explicitly gated primary-provider conversation path while retaining a safe
  deterministic fallback.
- Main risk: provider output crossing into execution, privacy/network/cost
  bypass, or regression of command/control routing.
- Dependencies: TASK-123 through TASK-126 and existing provider gates/adapters.
- Completion criteria: approved conversation calls the primary provider through
  existing gates, failures degrade safely, diagnostics stay separate, and
  generated response text is never executed.
- Explicit non-goals: autonomous tools, provider-owned domain state, or complex
  consensus/multi-provider orchestration.
- Implementation status: standard Desktop composition now uses the existing
  Groq gate with bounded safe context and deterministic compatibility fallback;
  direct AppService construction and legacy CLI compatibility behavior remain
  unchanged.
- Validation: expected missing-module RED with two collection errors; focused
  GREEN `56 passed in 1.13s`; related regression `437 passed in 2.69s`;
  compileall exit code `0`; single full acceptance
  `2696 passed, 4 skipped in 14.34s`.

### TASK-128 - Chat-First Desktop UX v1 - Completed

- Purpose: make sessions, response state, cancellation, retry, and persistence
  status clear through AppService DTOs.
- Main risk: Desktop becoming an execution or cognition owner.
- Dependencies: TASK-127.
- Completion criteria: the primary chat flow is usable and testable, injected
  state is projected through AppService, and unavailable/error states remain
  safe.
- Explicit non-goals: broad visual redesign, hidden automation, or direct
  Desktop imports of cognition/provider internals.
- Implementation status: completed, audit-remediated, and published at commit
  `612426d3e3aaed593c29ef16862a1ef6f1cf44f4`. AppService
  projects path-free chat session/response/retry/persistence state; Desktop
  presents a chat-first input/response/status flow and explicit eligible retry
  through the existing single worker without acquiring cognition, provider,
  persistence, or execution ownership.
- Validation so far: expected contract RED `2 errors in 1.92s`; focused GREEN
  `179 passed in 2.98s`; related regression `406 passed in 5.97s`; compileall
  exit code `0`; safe non-GUI fake-provider smoke passed; single full
  acceptance `2704 passed, 4 skipped in 27.16s`.
- Audit remediation: controlled RED `3 failed, 179 passed in 4.88s`; focused
  GREEN `182 passed in 5.44s`; related regression `427 passed in 8.35s`;
  compileall exit code `0`; safe non-GUI smoke passed. The pre-audit full result
  above is historical; the single post-audit full acceptance passed with
  `2707 passed, 4 skipped in 14.35s`.

## Stage A - Agentic Rebaseline And Measurement

### TASK-129 - Agentic Project Rebaseline & Legacy Freeze - Completed

- Purpose: make the approved full-personal-agent direction normative, replace
  only the old unimplemented TASK-129+ sequence, freeze literal-route growth,
  and classify legacy scaffolding without changing runtime behavior.
- Baseline: published TASK-128 commit
  `612426d3e3aaed593c29ef16862a1ef6f1cf44f4`.
- Implementation boundary: documentation and liveness audit only; no Agent
  Runtime, tools, planner, provider, memory, execution, or workflow changes.
- Liveness result: no file met the complete safe-deletion standard; empty
  unreferenced legacy placeholders remain delete-candidates, not removals.
- Completion criteria: one normative future sequence, TASK-130 next, completed
  history preserved, architecture ownership unchanged, validation green.
- Validation: roadmap structure check passed; focused architecture regression
  `32 passed in 0.92s`; single full acceptance
  `2707 passed, 4 skipped in 22.04s`; `git diff --check` exit code `0`.

### TASK-130 - Golden Agent Evals v1 - Completed And Audit Remediated

- Purpose: establish 25-30 representative goal-level evals and metrics for task
  success, tool choice, safety, recovery, duplicate effects, budgets, context,
  and verification.
- Main risk: optimizing architecture without measurable user-goal outcomes.
- Dependencies: TASK-129.
- Completion criteria: critical safety cases fail closed and future runtime work
  has a repeatable behavioral baseline.
- Explicit non-goals: Agent Runtime or new tool implementation.
- Implementation boundary: versioned offline catalog, reusable bounded eval
  runner, and public-AppService baseline adapter only; production runtime is
  unchanged.
- Baseline so far: 30 cases, 11 current goal successes, zero unsafe actions or
  duplicate side effects, four deterministic fake-model calls, one registered
  tool call, and unavailable token/cost/context/verifier signals kept explicit.
- Validation: focused GREEN `31 passed in 2.57s`; related regression
  `277 passed in 4.29s`; compileall exit code `0`; the single full repository
  acceptance passed with `2738 passed, 4 skipped in 28.22s`.
- Audit remediation: controlled RED `5 failed, 31 passed in 2.70s`; focused
  GREEN `37 passed in 2.42s`; related regression `283 passed in 4.05s`;
  compileall exit code `0`; safe offline smoke passed. The earlier full result
  is historical; the single post-remediation full acceptance passed with
  `2744 passed, 4 skipped in 22.05s`.

## Stage B - JARVIS Agent Runtime Foundation

### TASK-131 - Unified Tool Contract & Tool Registry v1

- Purpose: define one structured tool contract and registry covering schema,
  capability, side effects, risk, confirmation, reversibility, idempotency,
  data/network scope, budgets, and provenance.
- Boundary: adapt existing deterministic capabilities; do not create a second
  execution or workflow system.

### TASK-132 - Structured Capabilities, Scoped Permissions & Trust v1

- Purpose: evolve existing policy capabilities into structured, scoped
  permissions for agent runs.
- Boundary: natural-language phrases never grant tool permission.

### TASK-133 - Durable Agent Run Model & Repository

- Purpose: add a durable higher-level AgentRun owner for goals, criteria,
  plans, observations, linked operations, artifacts, approvals, budgets, and
  checkpoints.
- Boundary: `ExecutionJournal` remains the low-level operation journal.

### TASK-134 - Single-Agent Runtime Loop v1

- Purpose: implement one bounded `goal -> plan -> tool -> policy -> act ->
  observe` cycle through existing safety and execution owners.
- Boundary: no multi-agent behavior and no executable tool-output instructions.

### TASK-135 - Planner v2: Short-Horizon Goal Planning

- Purpose: add model-assisted next-step planning over registered tools while
  keeping the deterministic planner as a compatibility path.
- Boundary: planning never grants execution permission.

### TASK-136 - Verifier, Replanner & Runtime Budgets

- Purpose: separate goal verification from tool success, add bounded replanning,
  and enforce step/call/retry/token/cost/runtime budgets.
- Completion criteria: the first full plan/act/observe/verify/replan loop is
  measurable by Golden Agent Evals.

### TASK-137 - Context Manager & Provenance v1

- Purpose: select high-signal context just in time and label system, user,
  memory, tool, and external/untrusted sources.
- Boundary: external content remains data and never gains instruction authority.

## Stage C - Real Autonomous User Value

### TASK-138 - Artifact Registry & Safe Workspace

- Purpose: give generated/received artifacts stable identity, provenance,
  version/location, creator run, and input/output relationships.

### TASK-139 - File & Document Agent Vertical Slice

- Purpose: complete bounded multi-step work over explicitly approved documents
  with provenance, injection resistance, safe artifacts, and final verification.

### TASK-140 - Spreadsheet & Registry Agent

- Purpose: inspect and transform approved structured data while preserving
  sources, validating outputs, and preventing formula injection/overwrite.

### TASK-141 - Official Drafting Agent

- Purpose: create sourced, reviewable official/business draft artifacts without
  automatic transmission, signing, or submission.

### TASK-142 - External Research Agent

- Purpose: perform explicitly scoped web research with visible network use,
  source provenance/freshness, privacy gates, and untrusted-content handling.

### TASK-143 - MCP Adapter & Dynamic Tool Discovery

- Purpose: discover a bounded tool shortlist by capability and support external
  tool ecosystems without building a proprietary MCP replacement.

### TASK-144 - Pause, Resume & Restart Recovery

- Purpose: recover durable AgentRuns using explicit resume/restart/revise/
  abandon decisions while preserving approvals, idempotency, and budgets.
- Boundary: risky interrupted steps are never automatically replayed.

### TASK-145 - JARVIS Agentic Runtime v1 Acceptance

- Purpose: use Golden Agent Evals to prove safe completion of meaningful
  multi-step user goals.
- Milestone: **JARVIS Agentic Runtime v1**.

## Stage D - Memory, Knowledge And Intelligence Routing

### TASK-146 - MemoryService Read + Agent Context

- Purpose: expose existing memory through bounded, provenance-bearing reads
  without creating a second memory store.

### TASK-147 - Explicit Memory Command Migration

- Purpose: migrate explicit remember/recall/list/forget flows while preserving
  preview/execute parity, confirmation, and storage compatibility.

### TASK-148 - Memory Candidates & Approval

- Purpose: permit inferred facts only as expiring `MemoryPolicy` candidates;
  persist nothing inferred before explicit approval.

### TASK-149 - Personal Knowledge Workspace

- Purpose: retrieve from approved documents, artifacts, and safe memory
  summaries with provenance and freshness; no whole-disk indexing by default.

### TASK-150 - Model Capability Router

- Purpose: select replaceable GPT, Gemini, Groq, local, or future models by
  capability and policy beneath JARVIS-owned orchestration.

## Stage E - Deep Environment Integration

### TASK-151 - Windows Computer Tools v1

- Purpose: add bounded, permission-scoped local computer tools for approved
  file, application, and system interactions, preferring structured APIs over
  unconstrained GUI automation.

### TASK-152 - Browser Interaction v1

- Purpose: add explicit browser interaction with provenance, domain/permission
  limits, and strong prompt-injection boundaries.

### TASK-153 - Email & Calendar Connectors

- Purpose: read and draft first; send/create/update actions remain separate,
  policy-gated, and visibly confirmed.

### TASK-154 - Voice Agent v2

- Purpose: unify voice goals with Agent Runtime and conversation/run state
  without creating a weaker execution authorization path.

### TASK-155 - Durable Scheduled Tasks

- Purpose: add user-created schedules only after durable AgentRun/recovery
  semantics exist; scheduling never becomes independent execution authority.

### TASK-156 - Opt-In Proactive Agent

- Purpose: add consent-bound suggestions and monitoring with dismiss, snooze,
  and disable controls; hidden consequential actions remain prohibited.

### TASK-157 - Multi-Agent, Only If Evals Prove Benefit

- Purpose: permit specialist subagents only when Golden Evals demonstrate a
  measurable reliability benefit that justifies complexity and cost.

### TASK-158 - Installer, Backup, Upgrade & Security Audit

- Purpose: package the proven system and define safe backup, migration,
  recovery, security, and permission behavior before broader release.

### TASK-159 - JARVIS Personal Agent v1 Stabilization

- Purpose: stabilize the accepted runtime, tools, memory, recovery,
  integrations, packaging, and Golden Agent Task results without scope growth.

### TASK-160 - JARVIS Personal Agent v1 Release

- Purpose: release the first serious personal-agent product line only after all
  stabilization and acceptance gates pass.

## Progress Gate

From TASK-130 onward, each task must measurably improve a Golden Agent Task,
enable a named Golden Agent Task, remove a demonstrated safety/reliability
bottleneck, or reduce legacy complexity without breaking behavior. New
abstractions are not milestones by themselves. Multi-agent work remains deferred
until evals prove benefit, and literal-route growth remains frozen.
