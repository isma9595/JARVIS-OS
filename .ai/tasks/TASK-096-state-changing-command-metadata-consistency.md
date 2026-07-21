# TASK-096 - State-Changing Command Metadata Consistency

Baseline: `69969026f051142b0dcf92a58f8da0a6932764d8` (`Expand command resolution service`).

## Scope

TASK-096 addresses AUD-010 only: state-changing command metadata consistency across recognition, preview, execution, AppService projection, execution journal, and Desktop Shell projection.

Excluded and unchanged:

- AUD-008: memory preview/execute recognition inconsistency.
- AUD-009: Russian memory-key inflection.
- AUD-011: Russian forget-all planner misclassification.
- Command grammar, aliases, ids, categories, public DTO schemas, configuration, dependencies, provider behavior, hardware behavior, and credential storage.

## AUD-010 Evidence

The TASK-090 audit found that `profile.language.set` and some `memory.remember` / `memory.forget` routes changed persistent or session state while exposing read-only risk and/or `operation_id` as none. TASK-091 characterization narrowed this:

- AppService memory remember/forget executed with `local_write` and `succeeded`, but bypassed the execution coordinator and journal, leaving `operation_id` none.
- AppService language set changed isolated profile state while reporting `risk_level=read_only`, `executed=False`, and no operation status.
- Desktop Shell execution output rendered command id/category/risk/operation fields but omitted the requires-confirmation value.
- Planner capability descriptors for `language.set`, `memory.remember`, and `memory.forget` said `local_write`, but their policy factories created read-only policy requests.

## Source Of Truth

The existing source order is preserved:

1. CommandRegistry or planner capability descriptor for stable command metadata.
2. CommandResolutionService for resolver-owned command id/category/safe_args.
3. Unified Policy Decision Boundary for confirmation and denial.
4. ExecutionCoordinator and ExecutionJournal for operation lifecycle.
5. AppService as projection and coordination layer.
6. Desktop Shell as rendering layer.

No new registry, DTO field, or result hierarchy was added.

## Route Matrix

| Route family | Existing route | Public id | Category | Risk after TASK-096 | Confirmation | Operation behavior |
|---|---|---|---|---|---|---|
| Memory write | remember/add supported by AppService memory parser | `memory.remember` | `memory` | `local_write` | no | state change gets `op-*`, journal `succeeded` |
| Memory delete one | forget one supported by AppService memory parser | `memory.forget` | `memory` | `local_write` | no | state change gets `op-*`, journal `succeeded` |
| Memory forget-all | existing preview/confirmation paths only | `memory.forget_all` / pending memory operation id | `memory` | `confirmation_required` | yes | not executed by this task |
| Language set | existing language set phrases | `profile.language.set` | `profile` | `local_write` on changed execution | no | changed state gets `op-*`, journal `succeeded` |
| Language reset | existing reset phrase | `profile.language.reset` | `profile` | `local_write` when changed | no | changed state gets `op-*`, journal `succeeded` |
| Microphone modes | off/partial/continuous | existing resolver ids | `voice` | existing resolver metadata | no | no capture in tests |
| Voice output | enable/disable/safety settings | existing resolver ids | `voice` | existing resolver metadata | no | no TTS playback in tests |
| Assistant name/profile | set/reset/read | internal resolver ids preserved; public profile mapping preserved where already characterized | profile/assistant as existing | existing confirmation metadata | yes for set/reset | real profile not mutated by automated tests |
| Provider/session | select/reset/session routes | existing registry ids | `ai` / provider categories | existing confirmation/network metadata | existing policy | no provider call in tests |
| Secure keys | import/delete/status | existing registry ids | `secure_keys` | `sensitive` for mutations | yes | fake/preview only; no real credential values |
| Planner/workflow | execute/cancel workflow states | planner capability ids | `planner` / capability category | descriptor risk | descriptor confirmation | existing journal contract preserved |

## Corrections Applied

- Coordinated direct AppService state-changing language and memory results through the existing `ExecutionCoordinator`.
- Refined direct language and memory coordination to register and resolve duplicate/conflict decisions before any domain mutation:
  register / duplicate-conflict decision -> execute domain mutation once -> finalize operation.
- Preserved result command id/category/risk and copied safe metadata into the journal.
- Marked coordinated direct operations as `succeeded`, `awaiting_confirmation`, `denied`, or `failed` through the existing journal lifecycle.
- Changed language set/reset execution projection from read-only/no-execution to `local_write`/executed when state actually changes.
- Changed planner policy factories for `language.set`, `memory.remember`, and `memory.forget` from read-only requests to `local_write` with `file_write` capability, matching their existing descriptors.
- Added Desktop Shell execution rendering for `requires confirmation`.
- Corrected the hidden baseline AUD-010 confirmation projection for completed safe legacy routes: `статус микрофона` and `task096 неизвестная безопасная команда` already returned AppService `requires_confirmation=True` at baseline while completing as `succeeded` without awaiting confirmation; Desktop only made that stale value visible. Completed routes whose policy allowed execution without confirmation now project `requires_confirmation=False`.
- The stale source was unknown-preview confirmation metadata reused during completed legacy/CommandProcessor result projection. The correction is narrow: AppService clears `requires_confirmation` only when structured processor output proves the completed safe route (`requires_confirmation=False` from the processor result, or `intent == "microphone.mode.status"`).
- Redacted direct memory journal previews as `memory.remember [REDACTED]` / `memory.forget [REDACTED]`, with no raw memory key or value in operation metadata.
- Stored meaningful journal metadata strings for direct boolean fields (`requires_confirmation=no`, `network_may_be_used=no`).

## Intentional Behavior Preserved

- Memory preview remains unknown/non-mutating for routes covered by AUD-008.
- Russian memory-key inflection remains unchanged for AUD-009.
- Russian forget-all planner misclassification remains unchanged for AUD-011.
- Internal resolver ids and public AppService/Desktop ids remain distinct where TASK-095 characterized that as stable behavior.
- Direct no-op route behavior is characterized: setting the active language, forgetting a missing memory key, and remembering an identical existing value still register first and participate in duplicate/conflict handling; the projected result can remain `read_only` / `executed=False` when the handler reports no state change.
- Memory forget-all remains on its existing confirmation/pending-operation flow and is not re-registered by the direct remember/forget/language coordination path.
- Actual awaiting-confirmation routes continue to project `requires_confirmation=True`.
- No command-id/category/risk cleanup was performed for the manual-smoke routes; both keep command id none, category unknown, and risk unknown in Desktop execution output.
- No command aliases, ids, grammar, DTO fields, config, dependencies, provider calls, microphone capture, Vosk loading, TTS playback, real credential access, or real profile mutation were introduced.

## Tests

Focused coverage added or updated:

- Resolver state-changing metadata matrix.
- AppService language set metadata and journal operation.
- AppService memory remember/forget metadata and journal operations.
- AppService direct duplicate suppression and idempotency conflicts for memory and language.
- AppService direct registration-before-mutation and failed-execution finalization.
- AppService direct no-op duplicate behavior.
- AppService direct memory journal redaction.
- AppService and Desktop cross-layer coverage for `статус микрофона` and `task096 неизвестная безопасная команда`, proving succeeded operation status, no awaiting-confirmation result, `requires_confirmation=False`, unchanged none/unknown metadata, and no memory mutation.
- Desktop positive awaiting-confirmation rendering with a fake safe result, proving `requires confirmation: yes` still renders without executing a destructive action.
- Planner local-write policy factory metadata.
- Desktop Shell execution requires-confirmation and operation projection.
- Existing TASK-091 characterization updated from mismatch capture to TASK-096 corrected contract.

## Safe Manual Smoke Checklist

Manual smoke found the expected direct memory behavior and two confirmation metadata discrepancies:

- `memory.remember`: `local_write`, no confirmation, succeeded operation id present.
- `memory.forget`: `local_write`, no confirmation, succeeded operation id present.
- `статус микрофона`: baseline AppService execution already exposed `requires_confirmation=True` despite a succeeded, non-confirmation route; classified as pre-existing hidden AUD-010 inconsistency.
- `task096 неизвестная безопасная команда`: baseline AppService execution already exposed `requires_confirmation=True` despite a succeeded, non-confirmation fallback; classified as pre-existing hidden AUD-010 inconsistency.

Remaining manual smoke must use temporary reversible data:

- `remember task096marker = west`
- `what do you remember about task096marker`
- `forget task096marker`
- microphone mode status only; do not start capture
- voice-output status only; do not play TTS
- current assistant-name read only; do not change real profile without later approval
- AI/provider status only; do not invoke provider
- secure-key status only; do not reveal or mutate keys
- unknown harmless route

Compare command id, category, risk, confirmation, operation status, and AppService/Desktop projection where available.

## Completion

- Final verification:
  - Targeted AppService/Desktop/local TTS: 94 passed.
  - Broader TASK-096/policy/planner/coordinator batch: 209 passed.
  - TASK-094/TASK-095 invariant tests: 6 passed.
  - Full pytest: 1649 passed, 2 skipped.
  - Strict pytest: 1649 passed, 2 skipped.
  - Health check: SUCCESS, 1649 passed, 2 skipped.
  - Assistant smoke: JARVIS ASSISTANT SMOKE: SUCCESS, with one pytest cache warning.
  - Import probes:
    - COMMAND RESOLUTION SERVICE IMPORT: SUCCESS.
    - COMMAND PROCESSOR LOADED: False.
    - APP SERVICE IMPORT: SUCCESS.
    - DESKTOP SHELL IMPORT: SUCCESS.
  - Changed Python files compiled successfully with `PYTHONDONTWRITEBYTECODE=1`.
  - `git diff --check`: passed.
- TASK-095 invariants remain: extracted matcher count in `process()` is `0`; remaining matcher count is `50`; exact/mapping/prefix overlap is `0/0/0`.
- Commit: unchecked.
- Push: unchecked.
