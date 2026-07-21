# TASK-098 - Russian Memory Recall Inflection Alias

Baseline: `0942886227cbf5b47e433714c7cfaf38c4f3703b` (`Align memory preview recognition`).

## Scope

TASK-098 addresses AUD-009 only: Russian memory-key inflection was not normalized for natural read-only recall.

Excluded and unchanged:

- AUD-011: natural Russian forget-all planner misclassification.
- AUD-013: local TTS result metadata inconsistency.
- AUD-016: technical microphone error presentation.
- AppService command grammar, planner grammar, CommandResolutionService aliases, CommandProcessor behavior, registry aliases, public command IDs, categories, risks, DTO schemas, storage file formats, configuration, and dependencies.

## Problem

Representative stored key:

- `маркер аудита 9073`

Representative exact recall:

- `что ты помнишь о маркер аудита 9073`

Representative natural inflected recall:

- `что ты помнишь о маркере аудита 9073`

Before TASK-098, the exact form returned the stored value but the inflected query missed even though AppService correctly classified the command as `memory.recall`.

## Source Of Truth

`LocalMemoryManager` owns memory-key normalization and lookup. TASK-098 keeps AppService parsing, planner parsing, CommandProcessor, CommandResolutionService, and registry aliases unchanged.

## Correction

Recall now performs:

1. existing exact normalization;
2. exact stored-key lookup;
3. if exact lookup misses, a narrow read-only alias candidate lookup for the documented `маркере` -> `маркер` inflection case;
4. safe miss when there is no single deterministic alias match.

The alias path is recall-only. It is not used by `remember_user_fact()`, `forget_user_fact()`, forget-all behavior, write-time normalization, serialization, migration, or stored-key updates.

## Collision And Ambiguity Behavior

- Exact lookup has absolute priority.
- If an exact stored key exists for the query, alias candidates are not derived.
- If both `маркер аудита 9073` and `маркере аудита 9073` exist, exact queries return their exact values.
- If alias candidates match multiple stored records, recall returns the existing safe miss instead of guessing.

## Storage Guarantees

Inflected recall does not rename keys, duplicate records, persist aliases, rewrite the memory file, change stored normalized keys, alter serialization order or schema, or update timestamps/metadata.

## Tests

Focused coverage was added or updated for:

- AUD-009 characterization from inflected miss to corrected read-only hit.
- Exact recall.
- Documented inflected recall.
- Exact-first lookup before alias derivation.
- Exact-key collision behavior.
- Ambiguous alias candidates returning a safe miss.
- No alias persistence or serialized storage mutation.
- Bounded forget staying exact and conservative.
- Remember not writing through recall alias normalization.
- Unrelated Russian keys not being over-normalized.
- AppService Execute returning `memory.recall` / `memory` / `read_only`, no confirmation, no operation id, no mutation, and no CommandProcessor call for the inflected phrase.
- Preview remaining recognition-only and non-mutating for the same inflected phrase.

## Preserved Invariants

- AUD-011, AUD-013, and AUD-016 were not fixed or intentionally changed.
- TASK-095 invariants remain required: extracted matcher count in `process()` is `0`; remaining matcher count is `50`; exact/mapping/prefix overlap is `0/0/0`; direct `CommandResolutionService` import must not load `CommandProcessor`.
- TASK-096 operation coordination and genuine confirmation behavior are preserved.
- TASK-097 memory Preview/Execute recognition parity is preserved.
- Memory keys and values do not enter operation metadata or logs.
- Preview does not call providers, network, audio, microphone, hardware, or `CommandProcessor`.

## Completion

- Final verification:
  - Focused characterization batch: 10 passed.
  - Focused memory and cross-layer batch: 183 passed.
  - Additional storage, journal, operation, language, and privacy regression batch: 69 passed.
  - Full pytest: 1667 passed, 2 skipped.
  - Strict pytest: 1667 passed, 2 skipped.
  - Health check: SUCCESS, 1667 passed, 2 skipped.
  - Assistant smoke: JARVIS ASSISTANT SMOKE: SUCCESS, with one pytest cache warning.
  - Import probes:
    - COMMAND RESOLUTION SERVICE IMPORT: SUCCESS.
    - COMMAND PROCESSOR LOADED: False.
    - APP SERVICE IMPORT: SUCCESS.
    - MEMORY MANAGER IMPORT: SUCCESS.
  - Changed Python files compiled successfully with `PYTHONDONTWRITEBYTECODE=1`.
  - TASK-095 invariant tests: 3 passed.
  - `git diff --check`: passed.
- TASK-095 invariants remain: extracted matcher count in `process()` is `0`; remaining matcher count is `50`; exact/mapping/prefix overlap is `0/0/0`.

Commit: unchecked.
Push: unchecked.
