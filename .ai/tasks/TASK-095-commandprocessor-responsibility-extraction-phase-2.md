# TASK-095 - CommandProcessor Responsibility Extraction, Phase 2

Baseline: `444200859fbc28910f38350b7c21d29e8f211e3f`

Relationship to TASK-094: Phase 2 extends the same internal
`CommandResolutionService` boundary created in TASK-094. It does not replace
the public `CommandProcessor.process()` facade.

Audit findings:

- Primary: AUD-001, `CommandProcessor` still combines interpretation,
  dispatch, execution, formatting, mutation, and fallback behavior.
- Related: AUD-003, architecture documentation must match the actual command
  processing boundary.

Status: implementation, tests, and focused docs only. Commit and push
unchecked.

Focused duplicate-recognition correction:

- Obsolete TASK-095 text-recognition branches were removed from
  `CommandProcessor.process()`.
- TASK-095 extracted routes now have one recognition path in
  `CommandResolutionService` and one processor-owned execution path through
  `_command_resolution_result()`.
- TASK-095 extracted `process()` source-attribute matcher count is `0`.
- Total remaining `process()` matcher count is `50` using the documented
  review method; the remaining matchers are explicit legacy debt.
- Shared-alias precedence is characterized for `тест распознавания`,
  `путь модели vosk`, and `выключи микрофон`.

## Phase 2 Scope

Recognition moved to `CommandResolutionService` for existing deterministic
commands in these families:

- voice and Vosk status/diagnostics;
- microphone mode read and set routes, plus one-shot listen recognition;
- one-shot Vosk bridge and explicit one-shot recognition routes;
- TTS/voice-output status, diagnostics, enable/disable, and safety commands;
- assistant identity, assistant-name set, and assistant-name reset;
- profile status;
- version and services;
- safe AI/provider status and diagnostics;
- secure-key status, list, and help diagnostics.

No new command aliases, command ids, capability ids, risk metadata, categories,
DTO fields, dependencies, or configuration were added.

## Responsibilities Moved

The resolver now owns deterministic recognition for the Phase 2 groups,
including:

- exact group matching;
- explicit mapping group matching for provider-key status checks;
- assistant-name prefix recognition;
- safe argument projection for microphone mode, assistant name, provider name;
- `RESOLVED` versus `LEGACY_PASSTHROUGH` versus `UNKNOWN` classification.

The resolver remains read-only. It does not execute commands.

## Responsibilities Retained

`CommandProcessor` still owns:

- `process()`;
- command-id dispatch;
- all handler invocation;
- profile and assistant-name mutation;
- microphone mode mutation and one-shot capture execution;
- Vosk runtime, model, and dry-run handler calls;
- TTS mode mutation, safety flags, and any speech-producing command execution;
- provider/router/gate status handler calls;
- secure-key status/list/help formatting through the key manager;
- response formatting and response history;
- policy checks;
- confirmation state;
- ActionRouter and natural-language fallback.

## Dependency Direction

Required direction:

`CommandProcessor -> CommandResolutionService -> CommandRegistry /
HybridIntentResolver / neutral contracts`

Forbidden direction:

`CommandResolutionService -> CommandProcessor`

The processor passes explicit command groups into the resolver. The resolver
does not import the processor and does not own handler objects.

## Ownership Map

Phase 2 uses explicit resolver group names and source attributes. Attribute
names are not inferred by lowercasing, suffix stripping, or string replacement.

Exact collection examples:

- `voice_status` -> `VOICE_STATUS_COMMANDS` -> `voice.status` -> `{}`
- `vosk_recognition_status` -> `VOSK_RECOGNITION_STATUS_COMMANDS` ->
  `speech.backend.vosk.recognition.status` -> `{}`
- `microphone_status` -> `MICROPHONE_STATUS_COMMANDS` ->
  `microphone.mode.status` -> `{}`
- `voice_output_local_status` -> `VOICE_OUTPUT_LOCAL_STATUS_COMMANDS` ->
  `voice.output.local.status` -> `{}`
- `assistant_identity` -> `ASSISTANT_IDENTITY_COMMANDS` ->
  `assistant.identity` -> `{}`
- `profile_status` -> `PROFILE_COMMANDS` -> `user.profile` -> `{}`
- `system_version` -> `VERSION_COMMANDS` -> `system.version` -> `{}`
- `system_services` -> `SYSTEM_SERVICES_COMMANDS` -> `system.services` -> `{}`
- `ai_status` -> `AI_STATUS_COMMANDS` -> `ai.status` -> `{}`
- `secure_key_status` -> `SECURE_KEY_STATUS_COMMANDS` ->
  `secure_keys.status` -> `{}`

Mapping collection:

- `ai_provider_key_check` -> `AI_PROVIDER_KEY_CHECK_COMMANDS` ->
  `ai.key_check` -> `{"provider": <provider>}`

Prefix collection:

- `assistant_name_change` -> `ASSISTANT_NAME_CHANGE_PREFIXES` ->
  `assistant.name.set` -> `{"assistant_name": <original suffix>}`

Microphone mode exact groups project canonical mode:

- `microphone_mode_off` -> `MICROPHONE_MODE_OFF_COMMANDS` ->
  `microphone.mode.off` -> `{"mode": "off"}`
- `microphone_mode_partial` -> `MICROPHONE_MODE_PARTIAL_COMMANDS` ->
  `microphone.mode.partial` -> `{"mode": "partial"}`
- `microphone_mode_continuous` -> `MICROPHONE_MODE_CONTINUOUS_COMMANDS` ->
  `microphone.mode.continuous` -> `{"mode": "continuous"}`
- `microphone_mode_disable_continuous` ->
  `MICROPHONE_MODE_DISABLE_CONTINUOUS_COMMANDS` -> `microphone.mode.off` ->
  `{"mode": "off"}`

## Dispatch Rule

Every newly extracted route returns `RESOLVED` with `command_id` and immutable
`safe_args`. `CommandProcessor` dispatches these routes through
`_command_resolution_result()`. A resolved command id without a dispatch
branch raises an internal error.

Generated legacy passthrough catalogs subtract all extracted exact, mapping,
and prefix ownership so extracted routes cannot overlap with legacy ownership.
After duplicate branch removal, extracted routes must not be recognized again
by normalized text in `process()`.

## Exclusions

Confirmation flows remain legacy:

- yes/no parsing;
- destructive confirmations;
- pending operation confirmation state;
- cancellation confirmation execution.

ActionRouter fallback remains legacy:

- natural-language fallback;
- unknown future-idea behavior;
- semantic action selection;
- provider-backed fallback and broad conversation routing.

Hardware-start, provider-request, and destructive secure-key flows also remain
legacy and out of scope for this correction.

Known audit limitations unchanged:

- AUD-008 preview/execute memory inconsistency;
- AUD-009 Russian memory-key inflection;
- AUD-010 state-changing metadata inconsistency;
- AUD-011 Russian forget-all misclassification.

AUD-008 through AUD-011 remain unchanged.

## Safety Restrictions

The resolver must not:

- start listening or capture audio;
- load a real Vosk model;
- play TTS;
- call providers or networks;
- read or print secrets;
- mutate memory, profile, language, filesystem, or operations;
- construct Desktop Shell output.

Automated tests must not send destructive confirmations such as `yes` or `da`
for destructive operations.

## Rollback Notes

Rollback is limited to reverting:

- `core/command_resolution_service.py`;
- focused resolver group and dispatch edits in `core/command_processor.py`;
- TASK-095 tests;
- `docs/architecture/COMMAND_RESOLUTION_PHASE_2.md`;
- this task note.

No dependency, configuration, public API, DTO, Desktop Shell output, command
grammar, or metadata rollback is involved.

## Automated Test Plan

- Direct resolver tests for every Phase 2 family present in the repository.
- Spy `CommandProcessor` dispatch tests using non-alias normalized text.
- Ownership invariant tests using real `_command_resolution_groups()`.
- AST ownership test proving `process()` no longer references TASK-095
  extracted source attributes.
- Shared-alias precedence tests for overlapping recognition families.
- Existing voice, Vosk, microphone, one-shot, TTS, assistant-name, profile,
  provider, secure-key, AppService, Desktop Shell, memory, language, hybrid,
  and characterization tests.
- Full pytest.
- Strict deprecation pytest.
- Health check.
- Assistant smoke.
- Import smoke proving resolver import does not load processor.

## Manual Smoke Checklist

Document only; do not run automatically:

1. `status`
2. one Vosk or voice status command
3. microphone mode status
4. set microphone mode to partial, then restore off
5. TTS status without playback
6. assistant current-name query
7. version
8. services
9. provider status without provider request
10. secure-key status without credential values
11. harmless greeting
12. harmless unknown command

Do not start microphone capture, load live audio, play TTS, call a provider,
print secrets, change real profile fields except a reversible temporary
assistant-name marker if strictly necessary, or execute destructive
confirmation.

## Manual Smoke Metadata Investigation

Follow-up baseline check against commit
`444200859fbc28910f38350b7c21d29e8f211e3f` found no TASK-095 Desktop Shell
metadata regression for the eight observed commands.

Committed baseline and current Desktop/AppService metadata:

- `тест распознавания`: processor route
  `speech.backend.vosk.recognition.dry_run`; AppService command id `none`,
  category `unknown`, risk `unknown`; Desktop command id `none`, category
  `unknown`, risk `unknown`. Current resolver command id is
  `speech.backend.vosk.recognition.dry_run`.
- `путь модели vosk`: processor route
  `speech.backend.vosk.model.path.status`; AppService/Desktop command id
  `none`, category `unknown`, risk `unknown`. Current resolver command id is
  `speech.backend.vosk.model.path.status`.
- `статус микрофона`: processor route `microphone.mode.status`;
  AppService/Desktop command id `none`, category `unknown`, risk `unknown`.
  Current resolver command id is `microphone.mode.status`.
- `профиль`: processor route `user.profile`; AppService/Desktop command id
  `none`, category `unknown`, risk `unknown`. Current resolver command id is
  `user.profile`.
- `версия`: processor route `system.version`; AppService/Desktop command id
  `none`, category `unknown`, risk `unknown`. Current resolver command id is
  `system.version`.
- `покажи сервисы`: processor route `system.services`; AppService/Desktop
  command id `none`, category `unknown`, risk `unknown`. Current resolver
  command id is `system.services`.
- `статус голосового ответа`: processor route `voice.output.status`;
  AppService/Desktop command id `voice.output_status`, category `voice`, risk
  `read_only`. The preliminary expectation `voice.output.status` was not the
  committed AppService/Desktop metadata id.
- `как тебя зовут`: processor route `assistant.identity`;
  AppService/Desktop command id `profile.assistant_name`, category `profile`,
  risk `read_only`. The preliminary expectation `assistant.identity` was not
  the committed AppService/Desktop metadata id.

Classification:

- No regression: the first six commands intentionally preserved the committed
  AppService/Desktop `none`/`unknown` metadata while executing successfully.
- Preliminary expectation was wrong: the two registry-backed commands preserve
  committed stable AppService/Desktop ids `voice.output_status` and
  `profile.assistant_name`.
- TASK-095 regressions found: none.

Correction made: none to production code. Focused characterization tests were
added for the eight commands to pin resolver command ids, command-id dispatch,
and AppService/Desktop metadata.

Completed safe manual Desktop Shell smoke:

- `тест распознавания`: safe test-data Vosk dry run succeeded; no microphone;
  no real Vosk model loading; no real recognition; no network; no secrets.
  Desktop metadata preserved from baseline: command id `none`, category
  `unknown`, risk `unknown`.
- `путь модели vosk`: model-path setting read successfully; model files were
  not opened; model was not loaded; microphone was not started; no network; no
  secrets; path was redacted by the shell. Desktop metadata preserved from
  baseline: command id `none`, category `unknown`, risk `unknown`.
- `статус микрофона`: microphone reported OFF; no capture started; no state
  change. Desktop metadata preserved from baseline: command id `none`,
  category `unknown`, risk `unknown`.
- `статус голосового ответа`: command id `voice.output_status`, category
  `voice`, risk `read_only`; voice output OFF; no audible playback; no cloud
  TTS; no audio file created. The preliminary expected id
  `voice.output.status` was incorrect; committed stable AppService/Desktop id
  is `voice.output_status`.
- `как тебя зовут`: command id `profile.assistant_name`, category `profile`,
  risk `read_only`; returned `JARVIS`; no profile mutation. The preliminary
  expected id `assistant.identity` was incorrect; committed stable
  AppService/Desktop id is `profile.assistant_name`.
- `профиль`: profile summary returned; no profile mutation; no secrets.
  Desktop metadata preserved from baseline: command id `none`, category
  `unknown`, risk `unknown`.
- `версия`: version `v0.2` returned; no state change. Desktop metadata
  preserved from baseline: command id `none`, category `unknown`, risk
  `unknown`.
- `покажи сервисы`: active service list returned; no state change. Desktop
  metadata preserved from baseline: command id `none`, category `unknown`,
  risk `unknown`.
- `статус ai`: command id `ai.status`, category `ai`, risk `read_only`;
  dry-run/offline deterministic mode; external providers disabled; no provider
  called; no network; no keys required or displayed.
- `статус secure keys`: command id `secure_keys.status`, category
  `secure_keys`, risk `read_only`; Windows DPAPI backend status returned; no
  credential values retrieved or printed; no network; no secrets.
- `привет`: category `conversation`, risk `safe_read_only`; local small-talk
  route; no command execution; no provider; no network; no microphone or TTS.
- `task095 genuinely unknown route`: category `unknown`, risk `unknown`;
  existing safe future-idea fallback preserved; no network; no secrets.

Final manual smoke remains pending only for routes changed by this
investigation: none. Baseline comparison found no TASK-095 metadata
regressions; the six Desktop `none`/`unknown` metadata results intentionally
match the committed baseline.

Final invariants:

- TASK-095 extracted matcher count in `process()`: `0`.
- Remaining `process()` matcher count: `50`.
- Extracted/legacy overlap: exact `0`, mapping `0`, prefix `0`.
- Shared-alias precedence preserved:
  - `тест распознавания` -> `speech.backend.vosk.recognition.dry_run`;
  - `путь модели vosk` -> `speech.backend.vosk.model.path.status`;
  - `выключи микрофон` -> `microphone.mode.off`.
- Remaining recognition branches are explicit legacy debt.
- AUD-008 through AUD-011 remain unchanged.

## Checklist

- [x] Implementation scoped to TASK-095.
- [x] Confirmation-flow exclusion preserved.
- [x] ActionRouter fallback exclusion preserved.
- [x] Hardware/provider/secret side effects excluded from resolver.
- [ ] Commit unchecked.
- [ ] Push unchecked.
