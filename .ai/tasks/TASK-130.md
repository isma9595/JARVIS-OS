# TASK-130 — Golden Agent Evals v1

## Status

Audit remediation is completed in the unstaged worktree on the published
TASK-129 baseline. Staging, commit, and push are outside this implementation
phase.

## Objective

Create the first deterministic goal-level evaluation suite for JARVIS. The
suite measures current user-goal outcomes and safety boundaries instead of
mistaking unit-test count or new abstractions for agent progress.

TASK-130 does not implement Agent Runtime, Tool Registry, Planner v2, new tools,
or new user-facing behavior. It establishes a repeatable offline baseline that
future TASK-131+ work must improve.

## Verified Baseline

- Published dependency: TASK-129 — Agentic Project Rebaseline & Legacy Freeze.
- Baseline commit: `8d6b4087944b6698d82467589cd35e73f09cf4b1`.
- Baseline tree: `a0b98bcaf4a9d0f1f96eecae42e6b29ac419347b`.
- Branch and remote-tracking branch: `main` and `origin/main`, equal at
  preflight.
- Baseline worktree and staging: clean.
- TASK-129 full acceptance: `2707 passed, 4 skipped in 22.04s`.
- No TASK-130 record or repository eval framework existed at preflight.

## Architecture Boundary

The eval layer is an observer and test driver only. It uses public AppService
contracts and deterministic injected fakes. It owns no application, cognition,
session, policy, execution, workflow, provider, persistence, memory, Desktop,
or tool state.

Existing owners remain unchanged:

- `JarvisAppService` is the application facade;
- `ConversationSessionService` owns conversation sessions;
- `PolicyDecisionBoundary` owns policy decisions;
- `ExecutionCoordinator` and `ExecutionJournal` own operation lifecycle;
- `WorkflowRunner` owns workflow lifecycle;
- provider privacy/credential/network gates remain authoritative;
- provider output remains presentation-only and is never executed as a command.

## Golden Task Catalog

The version-1 catalog contains exactly 30 stable ordered scenarios covering:

- ordinary conversation and provider/fallback behavior;
- provider output isolation and error redaction;
- privacy refusal and secret handling;
- known command execution and side-effect-free preview;
- clarification, confirmation, cancellation, and idempotent control behavior;
- session state and bounded context;
- unsupported future email, research, scheduling, filesystem, spreadsheet,
  document, memory, voice, multi-step, model-routing, and restart goals.

Each case has a stable opaque id, category, bounded goal description, critical
safety flag, deterministic driver, expected current outcome, and explicit
step/model/tool/side-effect budgets.

## Metrics

The report exposes bounded aggregate metrics for:

- contract pass rate;
- task success rate;
- correct tool selection rate;
- unsafe action rate;
- unnecessary confirmation rate;
- human intervention rate;
- recovery rate;
- duplicate side-effect rate;
- average steps;
- model and tool call counts;
- token/cost budget;
- context precision;
- verifier accuracy.

Unavailable runtime signals remain `None` with zero coverage; they are never
invented as successful zero-cost or perfect-quality measurements.

## Safety And Privacy

- The suite is offline and deterministic.
- No real provider, network, microphone, TTS, user document, AppData, or
  execution side effect is used.
- Synthetic secret/error fixtures are generated in memory and never included in
  catalog, observation repr, result repr, or reports.
- Each catalog case is invoked exactly once per run.
- Critical safety failure is visible in the report and fails acceptance.
- Callback failures use bounded error codes without raw exception text,
  traceback, path, prompt, response, or secret disclosure.

## Approved File Scope

1. `.ai/tasks/TASK-130.md`
2. `evals/golden_agent.py`
3. `evals/golden_agent_tasks_v1.json`
4. `tests/evals/test_golden_agent_eval_contracts.py`
5. `tests/evals/test_golden_agent_baseline.py`
6. `.ai/CHECKPOINT.md`
7. `README.md`
8. `docs/ARCHITECTURE.md`
9. `docs/ROADMAP.md`
10. `docs/AGENTIC_ROADMAP_V1.md`

No production runtime, dependency, CI, or pytest configuration file is in
scope.

## Out Of Scope

- Agent Runtime, AgentRun persistence, Tool Registry, scoped permission model,
  Planner v2, verifier, replanner, context manager, or artifacts;
- new AppService methods or changes to command/provider/workflow routing;
- live model/network/browser/provider evaluation;
- real microphone, TTS, user filesystem, or persistence access;
- automatic scoring by an LLM;
- dependencies, CI changes, staging, commit, or push;
- TASK-131 implementation.

## Acceptance Criteria

- exactly 30 unique ordered versioned cases load deterministically;
- malformed, duplicate, unsupported, or unbounded catalog data fails closed;
- the runner invokes every case once and produces deterministic bounded results;
- all requested metrics are present and unavailable metrics remain explicit;
- critical safety cases pass on the published current behavior;
- current unsupported agent goals record honest task failure without hidden
  execution or network use;
- no raw goal, provider result, exception, traceback, path, or secret appears in
  diagnostic repr/report data;
- focused and related regression checks pass;
- compileall passes for the eval module;
- one full repository pytest passes;
- `git diff --check` passes and staging remains empty.

## Validation

- Focused RED: two expected collection errors because `evals.golden_agent` did
  not yet exist, `2 errors in 0.66s`.
- First GREEN candidate: `5 failed, 18 passed in 2.80s`; failures were limited
  to eval-layer assumptions about provider-call labels, legacy passthroughs,
  unknown preview confirmation, and the bounded-context oracle.
- Second GREEN candidate: `2 failed, 21 passed in 3.32s`; only the factual
  greeting/context provider-call count remained to align.
- Initial focused GREEN: `23 passed in 2.47s`.
- After strict count/order validation was added, focused GREEN reached
  `26 passed in 2.55s`; the related matrix passed with
  `272 passed in 4.92s`.
- Final parser/observation type hardening GREEN: `31 passed in 2.57s`.
- Final related regression: `277 passed in 4.29s`.
- Compileall: exit code `0` for `evals/golden_agent.py`.
- Final offline safe-report smoke: 30 cases, no critical failures, 11/30 goal
  success, 2/2 expected tool selections, zero unsafe actions, zero duplicate
  side effects, 11/30 unnecessary confirmations, 13/30 human intervention,
  2/2 recovery, average `34/30` steps, four fake model calls, one registered
  tool call, and zero real network/microphone/TTS/filesystem calls.
- Pre-audit full repository acceptance: `2738 passed, 4 skipped in 28.22s`.
- Final read-only audit found that future-goal success was derived from fixture
  expectations, duplicate command calls were collapsed to a boolean, external
  counters were not active guards, callback failures were excluded from the
  task-success denominator, and catalog I/O retained its original cause.
- Audit-remediation RED: `5 failed, 31 passed in 2.70s`, limited to those five
  regression contracts.
- Remediation candidates exposed only factual verifier alignment and safe
  LazyComponent error wrapping: `3 failed, 33 passed in 2.95s`, then
  `2 failed, 34 passed in 3.29s`, then `1 failed, 36 passed in 2.53s`.
- Post-remediation focused GREEN: `37 passed in 2.42s`.
- Post-remediation related regression: `283 passed in 4.05s`.
- Post-remediation compileall: exit code `0`.
- Post-remediation offline smoke: 30/30 observations, 11/30 actual task
  successes, 2/2 expected tool selections, zero unsafe actions and duplicate
  effects, four fake model calls, one registered tool call, zero real external
  calls, and unavailable token/cost/context/verifier metrics retained as
  unavailable.
- Single post-remediation full repository acceptance:
  `2744 passed, 4 skipped in 22.05s`.

## Next Stage

TASK-131 — Unified Tool Contract & Tool Registry v1.
