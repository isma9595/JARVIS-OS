# JARVIS Roadmap

Status: verified code baseline through TASK-121; future sequence realigned by
TASK-122. This roadmap begins after the completed execution/workflow platform
milestone and the TASK-112 cognitive architecture report. It records completed
TASK-113 through TASK-121 history and defines the current product sequence from
TASK-122 onward.

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

### TASK-125 - Unified User Data and Persistence Health

- Purpose: define one authoritative user-data root and expose safe health for
  conversation, memory, configuration, and other local persistence.
- Main risk: current-working-directory dependence, accidental migration loss,
  or leaking private paths and data.
- Dependencies: TASK-123 and TASK-124.
- Completion criteria: supported launches resolve the same bounded user-data
  locations, migration/fallback behavior is explicit, DPAPI and filesystem
  adapter boundaries remain intact, and failures are safely observable.
- Explicit non-goals: cloud sync, broad storage redesign, or deleting legacy
  user data.

### TASK-126 - Reproducible Environment and CI

- Purpose: add an approved dependency manifest, pytest configuration, and CI
  that reproduce the supported test baseline.
- Main risk: dependency drift or CI passing a materially different environment.
- Dependencies: TASK-125.
- Completion criteria: a clean supported environment can install declared
  dependencies and run the same required suite locally and in CI.
- Explicit non-goals: automatic runtime downloads/installs, release packaging,
  or broad platform support claims.

## Stage II - Daily User Value

Real primary-provider-backed AI conversation begins only after default
persistence, the Desktop worker lifecycle, unified user-data paths, and a
reproducible environment are complete.

### TASK-127 - Real AI Conversation Vertical Slice

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

### TASK-128 - Chat-First Desktop UX v1

- Purpose: make sessions, response state, cancellation, retry, and persistence
  status clear through AppService DTOs.
- Main risk: Desktop becoming an execution or cognition owner.
- Dependencies: TASK-127.
- Completion criteria: the primary chat flow is usable and testable, injected
  state is projected through AppService, and unavailable/error states remain
  safe.
- Explicit non-goals: broad visual redesign, hidden automation, or direct
  Desktop imports of cognition/provider internals.

### TASK-129 - Document Intake v1

- Purpose: accept bounded approved documents through the filesystem adapter and
  make their extracted content available to a visible user-requested workflow.
- Main risk: reading unrelated/private files, unbounded content, or treating
  document text as executable instructions.
- Dependencies: TASK-124 through TASK-128.
- Completion criteria: supported files are selected explicitly, bounded,
  provenance-labelled, and processed without source mutation or hidden network
  access.
- Explicit non-goals: recursive drive indexing, arbitrary format support, or
  automatic document actions.

### TASK-130 - Official Drafting Workflow

- Purpose: provide a reviewable workflow for drafting official text from
  user-approved context and sources.
- Main risk: fabricated facts, hidden transmission, or overwriting source
  documents.
- Dependencies: TASK-127 through TASK-129.
- Completion criteria: drafts retain source/provenance context, require user
  review, save only through approved filesystem behavior, and are never sent
  automatically.
- Explicit non-goals: email sending, e-signature, filing, or autonomous
  submission.

### TASK-131 - Spreadsheet and Registry Reports

- Purpose: produce bounded, reviewable spreadsheet/registry-style reports from
  explicitly supplied local data.
- Main risk: formula injection, malformed data, silent overwrite, or inaccurate
  aggregation.
- Dependencies: TASK-129 and TASK-130.
- Completion criteria: inputs and output destination are explicit, generated
  artifacts are validated, sources are preserved, and no external transmission
  occurs.
- Explicit non-goals: live enterprise-system integration or unattended report
  distribution.

## Stage III - Memory And Knowledge

### TASK-132 - MemoryService Read Adapter

- Purpose: expose existing memory through bounded cognitive read/recall
  contracts while preserving one storage owner and provenance.
- Main risk: creating a second memory store or exposing secret/private values.
- Dependencies: TASK-127 and the TASK-121 `MemoryPolicy` contract.
- Completion criteria: approved reads use existing records, fail safely when
  unavailable, preserve provenance, and do not give `MemoryPolicy` storage
  ownership.
- Explicit non-goals: memory writes, inferred candidates, or command migration.

### TASK-133 - Memory Command Migration

- Purpose: route explicit remember, recall, list, forget, and forget-all flows
  through the cognitive memory service without changing visible safety.
- Main risk: breaking preview/execute parity, confirmation, idempotency, or
  current storage compatibility.
- Dependencies: TASK-132.
- Completion criteria: existing commands retain behavior and metadata through
  the new service boundary, and destructive forgetting still requires the
  established confirmation path.
- Explicit non-goals: inferred writes or automatic fact extraction.

### TASK-134 - Memory Candidates and Approval

- Purpose: represent inferred personal-memory writes as bounded candidates that
  require `MemoryPolicy` evaluation and explicit approval.
- Main risk: silently persisting inferred or secret personal data.
- Dependencies: TASK-133.
- Completion criteria: candidates expire safely, secrets are rejected,
  approval is explicit and target-bound, and no inferred fact persists before
  approval.
- Explicit non-goals: autonomous profile building or provider-owned memory.

### TASK-135 - Local Knowledge Workspace

- Purpose: retrieve from explicitly approved local documents and memory
  summaries with source, timestamp, freshness, and confidence metadata.
- Main risk: scanning unrelated files or treating retrieval as authoritative
  truth.
- Dependencies: TASK-129, TASK-132, and TASK-134.
- Completion criteria: source boundaries are explicit, retrieval is local and
  provenance-bearing, stale/unavailable sources are visible, and no duplicate
  durable memory store is created.
- Explicit non-goals: whole-disk indexing, embeddings by default, or hidden
  network access.

### TASK-136 - External Research Gate

- Purpose: add an explicit permission, privacy, and network gate for
  user-requested external research.
- Main risk: hidden network access, private-context disclosure, or unsourced
  answers.
- Dependencies: TASK-127, TASK-135, and existing provider/privacy gates.
- Completion criteria: each external research action is explicit, scoped,
  observable, and provenance-bearing; denial or provider failure is safe.
- Explicit non-goals: background browsing, automatic research, or direct
  execution from retrieved content.

## Stage IV - Long-Task Reliability

### TASK-137 - Durable Operation and Workflow Summaries

- Purpose: persist bounded safe summaries and linkage for operations and
  workflows without duplicating execution authority.
- Main risk: claiming recoverability from incomplete summaries or persisting
  sensitive arguments.
- Dependencies: TASK-124 through TASK-126 and proven daily workflows.
- Completion criteria: durable summaries have stable identity, safe metadata,
  explicit terminal/interrupted states, and remain projections rather than
  execution owners.
- Explicit non-goals: automatic replay, unattended automation, or persistence
  of raw secrets.

### TASK-138 - Restart Recovery

- Purpose: define and implement safe recovery decisions for interrupted
  operations/workflows after restart.
- Main risk: duplicate side effects, stale approvals, or resuming an
  incompatible workflow.
- Dependencies: TASK-137.
- Completion criteria: recovery distinguishes resume, restart, revise, and
  abandon; user approval and idempotency are preserved; unsafe recovery fails
  closed.
- Explicit non-goals: universal process checkpointing or automatic resume of
  risky actions.

### TASK-139 - Routing Consolidation

- Purpose: consolidate remaining user-facing routes behind the established
  AppService cognitive and execution boundaries after durable recovery exists.
- Main risk: changing legacy behavior or creating a second authorization path.
- Dependencies: TASK-127, TASK-133, and TASK-138.
- Completion criteria: supported Desktop/CLI routes have explicit semantic
  ownership, compatibility paths remain covered, and safety/confirmation/
  cancellation/idempotency invariants are unchanged.
- Explicit non-goals: deleting provider adapters/tests or enabling autonomous
  execution.

Automation is not scheduled before TASK-137 and TASK-138 establish durable
operation and recovery semantics.

## Stage V - Expansion After Proven Daily Value

The exact architecture of TASK-140 through TASK-144 is not yet approved. These
entries constrain intent and order only.

### TASK-140 - Voice Dictation and Accessibility

High-level scope: improve explicit voice dictation and accessibility after the
chat-first workflows are stable. Always-on microphone listening and hidden
execution remain out of scope.

### TASK-141 - Email and Calendar Connectors

High-level scope: add explicit connector boundaries for reading and drafting.
Sending email and creating calendar events must remain separate, visible,
individually confirmed actions.

### TASK-142 - Reminders and Scheduled Tasks

High-level scope: add user-created reminders and scheduled proposals only after
durable operation/recovery exists. Scheduling must not become execution
authority.

### TASK-143 - Opt-In Proactive Suggestions

High-level scope: consent-bound suggestions with dismiss/snooze controls.
Proactive behavior is disabled by default and never executes hidden actions.

### TASK-144 - Installer, Upgrade, Backup and Release Audit

High-level scope: package the proven product, define safe upgrade/backup
behavior, and perform the full audit required before public release or other
dangerous external capabilities.

## Deferred Backlog

Goal services, cognitive planning, plan approval models, and other earlier
planning concepts remain valid design ideas but are intentionally unnumbered
until completed user scenarios demonstrate their requirements. Provider
adapters and tests are retained. Complex multi-provider consensus remains a
secondary option, not a near-term milestone.
