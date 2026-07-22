# TASK-100 - Local TTS Execution Metadata Consistency

Baseline: `53758c9543bbebaf5cbed1320850b610e626dbde` (`Fix Russian planner forget-all routing`).

## Scope

TASK-100 addresses AUD-013 only: local TTS commands execute immediately, but AppService and Desktop metadata reported an unknown command contract and fabricated `requires_confirmation=True`.

Excluded and unchanged:

- AUD-016: low-level microphone permission/device failure presentation.
- Command grammar, command aliases, CommandRegistry, CommandResolutionService, DTO schemas, policy definitions, configuration, dependencies, planner code, memory code, microphone handling, and local TTS backend behavior.

## Problem

Representative local TTS commands:

- `диагностика локального голоса`
- `включить локальный голос`
- `тест локального голоса`

Before TASK-100, Preview remained unknown for these routes and Execute reused that unknown Preview metadata after CommandProcessor completed the real route. Completed results could therefore report:

- `category=None`
- `risk_level=None`
- `requires_confirmation=True`

while also reporting:

- `executed=True`
- operation id present
- `operation_status=succeeded`
- `network_may_be_used=False`

## Root Cause

AppService Preview uses registry/planner/memory metadata and does not recognize the local TTS legacy command groups. AppService Execute routes local TTS through the hybrid resolver into CommandProcessor, but `_execute_resolved_command()` seeded the final result from the unknown Preview projection.

The AppService hybrid resolution object carries `intent_kind=local_command` and command text, but not a local TTS `command_id`. CommandProcessor's own resolver resolves local status and enable, while local test remains legacy passthrough. The stable execution evidence available at the AppService boundary is therefore the existing `processor_result["intent"]`, plus exact normalized command text where `voice.output.spoken` must be distinguished from ordinary speech output.

## Route Evidence

- Diagnostics success: `processor_result["intent"] == "voice.output.local.status"`.
- Enable success: `processor_result["intent"] == "voice.output.windows_local.enabled"`.
- Enable unavailable: `processor_result["intent"] == "voice.output.windows_local.unavailable"`.
- Local test before enable: `processor_result["intent"] == "voice.output.local_test.not_enabled"`.
- Local test after enable: `processor_result["intent"] == "voice.output.spoken"` and normalized command text is exactly a known local TTS test command.
- Diagnostics or enable exceptions are identified only by exact normalized command text because no processor result is returned.

`voice.output.spoken` is shared by ordinary speech routes such as `скажи: <text>`, generic voice tests, and local TTS tests. TASK-100 restricts the local TTS mapping to exact normalized local-test commands so ordinary speech output is not relabeled.

## Correction

AppService now applies a narrow local TTS execution metadata projection after actual route execution evidence is available. It uses existing DTO fields only.

Corrected metadata:

- Diagnostics: command id `voice.output.local.status`, category `voice`, risk `read_only`, `requires_confirmation=False`, network false.
- Enable: command id `voice.output.windows_local.enable`, category `voice`, risk `local_runtime`, `requires_confirmation=False`, network false.
- Local test before enable: command id `voice.output.local_test.not_enabled`, category `voice`, risk `local_runtime`, `requires_confirmation=False`, failed operation.
- Local test after enable: command id `voice.output.spoken`, category `voice`, risk `local_runtime`, `requires_confirmation=False`, succeeded or failed operation according to local TTS result evidence.

CommandProcessor was changed only for the local TTS test result to preserve `local_tts_success` and optional `local_tts_error` from `VoiceOutputManager.test_local_voice()`. This is the minimal boundary needed to represent adapter synthesis failure without parsing user-facing response prose.

Generic failure coordination was narrowed to local TTS AppService results. TASK-100 does not alter unrelated legacy command failure contracts.

## Preview

Preview remains unchanged and side-effect free for local TTS inputs. It does not synthesize speech, enable voice mode, call a TTS adapter, initialize audio hardware, access microphone hardware, call providers, use network, create an operation, create pending confirmation, mutate runtime state, or call CommandProcessor.

## Privacy

Tests use fake local TTS backends only. No real audio hardware is used. Spoken text, backend names, diagnostic payloads, local paths, and backend internals are not added to operation metadata or journal fields by TASK-100.

## Tests

Focused coverage was added or updated for:

- AUD-013 characterization from defect expectations to corrected Execute metadata.
- Preview side-effect freedom for diagnostics, enable, and local test.
- Diagnostics success and diagnostics exception failure.
- Enable success and unavailable failure.
- Local test before enable.
- Local test after enable with fake synthesis success.
- Local test after enable with fake synthesis failure.
- Ordinary `voice.output.spoken` speech output not relabeled as local TTS.
- Unrelated unknown fallback behavior unchanged.
- Desktop rendering of success and failure without fabricated confirmation.
- Journal metadata privacy for fake spoken text and backend internals.

## Preserved Invariants

- AUD-016 was not fixed or intentionally changed.
- TASK-095 invariants remain required: extracted matcher count in `process()` is `0`; remaining matcher count is `50`; exact/mapping/prefix overlap is `0/0/0`; direct `CommandResolutionService` import must not load `CommandProcessor`.
- TASK-096 genuine confirmation and operation-state semantics are preserved.
- TASK-097 memory Preview/Execute recognition parity is preserved.
- TASK-098 recall-only Russian alias and exact bounded forget behavior are preserved.
- TASK-099 Russian planner forget-all classification and confirmation safety are preserved.

## Verification

Focused verification completed before documentation:

- `python -m pytest -q tests/characterization/test_local_tts_contracts.py`: 1 passed.
- `python -m pytest -q tests/unit/test_app_service.py tests/unit/test_desktop_shell.py`: 117 passed.
- `python -m pytest -q tests/characterization/test_preview_execute_contracts.py tests/characterization/test_planner_contracts.py tests/unit/test_execution_coordinator.py tests/unit/test_execution_journal.py tests/unit/test_policy_decision_boundary.py`: 25 passed.
- Focused CommandProcessor/local TTS/TASK-095 batch: 8 passed.

Final verification:

- Full pytest: 1695 passed, 2 skipped.
- Strict pytest: 1695 passed, 2 skipped.
- Health check: SUCCESS, 1695 passed, 2 skipped.
- Assistant smoke: JARVIS ASSISTANT SMOKE: SUCCESS, with one pytest cache warning.
- Import probes:
  - COMMAND RESOLUTION SERVICE IMPORT: SUCCESS.
  - COMMAND PROCESSOR LOADED: False.
  - APP SERVICE IMPORT: SUCCESS.
  - DESKTOP SHELL IMPORT: SUCCESS.
- Changed Python files compiled successfully with `PYTHONDONTWRITEBYTECODE=1`.
- `git diff --check`: passed, with working-copy line-ending warnings only.

Commit: unchecked.
Push: unchecked.
