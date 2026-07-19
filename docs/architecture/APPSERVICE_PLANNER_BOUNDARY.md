# AppService Planner Boundary

Baseline: `c3f1c5daba2e92bc084ec1bb8c46335c26dfcea1`

TASK-093 Phase 1 partially addresses AUD-001 by extracting planner-specific
application orchestration from `JarvisAppService`. It also updates the
AppService architecture record for AUD-003.

## Phase 1 Scope

`JarvisAppService` remains the public facade for Desktop Shell, tests, and
external callers. It still owns top-level readiness checks, command
normalization, top-level dispatch ordering, public DTO boundaries, non-planner
commands, generic response safety rules, and the planner capability registry
bindings that call broader app features.

`PlannerCommandService` owns the planner slice after top-level dispatch reaches
planner handling:

- create/propose plan;
- show plan;
- preview execute plan projection;
- execute plan;
- cancel plan;
- planner awaiting-confirmation continuation;
- repeated Execute protection;
- planner result text and planner `AppCommandResult` population.

Phase 1 does not extract `CommandProcessor`, change command grammar, change
capability descriptors, change risk policy, change public DTO fields, or alter
Desktop Shell text.

## Dependency Direction

`JarvisAppService` constructs planner infrastructure:

- `PlannerCapabilityRegistry`
- `MultiStepPlanner`
- `PlanExecutor`
- `PlannerCommandService`

`PlannerCommandService` receives explicit dependencies only:

- `MultiStepPlanner`;
- `PlanExecutor`;
- language-code accessor (`Callable[[], str]`);
- localized text formatter (`Callable[[str, str], str]`);
- safe preview text formatter (`Callable[[str], str]`).

The planner service does not receive the `JarvisAppService` instance, does not
import AppService private state, and does not own the capability registry. It
returns the existing public `AppCommandPreview` and `AppCommandResult` DTOs.

The DTO dependency direction is one-way through `app.app_contracts`:

- `AppCommandSource`, `AppCommandPreview`, and `AppCommandResult` are defined
  in the neutral contract module;
- `JarvisAppService` imports those DTOs from `app.app_contracts`;
- `PlannerCommandService` imports those DTOs from `app.app_contracts`;
- `app.__init__` re-exports the DTOs so `from app import AppCommandPreview`,
  `AppCommandResult`, and `AppCommandSource` remain supported;
- `app.app_service` remains a compatibility import surface because it imports
  those DTOs, but the planner service never imports `app.app_service`.

There is no import from `app.services.planner_command_service` back to
`app.app_service`, including lazy imports inside methods.

## Public Facade Guarantees

The public AppService boundary remains stable:

- `preview_command()` returns `AppCommandPreview`;
- `preview_text_ru()` keeps the same planner-visible fields;
- `execute_command()` returns `AppCommandResult`;
- Desktop Shell still uses AppService only;
- command ids, categories, risk metadata, operation lifecycle fields, and
  confirmation fields are preserved.

## Preview Flow

1. `JarvisAppService.preview_command()` normalizes text and handles document
   preview first.
2. It delegates planner preview to `PlannerCommandService.preview_command()`.
3. The planner service detects planner command kind through `MultiStepPlanner`.
4. Create preview parses a temporary snapshot only.
5. Execute preview reads the current public planner snapshot and projects the
   next effective step.
6. Preview returns `operation_id=None`, does not call `PlanExecutor`, does not
   mutate memory, and does not arm awaiting confirmation.

## Execute Flow

1. `JarvisAppService.execute_command()` still handles startup, language, and
   pending memory-forget-all control before planner dispatch.
2. It delegates planner commands to
   `PlannerCommandService.handle_command()`.
3. Create/show/cancel/execute routes update only the planner state expected by
   existing planner contracts.
4. Non-planner commands fall back to existing AppService handling.

## Confirmation And Cancellation

Planner awaiting-confirmation ownership moved to `PlannerCommandService` for
planner snapshots only. Explicit positive confirmation can resume a paused
planner operation through `PlanExecutor.resume()`. Repeating Execute is rejected
with `explicit_confirmation_required` and does not resume or execute a
capability. Cancellation uses `PlanExecutor.cancel()` and preserves the current
planner operation id through the existing snapshot contract.

Generic non-planner confirmation and pending memory-forget-all control remain
in `JarvisAppService`.

Confirmation and memory-control text normalization share
`app.text_normalization.normalize_control_text`. The helper preserves the
existing exact behavior: trim, lowercase, replace Russian `ё` with `е`, replace
commas/colons/semicolons with spaces, and collapse whitespace. It performs no
encoding repair, no grammar expansion, and no alias or transliteration changes.
AUD-010 and AUD-011 behavior is intentionally unchanged.

The retained callable dependencies are deliberately narrow:

- `LanguageCodeProvider` returns only the current language code string;
- `LocalizedTextFormatter` receives already-authored RU/EN safe messages and
  returns one string;
- `SafeTextPreviewer` receives one string and returns a redacted bounded
  preview.

These callables expose values only and do not give the planner service a
reference to `JarvisAppService` or AppService private state.

## Operation Id Ownership

Preview owns no operation id. Execute operation ids are still created by
`PlanExecutor` through the existing `ExecutionCoordinator` integration. The
planner service propagates the operation id from execution snapshots into
`AppCommandResult`; it does not create independent operation ids.

## Testing Strategy

Focused tests cover:

- direct `PlannerCommandService` import and construction without obtaining the
  service from `JarvisAppService`;
- direct `PlannerCommandService` preview and execute behavior with explicit
  planner, executor, policy, and fake capability dependencies;
- read-only, local-write, and confirmation-required preview projections;
- first Execute awaiting confirmation;
- repeated Execute protection;
- cancel behavior;
- read-only plan execution;
- AppService delegation for preview, execute, show, and cancel;
- non-planner AppService compatibility.
- shared normalization compatibility between AppService memory control and
  planner confirmation control.

Existing TASK-091 and TASK-092 characterization tests remain in place. AUD-010
and AUD-011 behavior is intentionally unchanged.

## Rollback Notes

Rollback is limited to reverting:

- `app/app_contracts.py`;
- `app/text_normalization.py`;
- `app/services/planner_command_service.py`;
- `app/services/__init__.py`;
- the planner delegation edits in `app/app_service.py`;
- `app/__init__.py`;
- TASK-093 tests and docs.

No configuration, dependency, grammar, or public DTO field migration is
involved.

## Manual Smoke Checklist

Run later against isolated Desktop Shell state:

1. Preview a read-only planner command.
2. Preview a local-write planner command.
3. Preview an English forget-all plan.
4. Execute the forget-all plan once.
5. Repeat execute plan and verify `explicit_confirmation_required`.
6. Cancel the plan.
7. Confirm a temporary isolated marker survived.
8. Remove the marker.

Do not send `yes` or `да`.

- Commit: unchecked.
- Push: unchecked.
