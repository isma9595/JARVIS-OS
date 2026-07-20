# TASK-094 - CommandProcessor Responsibility Extraction, Phase 1

Baseline: `e7b459fe09fa0478967f03a56a5d2857d0b5f7d1`

Audit finding addressed:

- Primary: AUD-001, `CommandProcessor` combines interpretation, routing,
  execution, response formatting, state changes, and fallback behavior.
- Related: AUD-003, architecture documentation must reflect the actual
  command-processing boundary.

Status: corrected after independent review; commit and push unchecked.

## Phase 1 Objective

Extract deterministic command interpretation from `CommandProcessor` into one
internal service while preserving the existing public execution facade and
external behavior.

## Responsibilities Moved

`CommandResolutionService` now owns:

- input normalization for command recognition;
- exact command-group matching for command-registry, AppService, Desktop Shell,
  conversation, vertical integration, audio lifecycle, app-contract,
  provider-runtime provider-status, idea, memory, `system.status`, and current
  language get/set/reset routes extracted in Phase 1;
- command-registry alias lookup only when the returned command id has a
  processor command-id dispatch path;
- explicit `LEGACY_PASSTHROUGH` classification for known routes not yet
  extracted;
- HybridIntentResolver-backed ambiguous status clarification projection;
- clarification candidate selection;
- safe prefix argument extraction for existing memory, idea, registry search,
  AppService preview, and conversation preview forms;
- unknown-command classification for genuine ActionRouter fallback input.

## Responsibilities Retained By CommandProcessor

`CommandProcessor` remains the public execution facade and still owns:

- `process()`;
- command handler invocation;
- state mutation;
- memory, profile, language, voice, audio, provider, and filesystem calls;
- operation and confirmation handling;
- policy checks;
- ActionRouter fallback execution;
- response object construction and response history handling;
- error behavior.

## Dependency Direction

Required direction:

`CommandProcessor -> CommandResolutionService -> CommandRegistry /
HybridIntentResolver / neutral contracts`

Forbidden direction:

`CommandResolutionService -> CommandProcessor`

The resolver receives the command registry, optional hybrid resolver, and
explicit command groups. It does not receive a `CommandProcessor` instance and
does not import it.

Extracted attribute-backed groups are declared with explicit source
`CommandProcessor` attribute names when `CommandProcessor` constructs the
resolver input. Those exact source attributes are excluded from generated
legacy passthrough collections. Extracted exact aliases, mapping aliases, and
prefixes have zero overlap with the legacy catalogs.

## Internal Resolution DTO

`CommandResolution` is a frozen dataclass. It contains only deterministic
interpretation data needed by `CommandProcessor`: original and normalized text,
resolution status, command id, category, safe parsed arguments, clarification
prompt/candidates, confidence, match source, safe reason code, unknown flag,
optional command text, and optional registry metadata.

The candidate collection is a tuple. `safe_args` is stored as an immutable
defensive mapping, caller-owned argument dictionaries cannot mutate it, and
`to_dict()` returns a fresh mutable copy.

## Flows

Exact-match flow:

1. Normalize input.
2. Check injected deterministic command groups.
3. Extract safe text arguments for existing prefix commands.
4. Return a `CommandResolution`.
5. `CommandProcessor` dispatches `RESOLVED` routes by `command_id` and
   `safe_args` only.

Resolution statuses:

- `EMPTY`: no command text after normalization.
- `RESOLVED`: fully extracted Phase 1 route; no text re-match is required.
- `LEGACY_PASSTHROUGH`: existing known route left in legacy dispatch for this
  phase.
- `REQUIRES_CLARIFICATION`: bounded choice is required or an invalid answer
  must re-render the current clarification.
- `UNKNOWN`: genuine unknown input for existing fallback behavior.

Hybrid-resolution flow:

1. If no direct deterministic match exists, ask `HybridIntentResolver`.
2. Use it only for metadata and clarification projection.
3. Do not execute from the resolver.

Clarification flow:

1. Ambiguous status text returns `REQUIRES_CLARIFICATION`.
2. `CommandProcessor` stores the pending clarification state.
3. A follow-up is matched by the resolver against immutable options.
4. `CommandProcessor` executes the selected existing command by command id.
5. Invalid clarification answers re-render the same clarification without
   executing unrelated handlers.
6. Clearly resolved or legacy known standalone commands cancel stale
   clarification before executing.

Unknown-command flow:

1. If no deterministic, legacy, or hybrid clarification match exists, return
   `UNKNOWN`.
2. `CommandProcessor` keeps the legacy policy and ActionRouter fallback.

Execution boundary:

- The resolver never calls handlers, providers, memory, profile, voice, audio,
  filesystem, operation registration, or confirmation execution.
- All side effects remain in `CommandProcessor`.

## Exclusions

No planner behavior change, grammar expansion, Russian forget-all correction,
Russian memory inflection correction, AUD-008 through AUD-011 remediation,
risk-policy change, confirmation-policy change, operation lifecycle redesign,
provider routing, voice/Vosk/TTS change, Desktop Shell redesign, public API
redesign, dependency change, configuration change, or broad handler
reorganization is included.

Fully extracted command families:

- command-registry status/list/categories/category/search;
- AppService status/capabilities/commands/preview;
- Desktop Shell status/capabilities;
- conversation status/capabilities/preview;
- vertical integration status/checklist/summary;
- app-contract status/manifest/status-cards/command-cards;
- audio lifecycle status/capabilities/reset metadata;
- provider-runtime provider-status;
- memory add/delete-request/count/recent/about-user/list/search;
- idea add/list/count;
- `system.status`;
- current language get/set/reset;
- clarification selection to `system.status`.

Legacy passthrough families include the remaining existing
`CommandProcessor.process()` text branches: voice/Vosk/TTS, microphone,
assistant/profile identity and name management, version/services, AI/provider
families not listed above, secure keys, confirmation flows, and the existing
natural/ActionRouter fallback path.

## Rollback Notes

Rollback is limited to reverting:

- `core/command_resolution_service.py`;
- resolver injection and dispatch edits in `core/command_processor.py`;
- TASK-094 tests;
- this task note;
- `docs/architecture/COMMAND_RESOLUTION_BOUNDARY.md`.

No configuration, dependency, command grammar, command metadata, public DTO, or
Desktop Shell output migration is involved.

## Testing Strategy

- Direct resolver tests construct `CommandResolutionService` without
  constructing `CommandProcessor`.
- Direct resolver tests cover `RESOLVED`, `LEGACY_PASSTHROUGH`, `UNKNOWN`,
  immutable `safe_args`, defensive input copies, language routes,
  clarification selection, invalid clarification answers, and deterministic
  equivalent resolutions without operation ids.
- CommandProcessor delegation tests inject a spy resolver and verify one
  resolver call per input, command-id dispatch with deliberately non-matching
  normalized text, argument-bearing dispatch, legacy passthrough continuation,
  provider-runtime provider-status single ownership, clarification lifecycle,
  unknown fallback ownership, and execution-error ownership.
- Ownership tests use the real `CommandProcessor` group construction and verify
  extracted exact aliases, mapping aliases, and prefixes are disjoint from
  generated legacy passthrough catalogs.
- Existing CommandProcessor, AppService, Desktop Shell, memory, language,
  hybrid intent, and characterization tests remain unchanged.
- Full pytest, strict deprecation pytest, health check, and assistant smoke
  must pass before any future commit.

Remaining process text checks are explicit legacy debt only. The current count
is 140.

## Manual Smoke Checklist

Run later only against an isolated state:

1. Execute `статус системы`.
2. Execute ambiguous command `покажи статус`.
3. Provide the current clarification `системы`.
4. Execute exact temporary memory write
   `remember task094smokemarker = north`.
5. Recall `what do you remember about task094smokemarker`.
6. Forget only the temporary marker `forget task094smokemarker`.
7. Execute one unknown harmless phrase and verify the existing fallback.

Do not run forget-all and do not send `yes` or `да`.

## Safety Checklist

- [x] No dependency or configuration change.
- [x] No command grammar or metadata change.
- [x] No public API or DTO field change.
- [x] No Desktop Shell output change.
- [x] AUD-008 through AUD-011 left unchanged.
- [x] No real profile, microphone, Vosk, audible TTS, provider, network, or
  secret used.
- [x] No destructive confirmation sent.
- [ ] Commit unchecked.
- [ ] Push unchecked.
