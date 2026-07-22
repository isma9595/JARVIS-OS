# State-Changing Command Metadata

Baseline: `69969026f051142b0dcf92a58f8da0a6932764d8`.

## Contract

State-changing command metadata must be projected from existing canonical sources, not inferred from response text:

1. CommandRegistry metadata or planner capability descriptors define stable public command metadata.
2. CommandResolutionService owns deterministic resolver command id/category/safe_args for extracted routes.
3. PolicyDecisionBoundary owns confirmation and denial decisions.
4. ExecutionCoordinator and ExecutionJournal own operation id, duplicate suppression, and lifecycle status.
5. AppService coordinates and projects metadata into existing DTO fields.
6. Desktop Shell renders AppService values.

No Desktop text parsing, new public DTO fields, new registry, configuration change, dependency, provider call, microphone capture, Vosk model load, TTS playback, or credential access is part of this contract.

## Preview

Preview must not mutate state, start hardware, call providers, use network, retrieve secrets, or create completed operations. It projects command id/category/risk/confirmation/network metadata from existing registry, planner metadata, or the existing AppService memory parser where the route is known.

TASK-097 corrected AUD-008 for supported AppService memory parser routes: direct Preview recognizes memory remember, recall, and bounded forget with the same public command id/category/risk metadata as Execute while remaining non-mutating and operation-free.

## Execution

Execution of direct state-changing AppService routes must register before any domain mutation:

1. prepare the direct route and canonical command id without mutation;
2. create the request fingerprint;
3. register with `ExecutionCoordinator`;
4. return duplicate suppression or idempotency conflict before mutation;
5. execute the existing domain handler once only for a new accepted registration;
6. finalize the same operation as succeeded, awaiting confirmation, denied, or failed;
7. project that operation identity into the existing result DTO.

Journal metadata is redacted through `safe_journal_metadata`. Direct memory metadata uses structural previews such as `memory.remember [REDACTED]` and `memory.forget [REDACTED]`; raw memory keys and values are not stored in operation metadata. Free-form journal metadata values for direct-route booleans are meaningful strings (`yes` / `no`), not accidental empty strings.

The corrected direct AppService rows are:

- `profile.language.set`: changed execution is `local_write`, `executed=True`, operation status `succeeded`.
- `profile.language.reset`: changed execution uses the stable reset id and the same local-write operation behavior.
- `memory.remember`: execution is `local_write`, `executed=True`, operation status `succeeded`.
- `memory.forget`: execution is `local_write`, `executed=True`, operation status `succeeded`.

Read-only status/recall routes do not get artificial state-changing operation ids. TASK-098 corrected AUD-009 with a recall-only Russian memory-key alias path; that alias lookup remains read-only and does not affect remember, bounded forget, forget-all, write-time normalization, storage serialization, or operation registration. Direct no-op requests on the coordinated routes, such as setting the active language, forgetting a missing key, or remembering an identical existing value, still register before handler execution so duplicate/conflict detection cannot be bypassed by a later `changed=False` result. The projected result may remain `read_only` / `executed=False` while the operation lifecycle records the accepted request.

Forget-all remains excluded from this direct-route registration path because it already has its own confirmation and pending-operation flow.

TASK-099 corrected AUD-011 in planner parsing only: the exact normalized Russian natural forget-all planner phrase `забудь все что ты обо мне помнишь` now maps to the existing destructive `memory.forget_all` capability. Preview and plan creation remain non-mutating and operation-free; actual plan execution still pauses at the existing confirmation boundary before any deletion. Ordinary bounded forget phrases remain `memory.forget`.

For completed execution results, `requires_confirmation` must describe the actual confirmation contract, not a preview default. If `operation_status == "succeeded"` and the route did not enter awaiting confirmation or require confirmation before execution, AppService projects `requires_confirmation=False`. This covers safe completed legacy routes such as `статус микрофона` and harmless unknown/future-idea fallback text while preserving their existing command id/category/risk projection (`none` / `unknown` in Desktop output).

## Confirmation

Confirmation handling remains the existing policy/coordinator flow. TASK-096 does not send approval phrases to destructive commands. Destructive and secret-sensitive commands remain preview/fake-test-only unless separately approved.

Actual confirmation-required previews and awaiting-confirmation execution results continue to project `requires_confirmation=True`. Desktop Shell renders the AppService field directly; it does not infer confirmation from operation status, risk text, or response text.

## Planner Policy

Planner capability descriptors and policy requests must agree for state-changing local routes. `language.set`, `memory.remember`, and `memory.forget` use `local_write` risk and `file_write` capability in their policy requests, matching the existing descriptors.

## Desktop Projection

Desktop Shell execution output renders AppService metadata values, including:

- command id;
- category;
- risk;
- requires confirmation;
- operation id;
- operation status;
- duplicate suppression;
- network may be used.

The shell remains a rendering layer.

## Exclusions

Unchanged:

- AUD-016 technical microphone error presentation.
- Existing internal/public id mappings characterized by TASK-095.

Resolved after TASK-096:

- AUD-013 local TTS result metadata inconsistency was corrected by TASK-100 at the AppService execution projection boundary. Preview remains side-effect free and may stay unknown for these legacy local TTS inputs, but completed local TTS Execute results must not reuse unknown Preview confirmation metadata.

## Rollback

Rollback is limited to reverting the TASK-096 changes in AppService metadata coordination, Desktop execution rendering, focused tests, and this documentation. No data migration or configuration rollback is required.
