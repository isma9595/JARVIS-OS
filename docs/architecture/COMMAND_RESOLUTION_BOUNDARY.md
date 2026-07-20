# Command Resolution Boundary

Baseline: `e7b459fe09fa0478967f03a56a5d2857d0b5f7d1`

TASK-094 Phase 1 addresses AUD-001 by separating deterministic command
interpretation from `CommandProcessor` execution. It also updates architecture
documentation for AUD-003.

## Boundary

`CommandProcessor` remains the public execution facade. Current callers still
call `CommandProcessor.process()`.

`CommandResolutionService` is an internal deterministic resolver. It receives
only interpretation dependencies:

- `CommandRegistry`;
- optional `HybridIntentResolver`;
- explicit command groups owned by the facade.

It does not receive or import `CommandProcessor`.

## Resolution Contract

`CommandResolution` is an immutable internal dataclass with:

- original text;
- normalized text;
- resolution status;
- command id;
- category;
- safe parsed arguments;
- clarification prompt and candidate tuple;
- confidence and match source;
- safe reason code;
- unknown flag;
- selected command text;
- optional command metadata.

`safe_args` is stored as a defensive immutable mapping. Caller-owned
dictionaries cannot mutate a resolution after construction, and `to_dict()`
returns a fresh normal dictionary.

Resolution statuses are:

- `EMPTY`: normalized input is empty.
- `RESOLVED`: Phase 1 owns the route and `CommandProcessor` must dispatch by
  `command_id` and `safe_args`.
- `LEGACY_PASSTHROUGH`: the command is recognized as an existing route, but
  Phase 1 has not extracted its dispatch yet; legacy text checks may continue.
- `REQUIRES_CLARIFICATION`: deterministic execution is blocked on a bounded
  clarification choice.
- `UNKNOWN`: genuine unknown input for the existing processor-owned fallback.

The DTO contains no callbacks, credentials, provider objects, operation ids,
or private execution objects.

## Exact Match Flow

1. `CommandProcessor.process()` calls the resolver once.
2. The resolver normalizes input with the legacy trim/lowercase/whitespace
   collapse behavior.
3. It checks injected exact command groups and existing prefix forms.
4. It returns a `CommandResolution`.
5. `CommandProcessor` executes `RESOLVED` routes mechanically by
   `command_id` and `safe_args`.

Fully extracted Phase 1 families are command-registry routes, Desktop Shell,
AppService status/capabilities/commands/preview, conversation
status/capabilities/preview, vertical integration, app-contracts, audio
lifecycle, memory, idea, provider-runtime provider-status, `system.status`,
current language get/set/reset, and clarification selection to
`system.status`.

When `CommandProcessor` constructs the resolver inputs, each extracted
attribute-backed group is tied to its explicit source class attribute name.
Those exact source attributes are excluded from generated legacy passthrough
collections. The extracted exact alias, mapping alias, and prefix catalogs have
zero overlap with the legacy passthrough catalogs.

Legacy passthrough remains for the other existing `CommandProcessor` text
families, including voice and Vosk, microphone, general assistant/profile
identity, version/services, AI/provider status families not listed above,
secure keys, confirmation flows, and natural/ActionRouter fallback behavior.
Those routes are explicitly distinguishable from `UNKNOWN`.

## Hybrid Flow

When direct deterministic matching does not resolve the input, the resolver
uses `HybridIntentResolver` for non-executing metadata and clarification
projection. The resolver does not call providers or ActionRouter.

## Clarification Flow

Ambiguous status text returns `REQUIRES_CLARIFICATION` with immutable
candidate options. `CommandProcessor` stores the pending clarification state.
A valid follow-up answer is resolved by the service to the selected existing
command, and `CommandProcessor` executes that command through the same
command-id dispatch path.

If a pending clarification receives an invalid answer that is not a known
independent command, the same clarification is re-rendered and no unrelated
handler executes. If the next input is a clearly resolved or legacy known
standalone command, `CommandProcessor` cancels the stale clarification before
executing that command.

## Unknown Flow

Unknown input returns an internal `UNKNOWN` resolution with the legacy fallback
reason. `UNKNOWN` is not used to mean "continue old command matching" for
known routes. `CommandProcessor` keeps policy checks, ActionRouter fallback,
future idea classification, and final response construction for genuine
unknown input.

## Execution Boundary

The resolver never:

- executes commands;
- mutates memory, profile, language, planner, voice, audio, or filesystem
  state;
- registers operations;
- resumes or confirms operations;
- calls providers or networks;
- reads secrets;
- constructs Desktop Shell output.

`CommandProcessor` continues to own all of those behaviors.

## Preserved Limitations

TASK-094 intentionally does not remediate:

- AUD-008, Preview/Execute memory recognition inconsistency;
- AUD-009, Russian memory-key inflection;
- AUD-010, state-changing metadata inconsistency;
- AUD-011, Russian forget-all misclassification.

Existing characterization is expected to remain unchanged.

Remaining recognition debt: many deterministic legacy branches still live in
`CommandProcessor.process()` and are intentionally classified as
`LEGACY_PASSTHROUGH` until later phases extract their command-id dispatch.
The remaining 140 process text checks belong only to explicit legacy debt.

## Testing

Direct resolver tests cover exact system resolution, ambiguous status
clarification, clarification continuation, memory add/recall/forget
resolution, the known Russian forget-all limitation, unknown fallback
classification, immutability, and determinism.

CommandProcessor delegation tests inject a spy resolver and verify one
resolver call per input, exact dispatch, clarification without execution,
unknown fallback, and execution-error ownership.

Ownership tests use the real `CommandProcessor` group construction and verify
all extracted attribute-backed exact aliases, mapping aliases, and prefixes are
disjoint from generated legacy passthrough catalogs.

Full verification remains targeted pytest, full pytest, strict deprecation
pytest, health check, assistant smoke, import smoke, diff checks, and staging
checks. Commit and push remain unchecked.

## Rollback

Revert the resolver module, the constructor/delegation changes in
`core/command_processor.py`, the TASK-094 tests, and TASK-094 docs. No
configuration, dependencies, public DTO fields, Desktop Shell output, command
grammar, or command metadata are part of the rollback.
