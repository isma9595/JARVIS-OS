# TASK-120 - Desktop Cognitive Conversation Vertical Slice & Response Presentation Boundary

## Objective

Connect ordinary typed and Desktop one-shot voice input to the existing
stateful cognitive conversation pipeline while preserving command/control
safety and separating the natural JARVIS response from technical diagnostics.

## Scope

- Add one AppService-owned Desktop-turn facade for typed and recognized voice
  text.
- Keep Desktop presentation-only; Desktop does not classify input as
  conversation, command, clarification, confirmation, cancellation, or
  unsupported.
- Route ordinary conversation through the existing
  `CognitiveInteractionService` only after AppService classifies the turn as
  conversational.
- Keep known commands and control turns on the existing safe AppService
  execution route.
- Preserve one cognitive session id across sequential typed and Desktop
  one-shot voice turns.
- Project a clean assistant response, separate diagnostics, cognitive session
  id, and optional execution metadata through AppService contracts.
- Reuse TASK-115 session persistence when an existing repository-backed
  session id is reopened.
- Add focused unit, integration, architecture, and smoke regressions.
- Align the cognitive roadmap and architecture documentation with the
  implementation through TASK-120.

## Non-Goals

- No MemoryPolicy or cognitive memory integration.
- No CLI migration.
- No legacy `VoiceInputManager` migration or redesign.
- No new execution permissions, command aliases, provider behavior, network
  behavior, background work, always-on microphone behavior, or automatic
  downloads/installs.
- No new session, history, or memory subsystem.
- No large Desktop visual redesign.
- No command-response execution or provider-output execution.
- No broad changes to existing command behavior.

## Application Boundary

`JarvisAppService` owns the unified Desktop-turn routing decision. The facade:

1. preserves pending control and known-command routing;
2. uses only side-effect-free AppService interpretation to decide whether a
   non-command turn is conversational;
3. invokes the full cognitive conversation turn exactly once only for a
   conversational route;
4. invokes the existing command execution route for commands and control
   turns;
5. returns a UI-safe application projection.

`DesktopShellViewModel` submits text and a current cognitive session id. It
does not import cognition internals or duplicate routing rules.

## Session Ownership

- `ConversationSessionService` remains the only cognitive session lifecycle,
  ordering, turn-state, and persistence owner.
- Desktop stores only the current session id as presentation state.
- No Desktop turn history, context cache, or parallel memory is introduced.
- Reopening a known repository-backed session uses the TASK-115 load path.
- Tests use deterministic injected ids without network or provider calls.

## Presentation Boundary

The Desktop-turn application result separates:

- clean user-facing response text;
- structured technical diagnostics;
- cognitive session id;
- execution metadata only when the turn used the execution route.

The primary Desktop output never reconstructs these fields by parsing formatted
text and does not include the legacy Desktop execution report, operation id,
category/risk, network flags, or internal SafeConversationalLoop diagnostics.

`CompatibilityResponseComposer` receives the clean conversational answer, not
`SafeConversationalLoop.result_text_ru(...)`.

## Safety Invariants

- Cancellation is evaluated before confirmation.
- Confirmation without a target executes nothing.
- Confirmation during pending clarification does not select an option.
- One operation id is preserved for a clarification lifecycle.
- Cancelling pending clarification moves that operation to `cancelled`.
- Safe vague action references such as `сделай это` request clarification.
- Risky vague actions such as `удали это` remain unsupported and execute
  nothing.
- Desktop text does not fall through to legacy voice confirmation.
- No literal whole-phrase routing or special `if text == ...` behavior is
  introduced.
- Assistant response text is never submitted to command execution.

## Legacy Follow-Up

The direct `run.py -> CommandProcessor.process()` CLI path and the legacy
`VoiceInputManager -> CommandProcessor.process()` path remain explicitly out of
scope. They require a separate approved migration task after TASK-120.

## Acceptance Criteria

- Greeting through Desktop uses a cognitive session, returns clean response
  text, creates no execution operation, and does not call CommandProcessor.
- Two sequential conversational turns reuse one session id; the second turn
  receives bounded prior context; composition runs once per turn.
- Desktop one-shot voice uses the same AppService facade and session id.
- A known repository-backed session can be reopened and its safe context is
  available through TASK-115 persistence.
- Known commands still create and execute operations through AppService.
- TASK-119B clarification, cancellation, confirmation, unsupported, operation
  lifecycle, and legacy-voice-blocking behavior remains unchanged.
- `удали это` performs no action.
- Natural response and diagnostics occupy separate result/state projections.
- Primary Desktop output contains no technical execution report.
- Assistant response is never executed as a command.
- Focused and related regression tests pass.
- One final full `python -m pytest -q` passes.
- `git diff --check` passes.

## Validation

- Focused cognitive AppService integration: `19 passed`.
- Focused Desktop Shell: `92 passed`.
- Combined AppService/cognition/Desktop contracts: `227 passed`.
- Related command-routing, cognition, workflow, voice, and smoke regression:
  `552 passed`.
- Full cognition/AppService/Desktop/architecture regression: `528 passed`.
- Post-routing-edge focused Desktop/TASK-119B regression: `94 passed`.
- Post-routing-edge TASK-078 through TASK-084 integration regression:
  `84 passed`.
- Final Desktop/cognitive/one-shot voice focused regression: `157 passed`.
- Final full suite: `2143 passed, 2 skipped`.
- `git diff --check`: passed; only repository line-ending conversion warnings
  were emitted.
- Manual Desktop smoke: passed.
  - `статус app service`: operation
    `op-75cae7861cd542709f0a2da09b43d273`,
    command `app_service.status`, status `succeeded`, executed.
  - `сделай это`: new operation
    `op-d54e31dca31244daa580789f54ee970e`, category `clarification`, status
    `awaiting_clarification`, requires clarification, not executed; execution
    history selected the new operation.
  - `да`: preserved operation
    `op-d54e31dca31244daa580789f54ee970e`, remained
    `awaiting_clarification`, not executed.
  - `отмена`: preserved the same operation, moved it to `cancelled`, not
    executed.
  - `удали это`: new operation
    `op-445a5c3073664919add763de69a866d9`, category `unsupported`, no command,
    not executed.
  - Following `да`: new operation
    `op-41d9bc774b0640c6855d0600c0e2e4c4`, intent
    `confirmation_response`, category `clarification`, status
    `awaiting_clarification`, no command, not executed; execution history
    selected the new operation and no previous operation executed.
- Publication: manual Desktop verification succeeded and the user explicitly
  approved one TASK-120 commit and push to `origin/main`.
