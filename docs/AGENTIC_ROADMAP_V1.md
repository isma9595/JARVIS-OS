# JARVIS OS — Agentic Roadmap v1

Status: normative strategic roadmap from TASK-129 onward on the published
TASK-128 baseline.

This document records the approved product direction for JARVIS OS after
TASK-128. It does not rewrite completed historical TASK records or claim that
future Agent Runtime capabilities are implemented. `docs/ROADMAP.md` is the
canonical implementation-status and task-numbering record; this document is the
strategic architecture roadmap that governs its TASK-129+ sequence.

## Product Goal

JARVIS OS is to become a full personal AI agent, not only a conversational
assistant.

The target system must be able to:

- accept a user goal rather than requiring a sequence of literal commands;
- decompose a goal into bounded steps;
- select appropriate tools and deterministic workflows;
- execute through existing policy, confirmation, cancellation, idempotency,
  and execution boundaries;
- observe tool results and failures;
- verify whether the user goal was actually achieved;
- replan when the result is incomplete or a step fails;
- use working, session, episodic, and approved long-term memory without
  creating duplicate ownership;
- preserve provenance and distinguish trusted instructions from
  external/untrusted content;
- pause and safely resume long-running work;
- remain model-independent so GPT, Gemini, Groq, local models, and future models
  can be interchangeable intelligence engines.

The strategic objective is not to train a foundation model that beats GPT or
Gemini on every general benchmark. It is to make JARVIS more useful in the
user's real environment by combining strong models with superior local context,
memory, tools, workflows, permissions, verification, and deep computer
integration.

## Architecture Principles

1. Keep the existing safety kernel. `ExecutionCoordinator`,
   `PolicyDecisionBoundary`, confirmation/cancellation semantics, idempotency,
   `WorkflowRunner`, persistence boundaries, and AppService ownership remain
   authoritative.
2. Do not create a second execution system. Agent Runtime must orchestrate
   existing execution/workflow boundaries rather than bypass or duplicate them.
3. Do not create a second capability/security system. Existing
   `PolicyCapability` concepts are evolved into structured scoped permissions.
4. Freeze legacy literal routing. New user capabilities must not be implemented
   by continuously expanding `CommandProcessor` literal phrase tables.
5. Keep deterministic workflows where they are better. Not every request should
   use an LLM agent loop.
6. One agent first. Multi-agent architecture is deferred until evaluations
   prove a measurable benefit.
7. Short-horizon planning. Planner v2 plans the next useful bounded steps and
   replans from observations instead of predicting a long rigid sequence.
8. Verification is separate from execution. Tool success is not equivalent to
   user-goal success.
9. Context is selected just in time. Do not dump all history, memory, tools, or
   documents into every model call.
10. External content is data, not authority. Documents, webpages, emails, and
    tool output carry provenance/trust labels and cannot silently become
    system/user instructions.
11. Dynamic tool discovery. Large tool libraries are filtered by required
    capabilities before model exposure.
12. Real user outcomes are the progress metric. TASK count is secondary to
    Golden Agent Tasks and measurable task-success rate.

## Keep / Freeze / Deprecate Direction

### Keep and build on

- cognition and conversation architecture from TASK-113 through TASK-120;
- `ConversationSessionService` and safe conversation persistence;
- TASK-124 Desktop interaction worker and shutdown boundary;
- TASK-125 unified user-data paths and persistence health;
- TASK-121 `MemoryPolicy` foundation;
- provider gates and privacy/cost/credential boundaries;
- `ExecutionCoordinator` and `ExecutionJournal` as low-level execution
  primitives;
- `PolicyDecisionBoundary` and `PolicyCapability` as the starting safety model;
- `WorkflowRunner` for deterministic workflows;
- CI and the existing regression suite.

### Freeze as compatibility layers

- `CommandProcessor` literal-command growth;
- `CommandResolutionService` legacy passthrough expansion;
- current deterministic `MultiStepPlanner` phrase grammar;
- complex multi-provider consensus as a near-term priority.

These components are not deleted immediately. Existing behavior remains covered
by regression tests while new capabilities are built through Agent Runtime and
Tool Registry.

### Deprecate after proven replacement

- direct legacy CLI/`CommandProcessor` routing;
- legacy voice and passthrough entry paths that duplicate the AppService-owned
  path;
- duplicated routing surfaces.

Deprecation requires a named migration task, equivalent behavior, eval evidence,
compatibility tests, and a safe rollback boundary. TASK-129 disables none of
these paths.

### Audit for deletion

TASK-129 audited empty or speculative scaffolding. Empty unreferenced legacy
placeholders remain delete-candidates, but no file was removed because none was
proven free of runtime, package, test, documentation, migration, and
compatibility effects. No broad deletion is allowed without that evidence.

# Roadmap

## Published Foundation

TASK-129 — Agentic Project Rebaseline & Legacy Freeze is published at commit
`8d6b4087944b6698d82467589cd35e73f09cf4b1`. Its tree
`a0b98bcaf4a9d0f1f96eecae42e6b29ac419347b` and the existing runtime/safety
owners remain the baseline for TASK-130.

## Stage A — Agentic Rebaseline and Measurement

### TASK-129 — Agentic Project Rebaseline & Legacy Freeze

Purpose:

- formally replace the old unimplemented future TASK-129+ sequence with this
  agent-first roadmap;
- classify major architecture areas as keep/freeze/deprecate/delete-candidate;
- freeze new literal-routing growth;
- perform dead/scaffolding liveness audit;
- update central documentation to the new product goal without changing runtime
  behavior.

Historical completed TASK files are not rewritten.

### TASK-130 — Golden Agent Evals v1 — COMPLETED

Create the first real behavioral evaluation suite instead of relying only on
unit/integration tests.

Initial target: 25–30 representative user goals.

Metrics:

- task success rate;
- correct tool selection rate;
- unsafe action rate;
- unnecessary confirmation rate;
- human intervention rate;
- recovery rate;
- duplicate side-effect rate;
- average steps;
- model/tool call count;
- token/cost budget;
- context precision;
- verifier accuracy.

Critical safety scenarios must be fail-closed.

Implementation boundary: the first suite is offline and deterministic, uses a
versioned 30-case catalog and public AppService contracts, and adds no runtime
tools or agent loop. Contract compliance and actual task success are separate
metrics. Signals that current runtime cannot observe reliably remain explicitly
unavailable.

Validation completed with focused `31 passed in 2.57s`, related
`277 passed in 4.29s`, and the single full repository acceptance
`2738 passed, 4 skipped in 28.22s`. A subsequent read-only audit required an
eval-only repair for outcome derivation, duplicate-call detection, active
offline guards, failure denominators, and safe error chaining. Remediation
focused `37 passed in 2.42s`, related `283 passed in 4.05s`, and compileall exit
`0`; the single post-remediation full acceptance passed with
`2744 passed, 4 skipped in 22.05s`. TASK-131 remains the next stage.

## Stage B — JARVIS Agent Runtime Foundation

### TASK-131 — Unified Tool Contract & Tool Registry v1

Define one structured tool contract covering tool identity, schemas, required
capabilities, side-effect class, risk, confirmation, reversibility,
idempotency, network/data scope, budgets, and provenance/trust metadata.

Existing deterministic planner/workflow capabilities should be exposed through
adapters where useful rather than reimplemented.

### TASK-132 — Structured Capabilities, Scoped Permissions & Trust v1

Evolve existing `PolicyCapability` into structured, scoped permissions usable
by agent runs. File, network, process, destructive, and irreversible actions
must have explicit scope and policy. Natural-language phrases are never the
authoritative source of a tool's permission requirements.

### TASK-133 — Durable Agent Run Model & Repository

Introduce a durable higher-level `AgentRun` entity separate from low-level
`ExecutionOperation`. It covers goal, success criteria, status, plan/step,
observations, linked operation ids, artifacts, approvals, budgets, checkpoints,
timestamps, and safe failure state.

`ExecutionJournal` remains the low-level operation journal; it is not silently
repurposed into the AgentRun owner.

### TASK-134 — Single-Agent Runtime Loop v1

Implement the first bounded agent cycle:

`goal -> plan -> select tool -> policy -> act -> observe -> continue`

All side effects use existing safety/execution boundaries; tool output is not
executed as instructions; cancellation stays authoritative; every run has
explicit budgets; multi-agent behavior is excluded.

### TASK-135 — Planner v2: Short-Horizon Goal Planning

Add model-assisted goal planning above the deterministic compatibility planner.
Planner v2 derives a small next-step plan from the goal and observations,
selects only registered tools/capabilities, avoids long rigid plans, and never
grants execution permission.

### TASK-136 — Verifier, Replanner & Runtime Budgets

Separate goal verification from tool execution. Add explicit success criteria,
verification outcomes, replan/fail paths, and maximum steps, tool/model calls,
retries, tokens, cost, and runtime.

This completes the first full loop:

`goal -> plan -> act -> observe -> verify -> replan/complete`.

### TASK-137 — Context Manager & Provenance v1

Create a context assembly layer that selects high-signal runtime context and
distinguishes system policy, direct user instruction, approved memory, trusted
tool metadata, tool results, and external/untrusted content. External content
never gains instruction authority from imperative text.

## Stage C — Real Autonomous User Value

### TASK-138 — Artifact Registry & Safe Workspace

Create first-class artifact identity for generated/received files and outputs,
including type, provenance, creator run, version/location, safe metadata, and
input/output relationships.

### TASK-139 — File & Document Agent Vertical Slice

Deliver the first serious autonomous vertical slice over user-approved files:
bounded extraction, provenance, prompt-injection-resistant document handling,
tool-driven multi-step work, and final verification.

### TASK-140 — Spreadsheet & Registry Agent

Add structured spreadsheet/data tools for inspecting, filtering, sorting,
matching, and aggregating approved data while preserving sources, validating
artifacts, and preventing formula injection or overwrite.

### TASK-141 — Official Drafting Agent

Generate official/business drafts from approved sources and structured facts,
retain provenance, avoid fabricated source claims, create explicit artifacts,
and require user review before transmission, signing, or submission.

### TASK-142 — External Research Agent

Add explicit scoped web research through Agent Runtime with visible network use,
source provenance/freshness, private-context disclosure gates, and untrusted
content handling. Web instructions never trigger autonomous execution.

### TASK-143 — MCP Adapter & Dynamic Tool Discovery

Support external tool ecosystems through capability search and a bounded tool
shortlist. Do not build a proprietary MCP replacement unless a concrete
requirement proves it necessary.

### TASK-144 — Pause, Resume & Restart Recovery

Make durable AgentRuns recoverable across restart. Recovery distinguishes
resume/restart/revise/abandon and preserves approvals, idempotency, budgets, and
side-effect safety. Risky interrupted steps do not automatically replay.

### TASK-145 — JARVIS Agentic Runtime v1 Acceptance

Use Golden Agent Evals to prove independent completion of a meaningful set of
multi-step user goals while preserving all critical safety invariants.

Milestone name: **JARVIS Agentic Runtime v1**.

## Stage D — Memory, Knowledge and Intelligence Routing

### TASK-146 — MemoryService Read + Agent Context

Expose existing memory through bounded, provenance-bearing cognitive/agent
reads without introducing a second memory store.

### TASK-147 — Explicit Memory Command Migration

Move explicit remember/recall/list/forget flows through the memory service while
preserving preview/execute parity, confirmation, and storage compatibility.

### TASK-148 — Memory Candidates & Approval

Allow inferred personal facts only as expiring candidates evaluated by
`MemoryPolicy`; persist nothing inferred before explicit approval.

### TASK-149 — Personal Knowledge Workspace

Combine approved local documents, artifacts, and safe memory summaries into
provenance-bearing retrieval with freshness metadata. Whole-disk indexing and
hidden data collection remain disabled by default.

### TASK-150 — Model Capability Router

Route intelligence by model capability and policy rather than one default
model. GPT, Gemini, Groq, Ollama/local, and future models remain replaceable
engines beneath JARVIS-owned orchestration.

## Stage E — Deep Environment Integration

### TASK-151 — Windows Computer Tools v1

Add bounded, permission-scoped local tools for approved file, application, and
system interactions. Prefer structured APIs over unconstrained GUI automation.

### TASK-152 — Browser Interaction v1

Add explicit browser interaction with provenance, domain/permission limits, and
strong prompt-injection boundaries.

### TASK-153 — Email & Calendar Connectors

Read and draft first. Consequential send/create/update actions remain separate,
policy-gated, and visibly confirmed.

### TASK-154 — Voice Agent v2

Unify voice goals with Agent Runtime and conversation/run state without
creating a weaker execution authorization path.

### TASK-155 — Durable Scheduled Tasks

Introduce user-created schedules only on durable AgentRun/recovery semantics.
Scheduling does not become independent execution authority.

### TASK-156 — Opt-In Proactive Agent

Add consent-bound proactive suggestions and monitoring with clear dismiss,
snooze, and disable controls. Hidden consequential actions remain prohibited.

### TASK-157 — Multi-Agent, Only If Evals Prove Benefit

Introduce specialist subagents only if Golden Evals demonstrate a measurable
quality/reliability benefit that justifies added complexity and cost.

### TASK-158 — Installer, Backup, Upgrade & Security Audit

Package the proven system, define backup/migration/recovery, and perform a
security and permission audit before broader release.

### TASK-159 — JARVIS Personal Agent v1 Stabilization

Stabilize the agent runtime, tools, memory, recovery, integration, packaging,
and Golden Agent Task results without expanding scope.

### TASK-160 — JARVIS Personal Agent v1 Release

Release the first serious personal-agent product line after the stabilization
and acceptance gates pass.

Target experience: the user states a goal, JARVIS safely plans and executes the
necessary multi-step work, explains consequential approvals, verifies the
result, creates usable artifacts, and can resume durable work after interruption.

## Progress Gates

From TASK-130 onward, each architectural task must satisfy at least one of these
conditions:

1. measurably increases Golden Agent Task success;
2. is a required dependency for a named Golden Agent Task;
3. removes a demonstrated reliability/safety bottleneck;
4. materially reduces legacy complexity without breaking behavior.

A task should not be added solely to introduce a new `Manager`, `Coordinator`,
`Service`, abstraction, or speculative future layer.

## Explicit Non-Goals Until Proven Necessary

- training a new frontier foundation model;
- fully autonomous unrestricted computer control;
- hidden execution;
- multi-agent swarms;
- whole-disk indexing by default;
- automatic memory of everything;
- loading the entire tool catalog into every prompt;
- rewriting the application from scratch;
- replacing deterministic workflows with LLM calls when deterministic behavior
  is safer;
- deleting legacy components before replacement behavior is proven by
  tests/evals.

## Success Definition

JARVIS is on the correct path when progress is visible primarily as an increase
in reliably completed real user goals rather than TASK count or internal
architecture layers.

The defining loop is:

`GOAL -> CONTEXT -> PLAN -> TOOL -> POLICY -> ACT -> OBSERVE -> VERIFY -> REPLAN/COMPLETE`

All model intelligence remains subordinate to JARVIS-owned permissions,
execution, provenance, persistence, and verification boundaries.
