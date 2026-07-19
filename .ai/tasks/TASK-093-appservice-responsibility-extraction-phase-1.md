# TASK-093 - AppService Responsibility Extraction, Phase 1

Baseline: `c3f1c5daba2e92bc084ec1bb8c46335c26dfcea1`

Status: implemented and verified.

## Purpose

Address AUD-001 partially by extracting planner-specific AppService
orchestration from `JarvisAppService` into one focused internal service while
preserving the public AppService API and TASK-092 planner safety guarantees.

Related documentation update for AUD-003:
`docs/architecture/APPSERVICE_PLANNER_BOUNDARY.md`.

## Scope

Included:

- planner preview delegation;
- planner create/show/execute/cancel delegation;
- planner awaiting-confirmation continuation and cancellation handling;
- repeated Execute protection;
- operation id propagation through existing `PlanExecutor` and planner
  snapshot contracts;
- public command DTO ownership moved to `app.app_contracts` with compatible
  `app` and `app.app_service` import surfaces;
- focused direct planner service import/construction tests;
- focused AppService delegation tests.

Excluded:

- CommandProcessor extraction;
- general command dispatch redesign;
- memory grammar changes;
- AUD-010 remediation;
- AUD-011 remediation;
- provider routing;
- voice/TTS changes;
- Desktop Shell redesign;
- public DTO redesign;
- public DTO field/default/immutability changes;
- dependency container redesign;
- broad module reorganization.

## Final Boundary Corrections

`AppCommandSource`, `AppCommandPreview`, and `AppCommandResult` are now defined
in `app.app_contracts`. `JarvisAppService` and `PlannerCommandService` both
import the DTOs from that neutral contract module. `app.__init__` re-exports the
DTOs to preserve `from app import AppCommandPreview, AppCommandResult,
AppCommandSource`; `app.app_service` also remains compatible because it imports
the same DTOs.

`PlannerCommandService` does not import `app.app_service` anywhere, including
inside methods. It has explicit return annotations for preview, handle, and
result helpers, and its `source` and `idempotency_key` parameters are typed.

Direct service tests construct `PlannerCommandService` with explicit
`MultiStepPlanner`, `PlanExecutor`, policy boundary, execution coordinator, and
focused fake capability dependencies. They cover preview, first execute,
repeated execute, cancel, read-only completion, and import without loading the
facade module.

Memory-control normalization and planner confirmation normalization share
`app.text_normalization.normalize_control_text`. The helper preserves only the
existing exact normalization behavior: trim, lowercase, replace Russian `ё`
with `е`, replace commas/colons/semicolons with spaces, and collapse
whitespace. It performs no encoding repair and no grammar expansion, and does
not change AUD-010 or AUD-011.

Retained callable dependencies are documented as value-only contracts:
`LanguageCodeProvider`, `LocalizedTextFormatter`, and `SafeTextPreviewer`. They
do not pass or expose a `JarvisAppService` instance.

## Changed Files

- `app/app_service.py`
- `app/app_contracts.py`
- `app/text_normalization.py`
- `app/__init__.py`
- `app/services/__init__.py`
- `app/services/planner_command_service.py`
- `tests/unit/test_app_service.py`
- `tests/unit/test_planner_command_service.py`
- `.ai/tasks/TASK-093-appservice-responsibility-extraction-phase-1.md`
- `docs/architecture/APPSERVICE_PLANNER_BOUNDARY.md`

## Safety Checklist

- [x] Preview does not execute plans.
- [x] Preview does not create `operation_id`.
- [x] Preview does not arm awaiting confirmation.
- [x] Repeated Execute is not confirmation.
- [x] Cancel preserves the operation id through existing planner snapshots.
- [x] No positive forget-all confirmation was used in tests.
- [x] No dependency or configuration change.
- [ ] Commit unchecked.
- [ ] Push unchecked.

## Manual Smoke Plan

Completed against an isolated Desktop Shell state:

1. Non-planner command `статус системы` executed successfully.
2. Command id was `system.status`.
3. Category was `system`.
4. Risk was `read_only`.
5. Executed through AppService: yes.
6. Ordinary command was not routed through planner handling.
7. Safe plan `create plan: system status` was proposed.
8. Preview of `execute plan` showed `read_only`, no confirmation, operation id
   none, and active capability `system.status`.
9. Execute completed the plan with progress 100.
10. `show plan` preserved completed state and did not execute the step again.
11. No real memory, profile, hardware, network provider, secret, or destructive
    confirmation was used.

Historical isolated Desktop Shell plan:

1. Preview a read-only planner command.
2. Preview a local-write planner command.
3. Preview an English forget-all plan.
4. Execute the forget-all plan once.
5. Repeat execute plan and verify `explicit_confirmation_required`.
6. Cancel the plan.
7. Confirm a temporary isolated marker survived.
8. Remove the marker.

Do not send `yes` or `да`.
