# TASK-119 - Clarification Coordinator

## Objective

Add a stateless, deterministic clarification coordination boundary to the
cognitive turn pipeline. Clarification is conversational guidance only; it is
not execution approval, rejection, routing, planning, or persisted state.

## Delivered Scope

- Added immutable provider-neutral clarification DTOs in `cognition/contracts.py`.
- Added `ClarificationCoordinator` protocol and
  `RuleBasedClarificationCoordinator` in
  `cognition/clarification_coordinator.py`.
- Wired coordination into `CognitiveInteractionService` after reference
  resolution and before response composition.
- Extended `ResponseCompositionInput` so `ResponseComposer` receives the typed
  clarification request.
- Updated `CompatibilityResponseComposer` to emit the safe clarification
  question for `needed` and a generic prompt for `unavailable`.
- Wired `JarvisAppService` as the composition root for the coordinator.

## Non-Goals

TASK-119 does not add pending clarification persistence, a clarification state
machine, multi-turn slot filling, provider-generated questions, semantic entity
resolution, memory or knowledge lookup, command reconstruction, workflow
selection, execution routing, action approval, planning, retries, background
jobs, Desktop UI, CLI migration, voice changes, streaming, embeddings, vector
databases, or network dependencies.

## Ownership

- `ReferenceResolver` owns reference detection, candidate discovery, and
  resolved/unresolved/ambiguous classification.
- `ClarificationCoordinator` owns whether typed ambiguity should become one
  user-facing clarification request.
- `ResponseComposer` owns final assistant text.
- `ConversationSessionService` remains the sole owner of session and turn
  state.
- `JarvisAppService` remains the public facade and composition root.

## Contracts And Enums

New contracts are frozen, compact, JSON-safe, provider-neutral, and free of
mutable defaults:

- `ClarificationStatus`: `not_needed`, `needed`, `unavailable`.
- `ClarificationReason`: `ambiguous_reference`, `unresolved_reference`,
  `missing_subject`, `unclear_confirmation`, `unclear_rejection`,
  `insufficient_context`, `conflicting_signals`, `unsupported_ambiguity`,
  `none`.
- `ClarificationOption`: safe label, optional detached turn sequence or id,
  safe excerpt, source reason, ordinal.
- `ClarificationRequest`: status, reason, optional safe question, bounded
  options, related reference count, context count, coordinator identity/version,
  and rule id.
- `ClarificationCoordinationInput`: current user turn, bounded context,
  interpreted intent, and reference-resolution result.

All new integer fields validate with `type(value) is int`; bool, floats,
strings, `Decimal`, `Fraction`, `None`, negative values, and zero for positive
fields are rejected.

## Deterministic Precedence

1. Empty, unusable, safely redacted text, or explicit cancellation returns
   `not_needed`.
2. Ambiguous reference with two or more safe distinguishable candidates returns
   `needed`.
3. Ambiguous reference with fewer than two distinguishable options after
   redaction returns `unavailable`.
4. Unresolved reference in `action_request` or `information_request` returns
   `needed`.
5. Unresolved reference in ordinary conversation returns `not_needed`.
6. Confirmation or rejection with an observable prior assistant question returns
   `not_needed`.
7. Confirmation or rejection without an observable target returns `needed`.
8. Clarification response with an observable prior assistant question returns
   `not_needed`.
9. Clarification response without a recoverable prior question returns
   `unavailable`.
10. Otherwise return `not_needed`.

## Needed Criteria

Clarification is needed only when deterministic bounded evidence shows an
ambiguous reference with safe options, an unresolved actionable or information
reference, or a short confirmation/rejection without an observable target.

## Not-Needed Criteria

Clarification is not needed when no ambiguity is observable, references are
absent or uniquely resolved, intent is ordinary conversation with no actionable
unresolved reference, cancellation is explicit, confirmation/rejection has a
visible conversational target, a clarification answer follows an observable
assistant question, or the coordinator lacks deterministic evidence.

## Unavailable Semantics

`unavailable` means guessing would be unsafe but the bounded inputs do not
support a specific safe question or distinguishable options. The composer emits
a generic safe prompt:

- English: `Could you clarify what you mean?`
- Russian: `Уточните, пожалуйста, что именно вы имеете в виду.`

## Safe Template Generation

Questions are template-based and deterministic. Narrow Cyrillic character
presence selects Russian templates; otherwise English templates are used. At
most one question is produced and internal enum names, rule ids, sequences, and
diagnostics are not shown in user-facing text.

## Option Construction

Options are derived only from bounded `ReferenceCandidate` DTOs. The
coordinator preserves resolver ordering, skips redacted or empty excerpts,
deduplicates equivalent role/excerpt pairs, limits to three options, and uses
safe role labels plus safe excerpts. It never reads session history to recover
raw text and never invents executable payloads.

## Relationship To Intent

Intent is a weak descriptive signal. It can indicate actionable unresolved
references, confirmation, rejection, cancellation, and clarification responses.
It does not authorize execution, deny execution, select workflows, reconstruct
arguments, infer plan steps, or change security state.

## Relationship To Reference Resolution

The coordinator does not rerun detection, override resolver status, convert an
ambiguous reference to resolved, inspect additional history, reconstruct a
target, or persist pending clarification state.

## Stateless Continuity Model

No pending clarification store, hidden correlation id, retry counter, expiry,
or awaiting-response flag was added. The clarification question is appended as
an ordinary assistant turn; later user replies are interpreted through the
normal bounded-context pipeline.

## Orchestration Ordering

Successful cognitive turn order is:

1. Resolve or create session.
2. Append current user turn.
3. Project bounded context.
4. Interpret intent once.
5. Resolve references once.
6. Coordinate clarification once.
7. Compose response once with clarification included.
8. Append assistant turn.
9. Return recorded response and safe diagnostics.

## Failure Semantics

Projection failure preserves the accepted user turn and skips later stages.
Intent and reference-resolution failures preserve existing safe assistant error
behavior. Clarification-coordination failure records
`Conversation clarification coordination failed safely.`, skips composition, and
does not expose raw user text, options, or candidates. Composition and append
failures retain existing behavior.

## AppService Composition

`JarvisAppService` constructs or accepts an injected coordinator and passes it
to `CognitiveInteractionService`. Existing preview, execute, confirmation,
workflow, memory, provider, voice, activity, and Desktop-related APIs are not
changed.

## Safety And Redaction

Clarification DTOs use existing cognitive text redaction, bounded text lengths,
strict typed fields, and no arbitrary metadata dictionary. They contain no
workflow name, command arguments, provider prompt, memory identifier, plan,
goal, execution route, callback, or authorization state.

## Tests

Added focused tests for clarification contracts, strict integer validation,
coordinator decisions, deterministic ordering, bounded/redacted options,
English/Russian templates, statelessness, response composition, interaction
ordering/failures, AppService injection, and cognition import boundaries.

## Limitations

The rule-based coordinator intentionally handles only narrow deterministic
ambiguity. It does not perform broad missing-slot extraction, comprehensive
dialogue management, semantic ambiguity detection, entity lookup, or provider
reasoning.

## Acceptance Criteria

Satisfied: immutable clarification contracts exist; a stateless deterministic
coordinator boundary exists; decisions use only bounded context, intent, and
reference DTOs; ambiguous references can produce safe options; unresolved
actionable references ask a safe question without reconstructing commands;
unavailable ambiguity is explicit; the coordinator runs once between resolver
and composer; clarification questions are recorded as normal assistant turns;
no pending clarification store or execution approval path was introduced; and
focused tests pass.
