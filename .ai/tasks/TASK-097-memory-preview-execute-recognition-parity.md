# TASK-097 - Memory Preview/Execute Recognition Parity

Baseline: `f08aa62e49896f8aa4a0ca67f07057da1a5d8d47` (`Fix completed command confirmation metadata`).

## Scope

TASK-097 addresses AUD-008 only: supported AppService memory commands were recognized by Execute but not by Preview.

Excluded and unchanged:

- AUD-009: Russian memory-key inflection normalization.
- AUD-011: natural Russian forget-all planner misclassification.
- AUD-013: local TTS result metadata inconsistency.
- AUD-016: technical microphone error presentation.
- Command grammar, aliases, stable command ids, categories, risk classifications, public DTO schemas, configuration, dependencies, provider behavior, hardware behavior, and credential storage.

## Baseline Behavior

Before TASK-097, direct Execute recognized supported memory parser routes:

- `remember that audit091key is north` -> `memory.remember`, `memory`, `local_write`.
- `what do you remember about audit091key` -> `memory.recall`, `memory`, `read_only`.
- `forget audit091key` -> `memory.forget`, `memory`, `local_write`.

Preview did not consult the AppService memory parser for these same supported routes. It fell through to registry-only matching and projected unknown, confirmation-like metadata while remaining non-mutating.

## Source Of Truth

The existing AppService memory parser, `_parse_memory_command()`, is the source of truth for Preview recognition parity. TASK-097 does not duplicate memory grammar and does not infer command type from response text.

## Correction

AppService Preview now calls a narrow private memory projection helper before registry fallback and after the established document and planner preview routes.

The helper:

- reuses `_parse_memory_command()`;
- returns existing `AppCommandPreview` fields only;
- projects supported memory actions without reading, writing, deleting, or listing memory;
- does not call `_handle_memory_command()`;
- does not call `CommandProcessor`;
- does not register operations or create operation ids;
- does not arm pending confirmation.

Corrected Preview contracts:

- remember -> `memory.remember`, `memory`, `local_write`, read-only false, confirmation false.
- recall -> `memory.recall`, `memory`, `read_only`, read-only true, confirmation false.
- forget -> `memory.forget`, `memory`, `local_write`, read-only false, confirmation false.
- direct forget-all -> `memory.forget_all`, `memory`, `confirmation_required`, confirmation true, still non-mutating and not armed.

Vague memory forms remain on the existing clarification or fallback behavior. TASK-097 does not broaden command grammar.

## Tests

Focused coverage was added or updated for:

- AUD-008 characterization of remember, recall, and forget Preview as recognized and non-mutating.
- AppService Preview metadata for remember, recall, forget, and forget-all.
- Preview not mutating memory, not retrieving recall values merely to classify, not creating operation ids or journal entries, and not creating pending confirmations for bounded memory commands.
- Forget-all Preview remaining confirmation-required but non-mutating and not armed.
- Desktop Preview rendering for the exact supported remember, recall, and forget inputs.
- Existing Execute behavior for memory remember, recall, and forget.

## Preserved Invariants

- TASK-096 direct memory operation coordination and journal behavior are preserved.
- Private memory keys and values do not enter operation metadata.
- Genuine awaiting-confirmation behavior remains preserved.
- AUD-009, AUD-011, AUD-013, and AUD-016 were not fixed or intentionally changed.
- TASK-095 invariants remain required: extracted matcher count in `process()` is `0`; remaining matcher count is `50`; exact/mapping/prefix overlap is `0/0/0`; direct `CommandResolutionService` import must not load `CommandProcessor`.

## Completion

- Final verification:
  - Focused characterization batch: 9 passed.
  - Focused AppService/Desktop/resolver/TASK-095 invariant batch: 135 passed.
  - Additional memory, policy, operation, journal, and language regression batch: 94 passed.
  - Full pytest: 1656 passed, 2 skipped.
  - Strict pytest: 1656 passed, 2 skipped.
  - Health check: SUCCESS, 1656 passed, 2 skipped.
  - Assistant smoke: JARVIS ASSISTANT SMOKE: SUCCESS, with one pytest cache warning.
  - Import probes:
    - COMMAND RESOLUTION SERVICE IMPORT: SUCCESS.
    - COMMAND PROCESSOR LOADED: False.
    - APP SERVICE IMPORT: SUCCESS.
    - DESKTOP SHELL IMPORT: SUCCESS.
  - Changed Python files compiled successfully with `PYTHONDONTWRITEBYTECODE=1`.
  - `git diff --check`: passed.
- TASK-095 invariants remain: extracted matcher count in `process()` is `0`; remaining matcher count is `50`; exact/mapping/prefix overlap is `0/0/0`.

Commit: unchecked.
Push: unchecked.
