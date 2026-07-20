# Command Resolution Phase 2

Baseline: `444200859fbc28910f38350b7c21d29e8f211e3f`

TASK-095 continues the TASK-094 command-resolution extraction. The public
facade remains `CommandProcessor.process()`. The internal
`CommandResolutionService` owns more deterministic recognition; execution and
formatting remain in `CommandProcessor`.

## Boundary Change

Moved into `CommandResolutionService`:

- deterministic recognition for voice/Vosk diagnostics;
- microphone mode recognition and canonical mode projection;
- one-shot voice/Vosk recognition commands;
- TTS/voice-output status and mode command recognition;
- assistant identity and assistant-name recognition;
- profile status recognition;
- version and services recognition;
- safe AI/provider diagnostic recognition;
- secure-key diagnostic recognition.

Retained by `CommandProcessor`:

- all state mutation;
- all hardware-adjacent actions;
- all provider/router/gate handler calls;
- all secure-key manager calls;
- profile persistence;
- response construction;
- confirmation and cancellation flows;
- ActionRouter/natural-language fallback.

## Command-Id Dispatch

For Phase 2 routes the resolver returns:

- `resolution_status == RESOLVED`;
- the existing command id;
- normalized text;
- immutable `safe_args`;
- match-source metadata.

`CommandProcessor` dispatches these routes by `command_id` and `safe_args`.
Source-string checks are no longer required for the extracted routes. If a
resolved command id has no dispatch branch, `CommandProcessor` raises an
internal error.

The obsolete duplicate text-recognition branches for TASK-095 routes were
removed from `CommandProcessor.process()`. Extracted routes now have a single
recognition path in `CommandResolutionService` and a single processor-owned
execution path in `_command_resolution_result()`.

## Ownership Invariant

The processor builds resolver command groups from explicit source attributes.
After generated legacy passthrough catalogs are built, extracted exact aliases,
mapping keys, and prefixes are subtracted from legacy ownership. The required
invariant is zero overlap for:

- TASK-094 exact, mapping, and prefix groups;
- TASK-095 exact, mapping, and prefix groups.

Known overlapping aliases keep previous behavior by resolver precedence. For
example, status-style voice-output and secure-key aliases retain the same
handler order they had in `CommandProcessor.process()`.

The characterized shared-alias precedence cases are:

- `тест распознавания` -> `speech.backend.vosk.recognition.dry_run`;
- `путь модели vosk` -> `speech.backend.vosk.model.path.status`;
- `выключи микрофон` -> `microphone.mode.off` with `safe_args["mode"] == "off"`.

After the duplicate-removal correction, the TASK-095 extracted
`process()` matcher count is `0`. The total remaining `process()` matcher
count is `50` using the documented review method; those remaining matchers are
explicit legacy debt.

## Safe Arguments

Phase 2 safe arguments are limited to deterministic projections:

- `{"mode": "off" | "partial" | "continuous"}` for microphone mode commands;
- `{"assistant_name": <original suffix>}` for assistant-name set commands;
- `{"provider": <provider>}` for provider-key diagnostic commands.

The resolver does not validate credentials, load models, touch microphones, or
mutate profile state.

## Exclusions

Still legacy and out of scope:

- confirmation parsing and pending confirmation execution;
- destructive-action confirmation state;
- cancellation confirmations;
- natural-language and ActionRouter fallback;
- hardware-start routes;
- provider-request and session-mutation routes;
- destructive secure-key import/delete flows;
- provider-backed conversation routing;
- AUD-008 through AUD-011.

AUD-008 through AUD-011 remain unchanged.

## Verification Expectations

Automated verification covers direct resolver resolution, processor
command-id dispatch with non-alias normalized text, real ownership invariants,
targeted compatibility suites, full pytest, strict deprecation pytest, health,
assistant smoke, import smoke, diff checks, and staging checks.

Manual smoke is documented in the TASK-095 task note and must remain safe:
status-only provider/key commands, no real microphone capture, no live Vosk
audio, no TTS playback, no secrets, no destructive confirmations.
