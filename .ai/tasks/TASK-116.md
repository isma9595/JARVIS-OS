# TASK-116 - Conversation Context & Response Composition

## Objective

Introduce bounded, safe conversation-context projection and a narrow,
non-executing response-composition boundary for cognitive conversation turns.

## Scope

- Extend cognitive contracts with the minimum immutable DTOs for context
  projection and response composition.
- Add `cognition/context.py` with a stateless
  `ConversationContextProjector`.
- Add `cognition/response_composer.py` with a narrow `ResponseComposer`
  protocol and compatibility implementation.
- Add a detached `ConversationSessionService.context_source(...)` read API.
- Update `CognitiveInteractionService` to append the user turn, project
  bounded context, compose once, append the assistant turn, and return context
  diagnostics.
- Update `JarvisAppService` composition wiring without changing the public
  conversation-session API.
- Add focused contract, context, composer, interaction, AppService
  integration, and architecture regression tests.

## Non-Goals

- No `IntentInterpreter`, semantic intent classification, `ReferenceResolver`,
  clarification migration, `UserGoal`, `GoalService`, `ProposedPlan`,
  `CognitivePlanner`, `MemoryPolicy`, cognitive memory, `KnowledgeService`,
  provider-assisted response generation, network access, embeddings, vector
  databases, semantic summarization, workflow/execution changes, background
  automation, proactive suggestions, Desktop UI changes, CLI migration,
  streaming, or provider-specific token budgeting.

## Architectural Ownership

- `ConversationSessionService` remains the sole owner of session lifecycle,
  authoritative turn state, ordering, sequence allocation, and persistence
  coordination.
- `ConversationContextProjector` owns no durable state and reads only detached
  snapshots/turn tuples supplied by the session service.
- `ResponseComposer` owns no durable state and does not execute actions.
- `CognitiveInteractionService` remains orchestration-only and owns no session
  cache, context cache, repository, response history dictionary, or durable
  state.
- `JarvisAppService` remains the public facade and composition root.
- Cognition context and response-composition modules import no Desktop,
  concrete providers, platform adapters, `WorkflowRunner`,
  `ExecutionCoordinator`, `CommandProcessor`, or `LocalMemoryManager`.

## Context Contracts

New immutable JSON-safe DTOs:

- `ConversationContextTurn`;
- `ConversationContextSnapshot`;
- `ResponseCompositionInput`;
- `ResponseCompositionResult`.

The DTOs contain no arbitrary metadata dictionaries, execution payloads,
provider-specific fields, repository handles, mutable records, intent, goals,
plans, memory candidates, knowledge results, or clarification contracts.

## Context Bounds

Default provider-neutral bounds:

- `DEFAULT_CONTEXT_MAX_TURNS = 12`;
- `DEFAULT_CONTEXT_MAX_TURN_CHARS = 160`;
- `DEFAULT_CONTEXT_MAX_TOTAL_CHARS = 800`.

The projector keeps the newest turns when limits are exceeded, returns them in
chronological order, bounds each projected turn, bounds total projected text
characters, and reports deterministic omitted counts plus truncation reason.
Empty sessions are valid and closed sessions remain inspectable.

## Relevance Rules

TASK-116 relevance is intentionally simple: recent chronological turns only.
There is no semantic selection, intent-based selection, memory retrieval,
knowledge retrieval, embeddings, provider token budgeting, or provider/network
use.

## Redaction And Safety Behavior

Live in-memory turns are projected through deterministic local safety:

- whitespace normalization;
- existing `safe_cognitive_text(...)` redaction;
- replacement of obvious secret-like content with
  `[redacted sensitive content]`;
- per-turn and total character bounds;
- no command payloads, credentials, approval secrets, provider prompts,
  execution handles, workflow internals, or arbitrary metadata.

Known limitation: this does not claim comprehensive secret detection or
semantic summarization.

## Response-Composition Boundary

`ResponseComposer` is a protocol with `compose(input)`. The compatibility
implementation delegates to an AppService-owned callable that wraps the
existing side-effect-free `SafeConversationalLoop` behavior.

The composer receives bounded context and records
`context_turn_count_used`. It does not execute commands, call workflows,
providers, network, Desktop, memory, platform adapters, persistence, or
`CognitiveInteractionService`.

## Interaction Ordering

`CognitiveInteractionService.handle_turn(...)` now performs:

1. Resolve or create the session.
2. Append the current user turn through `ConversationSessionService`.
3. Obtain detached session context source from `ConversationSessionService`.
4. Project bounded context through `ConversationContextProjector`.
5. Invoke `ResponseComposer` exactly once.
6. Append the assistant turn through `ConversationSessionService`.
7. Return `AssistantResponse`, current session snapshot, context snapshot, and
   composition diagnostics.

## Failure Semantics

- Unknown sessions and closed sessions continue to raise typed session errors.
- Context projection failure occurs after the accepted user turn; no assistant
  turn is fabricated and the exception propagates.
- Response composition failure records the existing deterministic safe
  assistant error response and preserves valid sequencing.
- Assistant append or persistence failure propagates; no unrecorded successful
  assistant response is returned.
- Broad exceptions are not swallowed outside the documented composition
  fallback.

## AppService Integration

`JarvisAppService` constructs `ConversationContextProjector` and
`CompatibilityResponseComposer` through composition. Optional TASK-115 session
repository injection is preserved. The public conversation-session methods are
unchanged, and command preview/execution, workflows, confirmation,
clarification, memory, voice, activity, provider status, Desktop, and CLI
behavior are not routed through TASK-116 cognition.

## Test Evidence

- `python -m pytest -q tests/unit/test_cognitive_contracts.py tests/unit/test_cognitive_context.py tests/unit/test_cognitive_response_composer.py tests/unit/test_cognitive_interaction_service.py tests/unit/test_cognitive_app_service_integration.py tests/unit/test_cognitive_architecture.py tests/unit/test_cognitive_persistence.py tests/unit/test_cognitive_session_persistence.py`
  - Result: 66 passed.
- `python -m pytest -q tests/unit/test_app_service.py tests/unit/test_app_contracts.py tests/unit/test_conversational_loop.py`
  - Result: 116 passed.
- `python -m pytest -q tests/unit/test_cognitive_contracts.py tests/unit/test_cognitive_context.py tests/unit/test_cognitive_response_composer.py tests/unit/test_cognitive_interaction_service.py tests/unit/test_cognitive_app_service_integration.py tests/unit/test_cognitive_architecture.py tests/unit/test_cognitive_persistence.py tests/unit/test_cognitive_session_persistence.py tests/unit/test_app_service.py tests/unit/test_app_contracts.py tests/unit/test_conversational_loop.py`
  - Result: 182 passed after contract numeric validation was tightened.
- First final `python -m pytest -q`
  - Result: 1864 passed, 2 skipped.
- Corrective validation note: final diff review found coercive integer
  validation in TASK-116 context contracts and projector configuration. The
  validation accepted bools and coercible numeric/string values through
  `int(...)`. Production validation was corrected to require plain `int`
  values, reject bools, floats, strings, `Decimal`, `Fraction`, `None`, and
  malformed objects, then apply positive/nonnegative range checks. This
  required a second full-suite run; no claim is made that the full suite ran
  exactly once overall.
- `python -m pytest -q tests/unit/test_cognitive_contracts.py tests/unit/test_cognitive_context.py`
  - Result: 115 passed.
- `python -m pytest -q tests/unit/test_cognitive_contracts.py tests/unit/test_cognitive_context.py tests/unit/test_cognitive_response_composer.py tests/unit/test_cognitive_interaction_service.py tests/unit/test_cognitive_app_service_integration.py tests/unit/test_cognitive_architecture.py tests/unit/test_cognitive_persistence.py tests/unit/test_cognitive_session_persistence.py tests/unit/test_app_service.py tests/unit/test_app_contracts.py tests/unit/test_conversational_loop.py`
  - Result: 278 passed.
- Second final `python -m pytest -q`
  - Result: 1960 passed, 2 skipped.
- `git diff --check`
  - Result: passed with Git line-ending conversion warnings for changed files,
    but no whitespace errors.

## Acceptance Criteria

- Bounded immutable conversation context is available.
- Context preserves chronological order and deterministic truncation.
- Context projection is safe and provider-neutral.
- `ResponseComposer` is a narrow non-executing boundary.
- `CognitiveInteractionService` remains orchestration-only.
- `ConversationSessionService` remains the sole durable session-state owner.
- No context or response cache becomes a second source of truth.
- Existing command/workflow behavior remains unchanged.
- No provider, network, execution, workflow, memory, or Desktop dependency
  enters context or response composition.
- Focused tests pass.
- Full-suite validation passes after any production correction.
- `git diff --check` passes.
- Architecture boundaries remain healthy.

## Known Limitations

- Relevance is recent-turn only.
- Redaction is deterministic and obvious-pattern based, not comprehensive
  secret detection.
- Summaries are bounded projections, not semantic summaries.
- There is no provider or network use.
- There is no workflow/execution persistence or recovery.
- There are no Desktop, CLI, memory, knowledge, intent, clarification, goal,
  or planning changes.
