# TASK-118 - Reference Resolution

## Objective

Introduce a narrow, deterministic, provider-neutral reference-resolution
adapter for simple conversational references in cognitive turns.

## Scope

- Add immutable reference contracts for detected references, candidates,
  resolved references, resolution input, and resolution results.
- Add `cognition/reference_resolver.py` with a `ReferenceResolver` protocol and
  `RuleBasedReferenceResolver` implementation.
- Integrate reference resolution into `CognitiveInteractionService` after
  intent interpretation and before response composition.
- Pass reference-resolution results into `ResponseCompositionInput` and record
  deterministic reference counts in compatibility composition diagnostics.
- Wire the resolver through `JarvisAppService` as the composition root.
- Add focused contract, resolver, response-composer, interaction-service,
  AppService integration, and architecture regression tests.

## Non-Goals

No comprehensive linguistic coreference, entity extraction, named-entity
linking, people resolution, gender or animacy inference, semantic similarity,
embeddings, provider-assisted resolution, memory lookup, knowledge lookup,
filesystem or application-object resolution, command argument reconstruction,
workflow selection, execution routing, confirmation authorization,
clarification coordination, question generation, goals, planning, Desktop UI,
CLI migration, voice changes, proactive behavior, background automation, or
streaming.

## Ownership

- `ConversationSessionService` remains the sole owner of session lifecycle,
  authoritative turns, ordering, sequence allocation, and persistence.
- `ConversationContextProjector` remains stateless and supplies only bounded
  detached context.
- `RuleBasedIntentInterpreter` remains stateless and descriptive only.
- `RuleBasedReferenceResolver` is stateless and owns no reference cache,
  history, session state, persistence, memory, or execution state.
- `ResponseComposer` remains stateless and non-executing.
- `CognitiveInteractionService` remains orchestration-only.
- `JarvisAppService` remains the public facade and composition root.

## Contracts

New immutable JSON-safe DTOs and enums:

- `ReferenceKind`;
- `ReferenceResolutionStatus`;
- `ReferenceCandidate`;
- `DetectedReference`;
- `ResolvedReference`;
- `ReferenceResolutionInput`;
- `ReferenceResolutionResult`.

The contracts contain no arbitrary metadata dictionaries, resolved command
arguments, workflow identifiers, filesystem paths inferred from context,
entity graphs, memory keys, knowledge queries, plans, goals, approval tokens,
provider prompts, repository handles, or mutable internal records.

All new integer fields use strict plain-`int` validation through the existing
cognitive contract helpers. Bools, floats, strings, `Decimal`, `Fraction`,
`None`, and coercible objects are rejected before range checks.

## Supported Reference Forms

The initial phrase set is deliberately small.

English:

- `this`, `that`, `it`, `this one`, `that one`;
- `the previous message`, `the last message`;
- `your previous response`;
- `my previous request`;
- `the previous question`;
- `the last result`;
- explicit quoted excerpts.

Russian:

- `это`, `этот`, `эта`, `тот`, `та`, `то`, `оно`, `он`, `она`;
- `это сообщение`;
- `предыдущее сообщение`, `последнее сообщение`;
- `твой предыдущий ответ`;
- `мой предыдущий запрос`;
- `предыдущий вопрос`;
- `последний результат`.

This is fixed phrase matching, not broad multilingual coreference support.

## Deterministic Rule Precedence

1. Empty, unusable, fully redacted, or cancellation-intent text produces no
   references.
2. A quoted excerpt resolves only when it uniquely matches one bounded prior
   turn.
3. Explicit role-and-recency phrases select the nearest matching prior
   assistant response or user request.
4. Previous/last message phrases select the immediately preceding eligible
   bounded turn.
5. Previous question/result phrases select the nearest observable matching
   bounded turn.
6. Neutral demonstratives or pronouns resolve only when exactly one eligible
   salient prior candidate exists.
7. Multiple plausible candidates produce `ambiguous`.
8. Detected references with no eligible candidate produce `unresolved`.
9. No detected reference produces an empty result equivalent to
   not-applicable.

The resolver never chooses solely because a target is newest when multiple
equally plausible targets exist.

## Candidate Eligibility

Candidates use only bounded context turn properties:

- role;
- sequence;
- safe text;
- chronological position;
- visible question punctuation;
- visible result-like markers;
- explicit wording requesting user or assistant content.

The resolver does not use embeddings, semantic similarity, hidden entities,
inferred goals, provider token budgets, memory, workflow state, command
history outside bounded context, filesystem state, or application state.

## Ambiguity Policy

Ambiguity is returned when duplicate quoted matches, multiple neutral-pronoun
targets, or truncated context prevent a unique conservative answer. Unresolved
is returned when a reference is detected but no eligible target exists. The
resolver does not ask clarification questions; that remains later work.

## Context And Intent Use

Only TASK-116 bounded detached context is supplied. The interpreted intent from
TASK-117 is used as weak descriptive context: cancellation avoids target
selection, while action-like text such as "do it" may be treated as containing
a reference without authorizing execution.

## Safety And Redaction

Resolution normalizes whitespace, applies `safe_cognitive_text(...)`, uses
fixed phrase matching, bounds detected surface text to 80 characters, and
bounds candidate excerpts to 160 characters. Redacted candidate text is not
treated as a resolvable target. This does not claim comprehensive secret
detection.

## Interaction Ordering

`CognitiveInteractionService.handle_turn(...)` now performs:

1. Resolve or create the session.
2. Append the current user turn.
3. Project bounded context.
4. Interpret intent exactly once.
5. Resolve references exactly once.
6. Compose the response exactly once with context, intent, and references.
7. Append the assistant turn.
8. Return only a successfully recorded response plus safe diagnostics.

## Response-Composition Integration

`ResponseCompositionInput` now carries `reference_resolution`. The
compatibility composer records reference count, resolved count, ambiguous
count, and unresolved count in deterministic composition provenance. It does
not turn resolved candidates into command arguments or clarification prompts.

## Failure Semantics

- Unknown and closed sessions preserve typed session behavior.
- Context projection failure preserves the accepted user turn and skips
  interpreter, resolver, composer, and assistant append.
- Intent interpretation failure preserves TASK-117 behavior and skips resolver
  and composer.
- Typed reference-resolution failure records a deterministic safe assistant
  error turn and skips composer.
- Response composition failure preserves TASK-116/TASK-117 safe-error behavior.
- Assistant append or persistence failure propagates; no unrecorded successful
  assistant response is returned.

## AppService Composition

`JarvisAppService` constructs `RuleBasedReferenceResolver` by default and
accepts an injected resolver for tests. Persistence, context projection,
intent interpretation, and response composition injection remain preserved.
Preview, execute, workflow, memory, provider, voice, confirmation,
clarification, activity, Desktop, and CLI behavior are unchanged.

## Tests

- `python -m pytest -q tests/unit/test_cognitive_contracts.py tests/unit/test_cognitive_reference_resolver.py tests/unit/test_cognitive_response_composer.py tests/unit/test_cognitive_interaction_service.py tests/unit/test_cognitive_app_service_integration.py tests/unit/test_cognitive_architecture.py`
  - First run: 1 failed, 169 passed. The failed assertion expected a redacted
    prior turn to remain selectable; the implementation correctly treated
    redacted candidate text as unavailable. The test was corrected and a
    separate bounded-safe-candidate assertion was added.
  - Second run: 171 passed.
- `python -m pytest -q tests/unit/test_cognitive_contracts.py tests/unit/test_cognitive_context.py tests/unit/test_cognitive_intent_interpreter.py tests/unit/test_cognitive_reference_resolver.py tests/unit/test_cognitive_response_composer.py tests/unit/test_cognitive_interaction_service.py tests/unit/test_cognitive_app_service_integration.py tests/unit/test_cognitive_architecture.py tests/unit/test_cognitive_persistence.py tests/unit/test_cognitive_session_persistence.py tests/unit/test_app_service.py tests/unit/test_app_contracts.py tests/unit/test_conversational_loop.py`
  - Result: 358 passed.
- `python -m pytest -q`
  - Result: 2040 passed, 2 skipped.
- `git diff --check`
  - Result: passed with Git line-ending conversion warnings for changed files,
    but no whitespace errors.

## Acceptance Criteria

- Immutable provider-neutral reference contracts exist.
- A stateless deterministic `ReferenceResolver` boundary exists.
- Simple references are detected and resolved conservatively.
- Ambiguous and unresolved states are explicit.
- Bounded context is the only resolution source.
- Interpreted intent is used only as weak descriptive context.
- Resolver runs exactly once after intent and before composition.
- Reference result is observably supplied to composer.
- No reference cache or second state store exists.
- No resolved reference authorizes execution.
- No command or workflow arguments are reconstructed.
- `ConversationSessionService` remains the sole state owner.
- `CognitiveInteractionService` remains orchestration-only.
- Existing execution/workflow APIs remain unchanged.
- No provider, network, memory, knowledge, execution, workflow, Desktop, NLP,
  embedding, or vector dependency is added.
- Focused tests pass.
- Exactly one final `python -m pytest -q` passes.
- `git diff --check` passes.

## Limitations

- No comprehensive linguistic coreference.
- No entity extraction or people resolution.
- No semantic similarity, embeddings, NLP framework, or provider assistance.
- No memory, knowledge, filesystem, workflow, or application-object lookup.
- No command argument reconstruction or execution routing.
- No clarification coordination or clarification-question generation.
- No comprehensive multilingual understanding.
- No comprehensive secret-detection claim.
