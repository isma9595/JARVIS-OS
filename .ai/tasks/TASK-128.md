# TASK-128 - Chat-First Desktop UX v1

## Status

Implementation, audit remediation, and post-audit acceptance are complete in
the unstaged worktree. Staging, commit, and push are not part of this
implementation phase.

## Objective

Make the standard Desktop experience visibly chat-first while keeping routing,
conversation lifecycle, persistence, provider use, execution, and worker
lifecycle behind their existing application boundaries.

## Verified Baseline

- Published dependency: TASK-127 - Real AI Conversation Vertical Slice.
- Baseline commit: `435f66041149226840481efbb7728ceb4b7324a1`.
- Baseline tree: `3e2022167d5de714128a60eb62d33c35e0b31f0a`.
- Branch and `origin/main` both pointed to the baseline commit.
- Worktree and staging were clean and `git diff --check` passed.
- Published TASK-127 acceptance:
  `2696 passed, 4 skipped in 14.34s`.

## Architecture Boundary

- `JarvisAppService` remains the application facade and owns the safe chat
  projection.
- `ConversationSessionService` remains the only conversation lifecycle and
  ordered-turn owner.
- `DesktopShellViewModel` remains a presentation projection and retains only
  the current cognitive session id plus ephemeral retry presentation input.
- `DesktopInteractionWorker` remains the sole Desktop busy, cancellation, and
  shutdown lifecycle owner.
- Desktop imports no cognition, provider, persistence, execution, or workflow
  internals and never interprets provider output as a command.
- Direct `JarvisAppService()` construction remains in-memory and
  compatibility-based unless dependencies are explicitly injected.

## AppService Chat Contract

- `AppDesktopChatStatus` is an immutable, path-free application DTO.
- It projects session availability/state, bounded turn count, resumability,
  response state/source, explicit retry availability/reason, and safe
  persistence state/code.
- `AppDesktopTurnResult` carries this projection beside the natural response,
  diagnostics, session id, and optional execution contract.
- Desktop does not inspect repositories, provider objects, persistence health
  internals, or formatted diagnostic text to reconstruct chat state.

## Chat-First Projection

- The primary input is labelled `Сообщение`, the primary action is
  `Отправить`, and the assistant response is placed before secondary technical
  panels.
- A compact safe status line reports AppService-projected session, response,
  retry, and persistence state without paths, secrets, tracebacks, raw provider
  errors, or persisted records.
- Known commands and control turns retain the existing AppService execution
  route; ordinary eligible questions retain the TASK-127 Groq-or-local-fallback
  composition path.

## Retry Semantics

- Retry is explicit and available only for eligible conversational results.
- It resubmits the same bounded user input through the same AppService Desktop
  facade, current cognitive session id, and serialized Desktop worker.
- There is no automatic retry, retry queue, provider bypass, duplicate
  execution, or retry for command/control, clarification, privacy-blocked, or
  failed turns.
- Retry input is ephemeral Desktop presentation state and is not a second
  conversation history or persistence store.
- Gate-level semantic privacy refusal is projected as local/private and never
  enables retry; AppService reuses the configured gate's deterministic privacy
  decision rather than matching human-readable refusal text.

## Cancellation And Worker Boundary

- Typed send, one-shot voice, workflow resume, and chat retry use the existing
  single lazy serialized non-daemon worker.
- Busy submission remains bounded and duplicate work is rejected atomically.
- The existing general cancel action stays cooperative and does not claim
  rollback or force termination of a started opaque AppService call.
- Tk widgets and `DesktopShellState` are applied only on the main thread after
  one completion is consumed.

## Persistence Status

- Standard Desktop composition remains repository-backed and automatically
  resumes the latest ACTIVE conversation session from TASK-123.
- AppService projects only a bounded persistence state/code; repository paths,
  record contents, rejected ids, raw exceptions, and secrets are excluded.
- Direct AppService construction reports the in-memory boundary without
  creating a repository.
- An unknown externally supplied session id is not echoed into the path-free
  status DTO.

## Approved File Scope

1. `app/app_contracts.py`
2. `app/app_service.py`
3. `app/desktop_shell.py`
4. `app/__init__.py`
5. `tests/unit/test_app_contracts.py`
6. `tests/unit/test_cognitive_app_service_integration.py`
7. `tests/unit/test_desktop_shell.py`
8. `tests/unit/test_cognitive_architecture.py`
9. `.ai/tasks/TASK-128.md`
10. `.ai/CHECKPOINT.md`
11. `README.md`
12. `docs/ARCHITECTURE.md`
13. `docs/ROADMAP.md`
14. `docs/DESKTOP_APP_SHELL.md`
15. `docs/architecture/COGNITIVE_ARCHITECTURE.md`

## Out Of Scope

- broad Desktop redesign, new windows, chat selector, transcript editor, or
  parallel Desktop history/cache;
- new provider, model selector, provider settings, automatic retries, provider
  consensus, or provider-controlled tools;
- new AppService execution, workflow, voice, document, memory, or persistence
  ownership;
- changes to command routing, confirmation, clarification, execution policy,
  persistence schema, Desktop worker lifecycle, or shutdown behavior;
- MemoryPolicy runtime integration, document intake, TASK-129, or later work.

## Acceptance Criteria

- AppService returns one immutable path-free chat status projection.
- Standard Desktop presents chat input, assistant response, safe status, and
  explicit eligible retry without bypassing AppService.
- Retry reuses the same session and one worker, and duplicate submission cannot
  invoke AppService twice.
- Privacy-blocked and command/control turns are not retryable.
- Repository-backed persistence is visible only as safe state/code and ACTIVE
  session resume remains unchanged.
- Provider response is presentation-only and never enters command execution.
- Direct AppService construction remains in-memory and compatibility-based.
- Focused, related, compile, smoke, and one full repository acceptance pass.
- Only the fifteen approved files differ; staging remains empty and no commit
  or push is performed.

## Validation

- Preflight: passed.
- Focused RED: `2 errors in 1.92s`; both expected collection errors were caused
  by the not-yet-implemented `AppDesktopChatStatus` contract.
- Initial focused implementation run: `2 failed, 175 passed`; both failures
  were TASK-128 test-placement/label expectations and were corrected before
  the final focused gate.
- Focused GREEN: `179 passed in 2.98s`.
- Related regression: `406 passed in 5.97s`.
- Compileall for the four changed production modules: exit code `0`.
- Safe fake-provider non-GUI smoke: passed. It exercised a normal chat turn and
  explicit retry through one Desktop worker, rejected a duplicate submission,
  made two fake-provider calls, and created no execution journal entry.
- Pre-audit full repository acceptance:
  `2704 passed, 4 skipped in 27.16s`.
- Final read-only audit: failed with two MEDIUM findings (gate-level privacy
  refusal retry classification and unknown session-id publication) plus one
  LOW finding (stale visible chat status after Clear).
- Remediation RED: `3 failed, 179 passed in 4.88s`; all three failures were the
  new audit regressions.
- First remediation GREEN candidate: `1 failed, 181 passed in 3.88s`; the only
  failure was a stale FakeAppService idle-status contract, corrected without a
  production change.
- Remediation focused GREEN: `182 passed in 5.44s`.
- Remediation related regression: `427 passed in 8.35s`.
- Remediation compileall for both changed production modules: exit code `0`.
- Remediation non-GUI smoke: passed; semantic privacy refusal made no provider,
  network, or execution call, an unknown path-shaped id was not published, and
  Clear projected idle/no-retry state.
- Single post-audit full repository acceptance:
  `2707 passed, 4 skipped in 14.35s`.
- Real network/provider, GUI, microphone, TTS, document input, staging, commit,
  and push were not used.

## Next Stage

TASK-129 - Document Intake v1. TASK-129 is not started by this task. Staging,
commit, and push require separate user verification and explicit approval.
