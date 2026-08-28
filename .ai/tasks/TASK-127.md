# TASK-127 - Real AI Conversation Vertical Slice

## Status

Implementation and acceptance are complete in the unstaged worktree. Staging,
commit, and push are not part of this implementation phase.

## Objective

Replace the standard Desktop compatibility-only answer path with one useful
Groq-backed conversation path while retaining deterministic local fallback and
all existing command, privacy, persistence, execution, and lifecycle safety
boundaries.

## Verified Baseline

- Published dependency: TASK-126 - Reproducible Environment and CI.
- Baseline commit: `95702dbb772d903446c6a9c8660fa3a12b5c3762`.
- Baseline tree: `75610bd1b8b939021bd05d62722f683c61eee4d5`.
- Branch and `origin/main` both pointed to the baseline commit.
- The worktree and staging area were clean.
- Published TASK-126 acceptance:
  `2683 passed, 4 skipped in 40.35s`.
- The user separately verified one explicit real Groq request with
  `llama-3.1-8b-instant`; no credential value is recorded here.

## Architecture Boundary

- `JarvisAppService` remains the Desktop application facade and composition
  root.
- `CognitiveInteractionService` still performs one provider-neutral response
  composition pass per conversational turn.
- `ConversationSessionService` remains the sole lifecycle and ordered-turn
  owner.
- `ProviderBackedResponseComposer` is an app-level adapter. It owns no session,
  provider runtime, execution, workflow, memory, persistence, Desktop state, or
  widgets.
- Cognition modules do not import provider modules. Desktop does not import
  provider or cognition internals.
- Direct `JarvisAppService()` construction remains in-memory and uses the
  deterministic compatibility composer unless an explicit composer/gate is
  injected.
- Legacy `run.py` remains on its documented `CommandProcessor` path. TASK-127
  does not perform the later CLI/Desktop semantic-router consolidation.

## Primary Provider Composition

- The standard Desktop factory injects the existing `GroqRequestGate` into one
  app-owned composer.
- Groq model and cost limits continue to come from the existing Groq guard; the
  default model remains `llama-3.1-8b-instant`.
- Only ordinary conversation, question, and information-request intents are
  provider-eligible.
- Clarification and ineligible/action-oriented intents stay deterministic.
- Each eligible turn makes at most one gated provider attempt and creates no
  retry queue, consensus call, or provider session state.
- Missing credentials, privacy refusal, guard refusal, provider error, empty
  result, or unexpected provider exception degrades to the existing local
  compatibility answer.

## Context And Privacy

- Provider input is built only from the existing bounded
  `ConversationContextSnapshot` projection, not from raw persistence records,
  memory, profile, files, logs, screen content, or microphone audio.
- The composer payload before the existing language-policy prefix is capped at
  900 characters and keeps the most recent bounded safe context.
- A current turn already classified as redacted sensitive content never reaches
  the provider gate. Other private/sensitive markers remain subject to the
  existing external-provider privacy gate.
- Provider response text is bounded, secret-redacted, treated as untrusted
  presentation text, and appended through the existing session write path.
- API keys are resolved through the existing secure-runtime/env boundary. Real
  key values are never placed in prompts, diagnostics, task records, or tests.

## Failure And Diagnostics

- Primary success is reported only as `primary_provider:groq` in structured
  composition diagnostics.
- Fallback records only bounded constant provenance; provider exception text,
  paths, secrets, tracebacks, raw prompts, and raw provider metadata are not
  exposed.
- Conversation diagnostics conservatively report that network may be used when
  the primary-provider path was attempted.
- Natural response text remains separate from diagnostics.
- Provider response text is never submitted to `CommandProcessor`, policy,
  execution, or workflow APIs.

## Approved File Scope

1. `app/provider_backed_response_composer.py`
2. `app/app_service.py`
3. `tests/unit/test_provider_backed_response_composer.py`
4. `tests/unit/test_cognitive_app_service_integration.py`
5. `tests/unit/test_cognitive_architecture.py`
6. `.ai/tasks/TASK-127.md`
7. `.ai/CHECKPOINT.md`
8. `README.md`
9. `docs/ARCHITECTURE.md`
10. `docs/ROADMAP.md`
11. `docs/architecture/COGNITIVE_ARCHITECTURE.md`

## Out Of Scope

- OpenAI activation or any new provider adapter;
- automatic key creation, storage, download, or installation;
- real provider/network calls in automated validation;
- provider settings UI, model selector, retries, consensus, or multi-provider
  orchestration;
- autonomous tools, provider-controlled commands, execution, workflows, or
  domain state;
- memory/profile/file/document/screen/audio context packaging;
- changes to command routing, confirmation, cancellation, execution policy,
  persistence schemas, voice behavior, or Desktop worker lifecycle;
- legacy CLI semantic-router consolidation;
- TASK-128 or later work.

## Acceptance Criteria

- Standard Desktop composition connects Groq through the existing privacy,
  cost/model, credential, and language gates.
- Ordinary provider-eligible turns receive one useful response through a fake
  provider in automated tests; no real network is required.
- Known commands and control flows remain on the existing AppService execution
  route and do not call the provider composer.
- Missing/blocked/failed provider attempts return deterministic local fallback.
- Bounded prior context is supplied without raw secrets or other automatic user
  data packaging.
- Assistant response text is applied once as presentation output and is never
  executed as a command.
- Direct AppService construction remains in-memory and compatibility-based.
- The full repository suite passes once after implementation and documentation.
- Only the eleven approved files differ from the published baseline.
- Staging remains empty; commit and push are not performed.

## Validation

- Preflight: passed.
- Focused RED: two expected collection errors because
  `app.provider_backed_response_composer` did not yet exist.
- Focused GREEN: `56 passed in 1.13s`.
- Related regression: `437 passed in 2.69s`.
- Compileall for both changed production modules: exit code `0`.
- Fake-provider Desktop vertical slice: covered in both focused and related
  runs; exactly one provider call, no `CommandProcessor` call, no execution
  journal entry, and `response_executed_as_command=False`.
- Real provider/network, GUI, microphone, and TTS were not used by automated
  validation.
- Single full repository acceptance: `2696 passed, 4 skipped in 14.34s`.

## Next Stage

TASK-128 - Chat-First Desktop UX v1. TASK-128 is not started by this task.
Staging, commit, and push require separate user verification and explicit
approval.
