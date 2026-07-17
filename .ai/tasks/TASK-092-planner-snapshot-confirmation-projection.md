# TASK-092 - Planner Snapshot Boundary & Confirmation Policy Projection

## Baseline

- Committed baseline: `fe9c87a391a031b1f6697b0a750ad37e52bae0cc`
- Branch: `main`
- Commit: unchecked
- Push: unchecked

## Scope

TASK-092 addresses:

- AUD-002: public immutable planner snapshot DTOs expose safe plan and step
  metadata without private `_PlanState` imports.
- AUD-012: AppService Preview for `execute plan` projects the next effective
  step risk, read-only status, and confirmation requirement before execution.

TASK-092 excludes:

- AUD-011: the current Russian natural forget-all phrase remains characterized
  as `memory.forget`, not `memory.forget_all`.
- AUD-010: command grammar and broader planner capability interpretation are
  unchanged.

This task does not change capability descriptors, policy factories, command
grammar, or add a second hard-coded capability policy map.

## Public DTO Fields

`PlanSnapshot` is the public immutable plan inspection DTO. It includes:

- `plan_id`, `operation_id`
- `goal_summary`, `language_code`
- `status`, `current_step_id`, `current_step_index`
- `total_steps`, `completed_steps`, `progress_percent`
- `awaiting_confirmation`, `cancellable`
- tuple `steps`
- `safe_message`

`PlanStepSnapshot` is the public immutable step inspection DTO. It includes:

- `step_id`, `position`, `capability_id`
- localized safe `display_name`
- `status`, `safe_message`, `safe_argument_summary`
- `risk_level`, `side_effect`, `requires_confirmation`
- `is_current`
- optional safe `error_code`

`AppCommandPreview` includes optional planner preview fields:

- `active_plan_id`
- `active_plan_status`
- `active_step_id`
- `active_step_capability_id`
- `active_step_name`
- `operation_id`

All optional planner preview fields default to `None` so existing constructors
remain compatible.

## `is_current` Semantics

`PlanStepSnapshot.is_current` is deterministic and read-only:

- `True` only when the step id equals runtime `current_step_id`.
- `False` for every other step.
- Proposed plans normally have no current step yet.
- Terminal snapshots clear the marker when no current step remains.

Both snapshot construction paths set the marker:

- `MultiStepPlanner` private state to public snapshot.
- `PlanExecutor` public snapshot construction from workflow state.

## Default Step Messages

Default public step messages are derived from the current public
`PlanStepStatus` and language code through the shared planner contract helper.
Specific execution messages recorded in runtime step state still take
precedence. This prevents an awaiting-confirmation, cancelled, blocked, or
skipped step from retaining the old pending message.

## Next Effective Step Selection

Previewing `execute plan` selects the next effective public step from the
active `PlanSnapshot`:

- terminal plans have no projected step;
- if `current_step_id` is present, the matching step is selected;
- otherwise the first step whose status is not `succeeded`, `cancelled`, or
  `skipped` is selected;
- the selected step is returned regardless of whether confirmation is required.

Preview does not create, replace, execute, cancel, persist, register an
operation, resume a workflow, call a provider, call ActionRouter, or mutate
memory.

## Projection Rules

For planner Execute Preview:

- `risk_level` comes from `PlanStepSnapshot.risk_level`;
- `requires_confirmation` comes from
  `PlanStepSnapshot.requires_confirmation`;
- `read_only` is `True` only when `PlanStepSnapshot.side_effect` is
  `read_only`;
- active plan and active step fields are populated from the public snapshot;
- `operation_id` remains `None` before execution.

Expected results:

- read-only next step: `risk_level=read_only`, `read_only=True`,
  `requires_confirmation=False`;
- local-write next step without confirmation: `risk_level=local_write`,
  `read_only=False`, `requires_confirmation=False`;
- forget-all next step: `risk_level=confirmation_required`,
  `read_only=False`, `requires_confirmation=True`.

## Safe Text Rules

`safe_argument_summary` is sanitized through planner contract helpers:

- credential-like values are redacted as `[REDACTED]`;
- control characters are rejected during plan parsing;
- line breaks are flattened;
- summaries are truncated to the configured public DTO length.

The same credential-redaction boundary covers `sk-*`, API keys, access tokens,
generic tokens, passwords, and private-key blocks.

## Operation Lifecycle

- Preview: `operation_id=None`; no execution operation is registered.
- Execute: a planner operation id is created by `ExecutionCoordinator`.
- Awaiting confirmation: the same operation id is retained while the current
  confirmation-required step is paused.
- Only explicit confirmation responses may resume a paused plan.
- Repeating `execute plan`, `run plan`, `выполни план`, or `запусти план` is
  not confirmation.
- Repeated Execute while awaiting confirmation is safely rejected with
  `explicit_confirmation_required`; it does not register, resume, execute a
  capability, or mutate memory.
- Cancel: the same operation id is retained and the plan becomes terminal.
- Repeated Execute on a terminal plan does not resume or mutate state.

## Cancellation Guarantees

- Cancelled plans remain terminal.
- Repeated `execute plan` after cancellation returns the terminal-plan result.
- Memory remains unchanged after Preview, awaiting confirmation, cancellation,
  and terminal re-execute.
- Tests never send positive forget-all confirmation (`yes` or `да`).

## Manual Desktop Shell Smoke Checklist

- Create a read-only plan: `create plan: system status`.
- Preview: `execute plan`.
- Confirm Desktop Shell shows active plan id/status, active step id,
  capability, safe display name, operation id `none`, projected risk,
  confirmation requirement, and `executed through AppService: yes`.
- Create a local-write plan: `create plan: remember test word north`.
- Preview: `execute plan`; confirm `risk: local_write`, confirmation `no`,
  and memory is unchanged.
- Create a destructive plan:
  `create plan: forget everything you remember about me`.
- Preview: `execute plan`; confirm `risk: confirmation_required`,
  confirmation `yes`, operation id `none`, and memory is unchanged.
- Execute the destructive plan only to the awaiting-confirmation pause, then
  cancel. Do not send `yes` or `да`.

## Completed Manual Desktop Shell Smoke

- Temporary marker `task092smokemarker = north` was created and recalled.
- The English forget-all plan produced `memory.forget_all`.
- Preview exposed `confirmation_required` and `requires_confirmation=true`.
- First execution paused at `awaiting_confirmation` with progress `0`.
- Repeated execute plan returned `explicit_confirmation_required`.
- Repeated Execute preserved the same `operation_id`.
- Repeated Execute did not execute `memory.forget_all`.
- Cancel plan produced `cancelled` status.
- The temporary marker survived cancellation.
- The temporary marker was removed afterward.
- No `yes` or `да` confirmation was sent.

## Verification

Run:

```powershell
python -m pytest -q tests/characterization/test_planner_contracts.py tests/unit/test_multi_step_planner.py tests/unit/test_plan_executor.py tests/unit/test_app_service.py tests/unit/test_desktop_shell.py tests/integration/test_task_089_general_multi_step_planner.py
python -m pytest -q
python -W error::DeprecationWarning -m pytest -q
powershell -ExecutionPolicy Bypass -File scripts/health_check.ps1
powershell -ExecutionPolicy Bypass -File scripts/assistant_smoke.ps1
git diff --check
git status --short --untracked-files=all
git diff --stat
git diff --name-only
```
