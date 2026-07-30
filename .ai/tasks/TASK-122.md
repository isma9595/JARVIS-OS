# TASK-122 - Project Truth Baseline

## Objective

Align the central project documentation with the verified runtime state after
TASK-121 and replace the unimplemented future TASK-122 through TASK-139
sequence with the current product roadmap.

This is a documentation-only task. It adds no capability and changes no
runtime, test, dependency, configuration, provider, execution, workflow,
Desktop, cognition, or memory behavior.

## Verified Baseline

- Branch: `main`.
- TASK-120 is completed and published at
  `db21ed45ba35d9a97db42bd27a6dd60de33b2658`.
- TASK-121 is completed and published at
  `3336e4cac2595ba09313c7bde51692f0bd2c667f`.
- Verified baseline tree:
  `9b63aeb2200f0d429cac8abed8a45d1e163dd020`.
- Last confirmed full TASK-121 suite:
  `2458 passed, 2 skipped in 8.76s`.
- Desktop typed input and one-shot voice use one AppService-owned cognitive
  conversation facade.
- `ConversationSessionRepository` and
  `LocalConversationSessionRepository` exist, and explicitly injected
  repository-backed sessions can be reopened.
- The standard `launch_desktop_shell()` composition creates
  `JarvisAppService()` without a repository, and the standard
  `ConversationSessionService` therefore uses `repository=None`.
- Default Desktop conversation persistence across launches is not wired.
- `CompatibilityResponseComposer` is the default response composer. The
  ordinary Desktop cognitive conversation path remains compatibility-based,
  not a complete provider-backed AI conversation.
- Generated assistant response text is presentation output and is never
  automatically executed as a command.
- TASK-121 `MemoryPolicy` is exported, deterministic, stateless, and owns no
  storage. It is not integrated into AppService, Desktop, or existing memory
  command routes.

## Documentation Truth Boundary

Documentation distinguishes implemented behavior from opt-in composition,
contracts that are not runtime-integrated, and planned work. Future tasks are
not represented as implemented.

Completed historical TASK records are not rewritten. In particular, the
`Next Stages` section in `TASK-121.md` remains the historical plan recorded
when that task was created. The normative current numbering is defined by
`docs/ROADMAP.md`.

## Approved File Scope

- `.ai/tasks/TASK-122.md`
- `.ai/CHECKPOINT.md`
- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/ROADMAP.md`
- `docs/architecture/COGNITIVE_ARCHITECTURE.md`

## Required Documentation Changes

- Replace the obsolete checkpoint with the TASK-121 verified code baseline,
  TASK-122 documentation alignment, and TASK-123 next runtime task.
- Update README capability, architecture, and limitation claims through
  TASK-121.
- Record precise default, injected, contract-only, and planned boundaries in
  the architecture documentation.
- Mark TASK-120 and TASK-121 completed and replace only the unimplemented
  future roadmap sequence.
- Point the cognitive architecture summary to the normative roadmap without
  changing its ownership or safety boundaries.

## Superseded Planning

The former future TASK-122 through TASK-139 numbering was design planning and
was not implemented. TASK-122 supersedes that unimplemented numbering before
implementation. It does not revoke or rewrite completed TASK-113 through
TASK-121 history.

The new roadmap prioritizes a truthful durable core, daily user value, memory
and knowledge, and long-operation reliability before later expansion. Goal,
planning, and complex multi-provider ideas remain deferred design work rather
than cancelled work.

## Out Of Scope

- Runtime code, tests, scripts, configuration, dependencies, and scaffolding
- AppService, Desktop, cognition, memory storage, command routing, execution,
  workflow, provider, voice, TTS, or filesystem behavior
- A new full architecture or security audit
- TASK-123 implementation
- Staging, commit, push, fetch, pull, checkout, reset, merge, rebase, or amend

## Acceptance Criteria

- Exactly the six approved documentation files are changed, with this file as
  the only new file.
- Central documentation states the verified TASK-121 runtime truth and does
  not claim default Desktop session persistence.
- Central documentation states that the current ordinary cognitive response
  remains compatibility-based.
- Central documentation states that `MemoryPolicy` is implemented but not
  runtime-integrated.
- TASK-120 and TASK-121 are marked completed in the roadmap.
- The old unimplemented TASK-122 through TASK-139 sequence is explicitly
  superseded and replaced without duplicate future task IDs.
- The next runtime stage is TASK-123 - Default Conversation Persistence.
- Safety, confirmation, cancellation, idempotency, AppService DTO, privacy,
  network, DPAPI, filesystem adapter, provider adapter, and test boundaries are
  preserved.
- Documentation checks and exactly one full pytest run pass.
- No files are staged and no commit or push occurs.

## Validation

- Preflight: passed against the verified TASK-121 baseline.
- Documentation scope and content checks: passed; exactly the six approved
  files are changed, this is the only new file, required boundaries are
  explicit, the obsolete TASK-122 heading is absent, and current future task
  headings are unique.
- `git diff --check`: passed; Git emitted only line-ending conversion warnings
  for existing tracked files.
- Full suite, exactly one run of `python -m pytest -q`:
  `2458 passed, 2 skipped in 8.93s`.
- Staging, final status, and changed-file checks: passed; staging is empty and
  the worktree contains only the expected TASK-122 documentation diff.

## Next Stage

TASK-123 - Default Conversation Persistence is the next runtime task. Commit
and push are not part of this TASK-122 phase, and TASK-123 must not begin
automatically.
