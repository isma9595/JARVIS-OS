# TASK-099 - Russian Planner Forget-All Classification

Baseline: `b9fb05b16cf4ccab0d2889709c07162d78dd95e5` (`Add safe Russian recall alias`).

## Scope

TASK-099 addresses AUD-011 only: the natural Russian planner phrase for forgetting all memory was misclassified as bounded `memory.forget` instead of destructive `memory.forget_all`.

Excluded and unchanged:

- AUD-013: local TTS result metadata inconsistency.
- AUD-016: low-level microphone error presentation.
- AppService direct memory grammar, memory parsing, LocalMemoryManager, CommandResolutionService, CommandRegistry, CommandProcessor, DTO schemas, command IDs, categories, risks, policy definitions, dependency manifests, and configuration.

## Problem

Defective input:

- `составь план: забудь всё, что ты обо мне помнишь`

Previous incorrect planner step:

- `memory.forget`
- arguments: `{"key": "всё, что ты обо мне помнишь"}`
- `requires_confirmation=False`

Corrected planner step:

- `memory.forget_all`
- arguments: `{}`
- risk: `confirmation_required`
- `requires_confirmation=True`

## Root Cause

Planner step parsing in `planner/multi_step_planner.py` already recognized the exact Russian forget-all word order `забудь все что ты помнишь обо мне`. Existing normalization converts `ё` to `е` and collapses punctuation/whitespace, but the audited phrase normalizes to `забудь все что ты обо мне помнишь`. That normalized word order was missing, so parsing fell through to the generic `забудь ` bounded-forget branch.

## Correction

Planner parsing is the source of truth for this task. TASK-099 adds an exact normalized forget-all step set that includes:

- `забудь все что ты помнишь обо мне`
- `забудь все что ты обо мне помнишь`
- `forget everything you remember about me`

The forget-all exact check still runs before the generic bounded `забудь ` / `forget ` branch.

## Boundaries

Matching remains exact and conservative. TASK-099 does not infer global deletion from arbitrary phrases containing `забудь всё`.

Negative phrases remain bounded `memory.forget`:

- `забудь всё о проекте X`
- `забудь всё про работу`
- `забудь всё о настройках`
- `забудь всё, что касается проекта X`
- `забудь ключ`
- `забудь маркер аудита 9073`

## Safety Guarantees

Preview of the Russian create-plan phrase:

- classifies the proposed step as `memory.forget_all`;
- projects confirmation-required metadata for that proposed step;
- creates no active plan;
- creates no operation ID;
- creates no pending confirmation;
- creates no journaled destructive operation;
- mutates no memory;
- calls no CommandProcessor, provider, network, audio, microphone, or hardware path.

Execute of the create-plan command creates only a proposed plan snapshot. It does not execute the destructive step, delete memory, or register a completed destructive operation.

Plan execution reaches the existing real confirmation boundary: `execute plan` pauses at `awaiting_confirmation`, creates an operation ID through existing coordinator behavior, and does not delete memory before explicit confirmation. Cancellation preserves memory and cancels the pending operation. TASK-099 tests do not send `yes`, `да`, `confirm`, or any equivalent affirmative confirmation.

## Tests

Focused coverage was added or updated for:

- AUD-011 characterization from bounded `memory.forget` to destructive `memory.forget_all` with confirmation required.
- Exact audited Russian phrase.
- Existing Russian word-order form.
- Existing punctuation and `ё` normalization.
- Negative bounded-forget phrases.
- Forget-all exact check precedence before generic bounded forget.
- Planner command service Preview and Execute create-plan parity.
- AppService Preview and Execute create-plan non-mutation.
- Plan execution awaiting-confirmation and cancellation memory preservation.
- Desktop rendering of proposed and awaiting-confirmation forget-all plan metadata.

## Preserved Invariants

- AUD-013 and AUD-016 were not fixed or intentionally changed.
- TASK-095 invariants remain required: extracted matcher count in `process()` is `0`; remaining matcher count is `50`; exact/mapping/prefix overlap is `0/0/0`; direct `CommandResolutionService` import must not load `CommandProcessor`.
- TASK-096 operation coordination and genuine confirmation behavior are preserved.
- TASK-097 memory Preview/Execute recognition parity is preserved.
- TASK-098 recall-only Russian alias and exact bounded-forget safety are preserved.
- Memory keys and values do not enter operation metadata or logs.
- Preview does not call providers, network, audio, microphone, hardware, or `CommandProcessor`.

## Completion

- Final verification:
  - Focused characterization batch: 10 passed.
  - Focused planner, cross-layer, and TASK-095 batch: 168 passed.
  - Coordination, policy, journal, memory, and memory-aware regression batch: 65 passed.
  - Additional plan execution, language, privacy, and memory-aware regression batch: 48 passed.
  - Full pytest: 1681 passed, 2 skipped.
  - Strict pytest: 1681 passed, 2 skipped.
  - Health check: SUCCESS, 1681 passed, 2 skipped.
  - Assistant smoke: JARVIS ASSISTANT SMOKE: SUCCESS, with one pytest cache warning.
  - Import probes:
    - COMMAND RESOLUTION SERVICE IMPORT: SUCCESS.
    - COMMAND PROCESSOR LOADED: False.
    - APP SERVICE IMPORT: SUCCESS.
    - PLANNER IMPORT: SUCCESS.
  - Changed Python files compiled successfully with `PYTHONDONTWRITEBYTECODE=1`.
  - TASK-095 invariant tests passed in the focused planner/cross-layer batch.
  - `git diff --check`: passed.

Commit: unchecked.
Push: unchecked.
