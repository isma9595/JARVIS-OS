# TASK-119B - Desktop Cognitive Routing Integration

## Objective

Complete the Desktop Shell routing fix so safe vague references and
clarification control turns are handled through the cognitive intent,
reference, and clarification boundaries before legacy command fallback.

## Root Cause

Confirmation text entered while a clarification was pending could fall through
to legacy command processing when it did not select a clarification option. The
in-progress fix also routed command execution through
`handle_conversation_turn`, which risked recording conversation turns and
running response composition as a side effect of command routing.

## Architectural Solution

- `JarvisAppService` now probes cognitive clarification with the existing
  intent interpreter, reference resolver, and clarification coordinator without
  appending conversation turns or invoking response composition.
- Safe unresolved action references are converted to clarification before
  unsupported or legacy fallback.
- Risky unsupported reasons remain blocked and are not converted to safe
  clarification.
- Pending clarification keeps the same operation id across confirmation-like
  control turns, and cancellation moves the operation to `cancelled`.
- Cancellation has priority over confirmation.
- Confirmation without a resolved target does not execute a command.
- Desktop Shell and AppService expose consistent category/status metadata and
  keep `response_executed_as_command=False`.

## Changed Files

- `app/app_service.py`
- `app/intent_resolver.py`
- `cognition/intent_interpreter.py`
- `cognition/reference_resolver.py`
- `tests/integration/test_task_080_hybrid_intent_resolver.py`
- `tests/unit/test_cognitive_app_service_integration.py`
- `tests/unit/test_desktop_shell.py`

## Tests

- `python -m pytest tests/integration/test_task_080_hybrid_intent_resolver.py::test_clarification_confirmation_word_does_not_select_option -q`
  - Result: `1 passed`
- `python -m pytest tests/integration/test_task_080_hybrid_intent_resolver.py tests/unit/test_cognitive_app_service_integration.py tests/unit/test_desktop_shell.py tests/unit/test_app_service.py tests/smoke/test_assistant_smoke.py -q`
  - Result: `243 passed`
- `python -m pytest tests/unit/test_cognitive_clarification_coordinator.py tests/unit/test_cognitive_interaction_service.py tests/unit/test_cognitive_intent_interpreter.py tests/unit/test_cognitive_reference_resolver.py tests/unit/test_command_processor.py tests/unit/test_command_resolution_service.py -q`
  - Result: `467 passed`
- `python -m pytest tests/integration/test_task_081_unified_policy_boundary.py tests/integration/test_task_082_execution_control.py tests/unit/test_cognitive_architecture.py tests/unit/test_dialogue_manager.py tests/unit/test_voice_input_manager.py -q`
  - Result: `125 passed`
- `git diff --check`
  - Result: passed with Git line-ending conversion warnings only.
- `python -m pytest -q`
  - Result: `2135 passed, 2 skipped`

## Manual Desktop Smoke

The TASK-119B Desktop GUI smoke was completed successfully with:

1. `Сделай это.`
2. `Подтверждаю.`
3. `отмена`
4. `Подтверждаю.`
5. `Сделай это.`
6. `отмена`
7. `удали это`

Expected behavior was confirmed: clarification stays pending when appropriate,
confirmation does not execute without a target, cancellation cancels pending
clarification, risky vague delete remains unsupported, and no
`voice.confirmation` fallback appears.

## Commit Message

Complete desktop cognitive routing integration
