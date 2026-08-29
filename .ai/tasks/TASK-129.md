# TASK-129 — Agentic Project Rebaseline & Legacy Freeze

## Status

Completed in the unstaged worktree on the published TASK-128 baseline. Runtime
behavior is unchanged. Staging, commit, and push were not performed.

## Objective

Realign the normative JARVIS OS roadmap around the approved full-personal-agent
product goal without implementing that future runtime in this task.

JARVIS is intended to become a goal-driven, tool-using, verifiable, resumable,
model-independent personal AI agent. GPT, Gemini, Groq, local models, and future
models remain replaceable intelligence engines beneath JARVIS-owned context,
memory, permissions, tools, execution, provenance, persistence, and
verification.

TASK-129 is documentation/audit focused. It does not implement Agent Runtime,
Tool Registry, Planner v2, new execution behavior, memory integration, document
tools, or new user-facing automation.

## Verified Baseline

- Published dependency: TASK-128 — Chat-First Desktop UX v1.
- Baseline commit: `612426d3e3aaed593c29ef16862a1ef6f1cf44f4`.
- Baseline tree: `a2133d563993b1e88b9e3a7c6d27de86f3bf259b`.
- Branch and remote-tracking branch: `main` and `origin/main`, equal at
  preflight.
- Origin: `https://github.com/isma9595/JARVIS-OS.git`.
- Baseline worktree and staging: clean.
- TASK-128 full acceptance: `2707 passed, 4 skipped in 14.35s`.

## Architecture Boundary

The existing safety kernel remains authoritative:

- `JarvisAppService` remains the application facade;
- cognition and `ConversationSessionService` retain conversation/session
  ownership;
- `ExecutionCoordinator` and `ExecutionJournal` retain operation ownership;
- `PolicyDecisionBoundary` and `PolicyCapability` retain policy authority;
- `WorkflowRunner` retains deterministic workflow ownership;
- provider privacy, credential, cost/model, and network gates remain in place;
- confirmation, cancellation, idempotency, persistence, and regression
  boundaries do not change.

Future Agent Runtime work must orchestrate these boundaries. It must not bypass
or duplicate them.

## Normative Future Sequence

`docs/AGENTIC_ROADMAP_V1.md` is the approved strategic roadmap. TASK-129 makes
its TASK-129 through TASK-160 sequence the only normative future numbering in
`docs/ROADMAP.md`. Only the old, unimplemented TASK-129+ sequence is
superseded. Completed TASK history and completed task records remain intact.

The next implementation task is TASK-130 — Golden Agent Evals v1.

## Legacy Freeze

The following components remain compatibility layers unless a specifically
approved migration task changes them:

- growth of literal phrase routing in `CommandProcessor`;
- growth of legacy passthrough tables in `CommandResolutionService`;
- growth of the deterministic `MultiStepPlanner` phrase grammar;
- complex multi-provider consensus as a near-term product priority.

New user capabilities must be introduced through the future Agent Runtime and
Tool Registry boundaries, or through an existing deterministic workflow when
that is safer. They must not be implemented primarily by adding more literal
phrases to legacy routing.

## Liveness Audit

The audit was read-only and covered tracked Python file sizes, zero/small-file
inventory, placeholder markers, import/name references, documentation/history
references, and surrounding implementation context.

Findings:

- empty `core/system_info.py` is still named by the historical TASK-011
  requirements traceability record;
- empty files under `database/versioning/`, `language/`, and `security/` are
  speculative legacy placeholders with no live imports found;
- zero/short `__init__.py` files are package/namespace markers;
- `...` occurrences in provider and secure-key modules are Protocol method
  bodies;
- standalone `pass` occurrences reviewed are exception classes or bounded
  failure-handling branches in active modules;
- Vosk `stub` names describe an intentional safe disabled runtime boundary that
  has live command/dialogue references;
- planner capability and workflow components contain implemented behavior and
  are covered by current architecture/tests.

No file met the full deletion standard of having no runtime, test,
documentation, migration, package, or compatibility effect. Therefore TASK-129
deletes no source file. The unreferenced empty legacy placeholders are recorded
as delete-candidates for a later task with explicit compatibility evidence;
they are not silently removed during the roadmap rebaseline.

## Module Classification

### Keep

- cognition/conversation core and conversation persistence;
- Desktop interaction worker and chat-first AppService projection;
- unified user-data paths and persistence health;
- `MemoryPolicy` foundation;
- `ExecutionCoordinator` and `ExecutionJournal`;
- `PolicyDecisionBoundary` and `PolicyCapability`;
- `WorkflowRunner` and proven deterministic workflows;
- provider gates and privacy/cost/credential boundaries;
- CI and the regression suite.

### Freeze

- `CommandProcessor` literal-command growth;
- `CommandResolutionService` legacy passthrough growth;
- deterministic `MultiStepPlanner` phrase-grammar growth;
- complex multi-provider consensus as a near-term priority.

### Deprecate Direction

- direct legacy CLI/`CommandProcessor` routing after equivalent behavior is
  covered by Agent Runtime evals and an explicitly approved migration;
- legacy voice/passthrough entry paths after the AppService-owned replacement
  is proven and compatibility tests exist;
- duplicated routing surfaces only after their replacement owns the full
  contract and rollback path.

Deprecation is directional only in TASK-129. No runtime path is disabled or
removed.

### Delete-Candidate

- empty, unreferenced legacy placeholders under `database/versioning/`,
  `language/`, and `security/`;
- other empty scaffolding only if a future audit proves absence of runtime,
  package, test, documentation, migration, and compatibility dependencies.

No delete-candidate is deleted by TASK-129.

## Do Not Create

- a second execution coordinator;
- a second workflow engine;
- a second memory store;
- a second independent capability/security model;
- a multi-agent architecture;
- a proprietary MCP replacement.

## Approved File Scope

- `.ai/tasks/TASK-129.md`;
- `docs/AGENTIC_ROADMAP_V1.md`;
- `.ai/CHECKPOINT.md`;
- `README.md`;
- `docs/ARCHITECTURE.md`;
- `docs/ROADMAP.md`;
- `docs/architecture/COGNITIVE_ARCHITECTURE.md`.

No production code, test code, dependency, CI, or configuration file is in
scope.

## Out Of Scope

- Agent Runtime, Tool Registry, Planner v2, Verifier, AgentRun repository, or
  context manager implementation;
- new provider, network, voice, filesystem, memory, execution, or workflow
  behavior;
- document/spreadsheet/browser/email/calendar/computer tools;
- multi-agent orchestration or unrestricted autonomy;
- deletion without complete liveness and compatibility evidence;
- staging, commit, or push.

## Acceptance Criteria

- runtime behavior is unchanged;
- central documentation contains exactly one normative future numbering
  sequence;
- TASK-130 is the next implementation task;
- completed TASK history remains intact;
- legacy literal-routing growth is explicitly frozen;
- module keep/freeze/deprecate/delete-candidate decisions and liveness evidence
  are recorded;
- existing execution, policy, confirmation, cancellation, idempotency,
  workflow, persistence, provider-privacy, and test boundaries are preserved;
- relevant documentation/architecture checks pass;
- one final full pytest run passes;
- `git diff --check` passes;
- staging remains empty; commit and push require later explicit approval.

## Validation

- Roadmap structure check: TASK-129 through TASK-160 appears once, uniquely and
  sequentially; no superseded future task title remains in central status docs.
- Focused architecture regression:
  `32 passed in 0.92s`.
- Single full repository acceptance:
  `2707 passed, 4 skipped in 22.04s`.
- `git diff --check`: exit code `0`; Git emitted only ordinary potential
  LF-to-CRLF conversion warnings, with no whitespace errors.
- No runtime, test, dependency, CI, or configuration file was changed.

## Next Stage

TASK-130 — Golden Agent Evals v1.
