# Planner Snapshot Contract

Baseline: `fe9c87a391a031b1f6697b0a750ad37e52bae0cc`

The planner snapshot boundary is the public, immutable inspection surface for
bounded multi-step plans. It is safe for AppService, Desktop Shell, tests, and
future UI surfaces to read. It must not expose executors, callbacks, provider
objects, credential values, or private runtime containers.

TASK-092 addresses AUD-002 and AUD-012. AUD-011 remains the current Russian
natural forget-all limitation, and AUD-010 grammar behavior is excluded from
this contract update.

## Public DTOs

`PlanSnapshot` describes one active plan:

- `plan_id`, `operation_id`
- `goal_summary`, `language_code`
- `status`
- `current_step_id`, `current_step_index`
- `total_steps`, `completed_steps`, `progress_percent`
- `awaiting_confirmation`, `cancellable`
- immutable tuple `steps`
- `safe_message`

`PlanStepSnapshot` describes one public step:

- `step_id`, `position`
- `capability_id`, localized safe `display_name`
- `status`, `safe_message`
- `safe_argument_summary`
- `risk_level`
- `side_effect`
- `requires_confirmation`
- `is_current`
- optional safe `error_code`

`AppCommandPreview` may also expose read-only planner preview fields:

- `active_plan_id`
- `active_plan_status`
- `active_step_id`
- `active_step_capability_id`
- `active_step_name`
- `operation_id`

These AppService fields default to `None` for unrelated previews.

All DTOs are frozen dataclasses. Their `to_dict()` methods emit sanitized
values and defensive copies so caller-side dictionary edits do not mutate
snapshots or planner internal state.

## `is_current`

`PlanStepSnapshot.is_current` is true only when the step id equals the runtime
`current_step_id`. It is false for every other step. Proposed plans may have no
current step yet. Terminal snapshots have no current step unless a runtime
boundary explicitly reports one.

Both public snapshot construction paths set this marker:

- `MultiStepPlanner` private state snapshot construction.
- `PlanExecutor` public snapshot construction from workflow state.

## Default Step Messages

Default public step messages are derived from the current public
`PlanStepStatus` and language code through the shared planner contract helper.
Specific runtime execution messages still take precedence. Steps whose public
status is awaiting confirmation, cancelled, blocked, or skipped must not retain
the pending default message.

## Next Effective Step

Planner Execute Preview selects the next effective public step without
executing anything:

- terminal plans project no step;
- if `current_step_id` is present, select that matching step;
- otherwise select the first step not marked `succeeded`, `cancelled`, or
  `skipped`;
- return the selected step even when it does not require confirmation.

This avoids private state access and avoids any second hard-coded capability
policy map.

## Projection Rules

For `execute plan` Preview:

- `risk_level` is copied from the selected step;
- `requires_confirmation` is copied from the selected step;
- `read_only` is true only when the selected step side effect is `read_only`;
- active plan and active step fields are populated from the public snapshot;
- `operation_id` is `None` before execution.

Expected projections:

- read-only step: `risk_level=read_only`, `read_only=True`,
  `requires_confirmation=False`;
- local-write step without confirmation: `risk_level=local_write`,
  `read_only=False`, `requires_confirmation=False`;
- destructive forget-all step: `risk_level=confirmation_required`,
  `read_only=False`, `requires_confirmation=True`.

## Safe Argument Summary

Step argument summaries are safe display text:

- credential-like values are redacted as `[REDACTED]`;
- parser rejects control characters before plan creation;
- newlines are flattened;
- public summaries are truncated to DTO length limits.

Credential-like redaction covers `sk-*`, API keys, access tokens, generic
tokens, passwords, and private-key blocks.

## Operation Lifecycle

- Preview has `operation_id=None` and performs no operation registration.
- Execute registers one planner operation through `ExecutionCoordinator`.
- Awaiting confirmation keeps the same operation id.
- Only explicit confirmation responses may resume a paused plan.
- Repeating `execute plan`, `run plan`, `выполни план`, or `запусти план` is
  not confirmation.
- Repeated Execute while awaiting confirmation is safely rejected with
  `explicit_confirmation_required`; it does not register, resume, execute a
  capability, or mutate memory.
- Cancel keeps the same operation id and makes the plan terminal.
- Repeated Execute on a terminal plan does not resume or mutate state.

## Safety Boundaries

- Plan creation parses and stores bounded step definitions only.
- Preview does not create, replace, execute, cancel, persist, call providers,
  call ActionRouter, register operations, resume workflows, or mutate memory.
- Destructive or confirmation-required steps pause at execution until explicit
  confirmation through the existing execution flow.
- Repeating Execute while paused is not treated as confirmation.
- Cancellation preserves memory and prevents terminal re-execution.
- Tests must not send positive forget-all confirmation (`yes` or `да`).

## Desktop Shell Visibility

Desktop Shell planner Execute Preview must visibly show:

- active plan id;
- active plan status;
- active step id;
- active step capability;
- active step safe display name;
- operation id `none` before execution;
- projected risk;
- requires confirmation;
- executed through AppService.

Manual smoke:

- `create plan: system status`, then Preview `execute plan`.
- `create plan: remember test word north`, then Preview `execute plan`.
- `create plan: forget everything you remember about me`, then Preview
  `execute plan`.
- Execute the destructive plan only to awaiting confirmation and cancel it.
  Do not send `yes` or `да`.

Commit: unchecked. Push: unchecked.
