# TASK-091 - Contract & Metadata Characterization Tests

## Objective

Add passing characterization tests that record the current observable contracts for audit findings AUD-008 through AUD-013 before production remediation begins.

These tests intentionally document current behavior. Later remediation tasks must update both production behavior and these characterization expectations deliberately.

## Baseline Commit

- `ec1c4ee496faa4487bd9a57383ddfe03a6ed6565`
- `ec1c4ee Add full system audit and remediation roadmap`

## Findings Covered

- AUD-008 - Preview/Execute recognition inconsistency for memory commands
- AUD-009 - Russian memory-key inflection is not normalized
- AUD-010 - State-changing operation metadata is inconsistent
- AUD-011 - Natural Russian forget-all phrase is misclassified
- AUD-012 - Planner execution Preview does not expose active-step confirmation policy
- AUD-013 - Local TTS result metadata is inconsistent with actual execution

## Exclusions

- No production behavior changes.
- No command recognition, routing, planner parsing, memory normalization, risk classification, confirmation policy, operation tracking, or TTS execution changes.
- No runtime configuration or dependency changes.
- No changes to TASK-090 findings or verdict.
- No real user memory/profile data, microphone hardware, Vosk model, audible TTS, network service, or AI provider is used.

## Safety And Isolation Rules

- All stateful tests use `tmp_path` with isolated memory and profile JSON files.
- TTS tests use a fake local backend only.
- Planner tests use isolated in-process planner state and never confirm destructive forget-all execution.
- Preview assertions verify read-only behavior where state is involved.
- Tests avoid fixed shared workspace state and generated ID equality.

## Current Behavior Matrix

| Finding ID | Scenario | Current observed behavior | Safety invariant | Expected remediation task |
|---|---|---|---|---|
| AUD-008 | Memory remember/recall/forget through Preview and Execute | Preview reports unknown / confirmation-like metadata; Execute recognizes remember, recall, and forget with current memory metadata | Preview exact before/after snapshots prove no fact is added, changed, or deleted; Execute touches only isolated memory | TASK-093 / TASK-094 |
| AUD-009 | Recall `маркер аудита 9073` through `о маркере аудита 9073` | Exact key succeeds; inflected key misses | No cross-key matching is introduced | TASK-094 |
| AUD-010 | `profile.language.set`, `memory.remember`, `memory.forget` metadata | Desktop Shell matches the tested AppService values for the fields it renders, but currently omits the requires-confirmation field. The characterization tests assert both the AppService value and the Desktop omission. Memory writes report `local_write` / succeeded, while language set reports `read_only` and no operation status despite changing isolated profile state | Preview remains read-only | TASK-093 / TASK-094 |
| AUD-011 | `составь план: забудь всё, что ты обо мне помнишь` | Creates ordinary `memory.forget` for literal key text | Plan creation does not delete memory | TASK-092 / TASK-094 |
| AUD-012 | Preview `execute plan` for active forget-all plan | Preview reports read-only / no confirmation; execution pauses at awaiting confirmation; cancellation preserves the operation relationship and a later status read does not resume the plan | No side effect before confirmation or after cancellation | TASK-092 |
| AUD-013 | Local TTS diagnostics and test commands | AppService Preview is unknown; Execute wraps CommandProcessor with generic confirmation metadata; diagnostics, disabled test, enable, and enabled test all have structured Execute metadata assertions; only enabled fake test synthesis speaks through the fake backend once | Fake backend only; no network, file, provider, microphone, or audible speech | TASK-096 |

## Desired Future Contract Matrix

| Finding ID | Scenario | Desired future contract |
|---|---|---|
| AUD-008 | Memory commands | Preview and Execute agree on command id, category, risk, confirmation, network, and read/write metadata without Preview side effects. |
| AUD-009 | Russian inflection | Safe normalization or alias resolution handles natural Russian inflection without accidental unrelated-key matches. |
| AUD-010 | State-changing metadata | State changes consistently expose command id, category, risk, confirmation, operation id/status, and actual mutation status across public routes. |
| AUD-011 | Russian forget-all planner phrase | Natural Russian forget-all maps to the real destructive `memory.forget_all` capability and requires confirmation. |
| AUD-012 | Planner execute Preview | Preview projects the active step's effective confirmation and risk policy for `execute plan`. |
| AUD-013 | Local TTS | TTS result metadata distinguishes diagnostics, mode enablement, not-enabled tests, and actual fake/local synthesis execution accurately. |

## Tests Added

- `tests/characterization/test_preview_execute_contracts.py`
- `tests/characterization/test_memory_language_contracts.py`
- `tests/characterization/test_planner_contracts.py`
- `tests/characterization/test_local_tts_contracts.py`

## Metadata Completeness Notes

- Desktop Shell confirmation metadata is explicitly characterized for `memory.remember`, `memory.forget`, and `profile.language.set`: AppService structured results contain `requires_confirmation=False`, while Desktop Shell currently omits the requires-confirmation line for those routes.
- AppService `profile.language.set` explicitly characterizes `registry_match_id`, `category`, `risk_level`, `executed`, `requires_confirmation`, `network_may_be_used`, `response_executed_as_command`, `operation_id`, `operation_status`, and the isolated language state change.
- Local TTS diagnostics, disabled test, enable, and enabled test Execute routes all explicitly characterize structured result metadata.

## Planner Introspection Boundary

AppService structured results do not currently expose enough detail to distinguish planned `memory.forget` from `memory.forget_all` or inspect literal step arguments. The characterization tests therefore use the planner's read-only `snapshot()` and `steps()` inspection boundary. They do not import or assert private `_PlanState` internals. Future public plan DTO work may replace this inspection route.

## Verification Checklist

- [x] Run newly added characterization tests.
- [x] Run closest existing related suites for AppService, CommandProcessor, memory, profile/language, planner, Desktop Shell Preview/Execute, and local TTS.
- [x] Run `python -m pytest -q`.
- [x] Run `python -W error::DeprecationWarning -m pytest -q`.
- [x] Run `powershell -ExecutionPolicy Bypass -File scripts/health_check.ps1`.
- [x] Run `powershell -ExecutionPolicy Bypass -File scripts/assistant_smoke.ps1`.
- [x] Run `git diff --check`.
- [x] Run `git status --short --untracked-files=all`.

## Verification Evidence

- Targeted characterization: `python -m pytest -q tests/characterization` -> `10 passed in 0.47s`.
- Related suites: `python -m pytest -q tests/unit/test_app_service.py tests/unit/test_desktop_shell.py tests/unit/test_command_processor.py tests/unit/test_memory_aware_conversation.py tests/unit/test_memory_manager.py tests/unit/test_user_language_preference.py tests/unit/test_language_manager.py tests/unit/test_multi_step_planner.py tests/unit/test_plan_executor.py tests/unit/test_voice_output_manager.py tests/unit/test_windows_local_tts_backend.py tests/integration/test_task_086_user_language_preference.py tests/integration/test_task_088_memory_aware_conversation.py tests/integration/test_task_089_general_multi_step_planner.py` -> `486 passed in 2.88s`.
- Full pytest: `python -m pytest -q` -> `1550 passed, 2 skipped in 5.01s`.
- Strict pytest: `python -W error::DeprecationWarning -m pytest -q` -> `1550 passed, 2 skipped in 5.09s`.
- Health: `powershell -ExecutionPolicy Bypass -File scripts/health_check.ps1` -> `Result: SUCCESS`, `Failures: 0`, `Warnings: 0`, internal pytest `1550 passed, 2 skipped in 4.84s`.
- Permanent smoke: `powershell -ExecutionPolicy Bypass -File scripts/assistant_smoke.ps1` -> `JARVIS ASSISTANT SMOKE: SUCCESS`, `1 passed, 1 warning in 0.21s`; warning was a pytest cache write permission warning for `.pytest_cache`.
- Git diff check: `git diff --check -- .ai/tasks/TASK-091-contract-metadata-characterization-tests.md docs/testing/TASK_091_CONTRACT_CHARACTERIZATION.md tests/characterization/test_local_tts_contracts.py tests/characterization/test_memory_language_contracts.py tests/characterization/test_planner_contracts.py tests/characterization/test_preview_execute_contracts.py` -> exit 0; Git printed LF-to-CRLF working-copy warnings only.
- Encoding validation: all six files are valid UTF-8 without BOM, have CRLF count `0`, and LF count greater than `0`.
- Final git status: `git status --short --untracked-files=all` -> exactly the six untracked TASK-091 files.

## Commit And Push

- [ ] Commit left unchecked.
- [ ] Push left unchecked.
