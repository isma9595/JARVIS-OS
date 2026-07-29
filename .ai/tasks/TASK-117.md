# TASK-117 - IntentInterpreter Adapter

## Objective

Introduce a narrow, deterministic, provider-neutral intent interpretation
adapter for cognitive conversation turns.

## Scope

- Add immutable intent contracts for broad descriptive intent categories,
  confidence, bounded evidence, interpretation input, and interpreted results.
- Add `cognition/intent_interpreter.py` with an `IntentInterpreter` protocol and
  `RuleBasedIntentInterpreter` implementation.
- Integrate interpretation into `CognitiveInteractionService` after context
  projection and before response composition.
- Pass interpreted intent into `ResponseCompositionInput` and make
  compatibility composition record the observed category in deterministic
  diagnostics.
- Wire the interpreter through `JarvisAppService` as the composition root.
- Add focused contract, interpreter, response-composer, interaction-service,
  AppService integration, and architecture regression tests.

## Non-Goals

No reference resolution, entity extraction, pronoun resolution,
ClarificationCoordinator migration, goals, planning, execution routing,
workflow selection, command authorization, memory reads or writes, knowledge
retrieval, providers, network access, embeddings, vector databases, semantic
classifiers, ML/NLP libraries, Desktop UI, CLI migration, proactive behavior,
background automation, streaming, or provider-assisted intent detection.

## Architectural Ownership

- `ConversationSessionService` remains the sole owner of session lifecycle,
  authoritative turn state, ordering, sequence allocation, and persistence
  coordination.
- `ConversationContextProjector` remains stateless and owns no context cache.
- `RuleBasedIntentInterpreter` is stateless and owns no intent cache, history,
  repository, session state, memory state, or execution state.
- `ResponseComposer` and `CompatibilityResponseComposer` remain stateless and
  non-executing.
- `CognitiveInteractionService` remains orchestration-only and injects the
  projector, interpreter, and composer.
- `JarvisAppService` remains the public facade and composition root.

## Contracts

New immutable JSON-safe DTOs and enums:

- `IntentCategory`;
- `IntentConfidence`;
- `IntentEvidence`;
- `InterpretedIntent`;
- `IntentInterpretationInput`.

Contracts contain no arbitrary metadata dictionaries, command payloads,
workflow identifiers, execution arguments, approval tokens, provider prompts,
repository handles, mutable internal records, goals, plans, memory candidates,
knowledge queries, or resolved entities.

## Categories

The initial closed category set is descriptive only:

- `conversation`;
- `question`;
- `information_request`;
- `action_request`;
- `clarification_response`;
- `cancellation`;
- `confirmation`;
- `rejection`;
- `unknown`.

`action_request` does not authorize or trigger command execution.

## Rule Precedence

The rule-based interpreter uses deterministic local rules:

1. Empty or fully redacted safe text becomes `unknown`.
2. Explicit cancellation phrases become `cancellation`.
3. Short replies after an observable prior assistant question become
   `clarification_response`.
4. Explicit confirmation phrases become `confirmation`.
5. Explicit rejection phrases become `rejection`.
6. Direct interrogative forms become `question`.
7. Information-request prefixes become `information_request`.
8. Action-request prefixes become `action_request`.
9. Everything else becomes `conversation`.

The phrase set is intentionally small and includes representative English and
Russian phrases only. It is not a semantic classifier.

## Context Usage

The bounded context from TASK-116 is used only to inspect chronological prior
turns for the latest assistant question before the current user turn. This can
classify a short reply such as "yes" as a clarification response when the
context provides observable evidence. The interpreter does not resolve
references, reconstruct commands, infer goals, retrieve memory, or select
workflows.

## Safety And Redaction

Intent interpretation uses the existing `safe_cognitive_text(...)` boundary,
whitespace normalization, bounded safe user text, and bounded evidence
excerpts. Obvious token/secret-like values covered by the existing cognitive
redaction pattern are not exposed in intent DTO serialization.

Known limitation: this is not comprehensive secret detection and does not
perform semantic summarization or multilingual understanding beyond the small
documented phrase set.

## Response-Composition Integration

`ResponseCompositionInput` now carries `interpreted_intent`. The compatibility
composer continues to delegate response text to the existing AppService-owned
safe conversational behavior, and records the observed intent category in
`composition_source` diagnostics. It does not execute commands, call workflows,
call providers, inspect Desktop state, persist data, or mutate sessions.

## Interaction Ordering

`CognitiveInteractionService.handle_turn(...)` performs:

1. Resolve or create the session.
2. Append the current user turn through `ConversationSessionService`.
3. Obtain detached context source and project bounded context.
4. Interpret intent exactly once.
5. Pass context and interpreted intent into response composition.
6. Append the assistant turn through `ConversationSessionService`.
7. Return only a response that was successfully recorded, plus session,
   context, composition, and intent diagnostics.

## Failure Semantics

- Unknown and closed sessions continue to raise typed session errors.
- Context projection failure occurs after the accepted user turn; no intent,
  composer, or assistant turn is recorded and the exception propagates.
- Typed intent interpretation failure records a deterministic safe assistant
  error turn, skips response composition, and does not expose raw text.
- Response composition failure preserves TASK-116 behavior by recording a
  deterministic safe assistant error response.
- Assistant append or persistence failure propagates; no unrecorded successful
  assistant response is returned.
- Broad untyped interpreter failures are not swallowed.

## AppService Composition

`JarvisAppService` constructs `RuleBasedIntentInterpreter` by default and
accepts an injected interpreter for tests. Optional session persistence,
context projection, and response composition injection remain unchanged.
Command preview/execution, workflows, confirmation, clarification, memory,
voice, activity, provider status, Desktop, and CLI behavior are not routed
through intent interpretation.

## Test Evidence

- `python -m pytest -q tests/unit/test_cognitive_contracts.py tests/unit/test_cognitive_intent_interpreter.py tests/unit/test_cognitive_response_composer.py tests/unit/test_cognitive_interaction_service.py tests/unit/test_cognitive_app_service_integration.py tests/unit/test_cognitive_architecture.py`
  - Result: 135 passed.
- `python -m pytest -q tests/unit/test_cognitive_contracts.py tests/unit/test_cognitive_context.py tests/unit/test_cognitive_intent_interpreter.py tests/unit/test_cognitive_response_composer.py tests/unit/test_cognitive_interaction_service.py tests/unit/test_cognitive_app_service_integration.py tests/unit/test_cognitive_architecture.py tests/unit/test_cognitive_persistence.py tests/unit/test_cognitive_session_persistence.py tests/unit/test_app_service.py tests/unit/test_app_contracts.py tests/unit/test_conversational_loop.py`
  - Result: 307 passed.
- `python -m pytest -q`
  - Result: 1989 passed, 2 skipped.

## Acceptance Criteria

- Immutable provider-neutral interpreted-intent contracts exist.
- A stateless deterministic `IntentInterpreter` boundary exists.
- Broad categories are classified conservatively.
- Bounded context is used only for narrow conversational disambiguation.
- Interpretation occurs exactly once before response composition.
- Interpreted intent is supplied observably to response composition.
- Intent does not authorize or trigger execution.
- No intent cache or second cognitive state store exists.
- `ConversationSessionService` remains the sole session owner.
- `CognitiveInteractionService` remains orchestration-only.
- Existing AppService execution/workflow behavior remains unchanged.
- No provider, network, memory, knowledge, execution, workflow, or Desktop
  dependency is added.
- Focused tests, one final full suite, and `git diff --check` pass.

## Limitations

- No intent interpretation beyond the documented deterministic rules.
- No semantic relevance or semantic context selection.
- No reference resolution or entity extraction.
- No provider-assisted generation or provider-assisted intent detection.
- No memory or knowledge retrieval.
- No comprehensive secret-detection claim.
