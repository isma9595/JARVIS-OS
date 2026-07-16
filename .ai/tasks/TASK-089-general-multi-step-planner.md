# TASK-089 — General Multi-Step Planner

## Scope

TASK-089 adds a bounded, deterministic, linear planner behind `JarvisAppService`.

Planning is explicit only:

- Russian: `составь план: ...`, `создай план: ...`, `спланируй: ...`
- English after language switch: `create plan: ...`, `plan: ...`

Ordinary commands such as `статус системы` continue through the normal command path and do not create a plan.

## Separation

Plan creation, inspection, execution, step confirmation, cancellation, and terminal result inspection are separate operations.

- Creating or showing a plan executes no steps.
- Execution requires `выполни план` / `запусти план` or English `execute plan`.
- `да` resumes only an already running plan paused on a confirmation-required step.
- `отмена` / `cancel` cancels the current paused/running plan and executes no remaining steps.

## Planner Boundary

The planner is session-only and AppService-owned. It does not persist plans and does not use persistent memory as plan storage.

The planner supports:

- ordered steps;
- maximum 8 steps;
- deterministic parsing;
- registered capabilities only;
- typed internal step arguments;
- read-only steps;
- bounded local state changes;
- confirmation-required steps;
- cancellation;
- failure stopping;
- progress;
- idempotency through `ExecutionCoordinator`;
- safe snapshots and results.

The planner does not support branches, loops, DAGs, parallel steps, recursion, arbitrary tools, shell commands, dynamic Python, provider-generated executable plans, autonomous background planning, scheduling, persistence, crash recovery, rollback, browser/desktop automation, or provider warm-up.

## Capability Registry

Every capability is deliberately registered in `JarvisAppService._build_planner_registry`.

Initial capabilities:

- `system.status` — read-only, executes the existing system status boundary.
- `startup.profile` — read-only startup profile.
- `language.get` — read-only language preference.
- `language.set` — bounded local language preference change.
- `memory.remember` — bounded local memory write.
- `memory.recall` — read-only memory recall.
- `memory.list` — read-only memory listing.
- `memory.forget` — bounded local memory deletion by key.
- `memory.forget_all` — confirmation-required bounded local memory deletion.

Document review is not exposed in TASK-089 because it already has its own multi-step workflow and confirmation path. Composing it inside the general planner would create nested workflow/confirmation semantics, so it remains unsupported until a later explicit design.

## Parsing

Step separators:

- semicolon;
- `затем`;
- `потом`;
- `после этого`;
- `then`.

The parser rejects empty plans, plans over 8 steps, oversized text, control characters, credential-like values, unknown steps, ambiguous steps, and empty required arguments. Parse failure creates no partial executable plan and performs no capability execution.

## Execution

Execution uses one operation id for the whole plan via `ExecutionCoordinator`.

Steps are executed by a thin planner executor over the existing `WorkflowRunner`. Policy is evaluated immediately before each step through `PolicyDecisionBoundary`. A denied or failed step stops later steps. Confirmation-required steps pause before the side effect and resume only for the same plan operation and step.

Provider output and memory values are never evaluated as plan text or commands. Capability output is safe result text only.

## Language

Russian remains the default. English planner commands and messages are available only after English is selected. Changing language does not rewrite internal capability ids.

## Desktop Shell

Desktop Shell remains AppService-only. Planner results are surfaced through the existing execution result formatting fields: plan id, status, operation id, current step, step count, progress, and confirmation requirement. The GUI does not access the planner registry or executors directly.

## Startup And Safety

Planner objects are lightweight AppService state. Creating, showing, or executing a read-only plan does not initialize providers, credentials, microphone, Vosk, TTS, network, or unrelated platform adapters.

## Manual Smoke

Recommended verification order:

1. `python -m pytest tests/unit/test_multi_step_planner.py -v`
2. `python -m pytest tests/unit/test_plan_executor.py -v`
3. `python -m pytest tests/integration/test_task_089_general_multi_step_planner.py -v`
4. `powershell -ExecutionPolicy Bypass -File scripts/assistant_smoke.ps1`
5. Run compatibility suites for AppService, Desktop Shell, memory-aware conversation, lazy initialization, and workflow runner.
6. Run full pytest and health check.

Known limitation: future provider-assisted planning may summarize or suggest possible steps, but provider output must remain non-executable unless translated through the same deterministic parser and explicit capability registry.
