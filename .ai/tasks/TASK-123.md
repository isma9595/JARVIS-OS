# TASK-123 - Default Conversation Persistence

## Objective

Connect the existing TASK-115 local conversation repository to the standard
Desktop composition so a bounded safe conversation can continue across
Desktop process recreation.

## Verified Baseline

- Branch: `main`.
- Baseline commit and `origin/main`:
  `aef9d416c9c79c86419f942d50f393808d9afc83`.
- Baseline tree: `4437a4c0e0d7dd53c389ac86e6610d90b115280b`.
- TASK-122 is the published Project Truth Baseline at the baseline commit.
- Last confirmed full pytest before this task:
  `2458 passed, 2 skipped in 8.93s`.
- All required source blob IDs and the clean worktree/staging preflight matched
  the approved task specification.

## Architecture Boundary

- `ConversationSessionService` remains the only lifecycle, ordering, and
  authoritative session-state owner.
- `LocalConversationSessionRepository` remains a detached storage adapter.
- `JarvisAppService` remains the application facade.
- `DesktopShellViewModel` stores only the current cognitive session id and asks
  AppService for a resumable id.
- `CognitiveInteractionService` receives no repository and owns no persistence
  or parallel session cache.
- TASK-115 persistence is reused, not rewritten.

## Default Desktop Composition

`create_default_desktop_app_service()` constructs the standard Desktop
AppService with `LocalConversationSessionRepository`. `launch_desktop_shell()`
uses that factory. Direct `JarvisAppService()` construction without an explicit
repository remains in-memory.

The factory performs no provider, network, microphone, TTS, or execution work,
and repository construction does not create the session directory.

## Storage Layout

Persisted record schema version 1 and its JSON format are unchanged. Storage
layout version 1 is a separate concern.

- Windows default:
  `%LOCALAPPDATA%\JARVIS-OS\data\v1\cognition\sessions`
- Fallback:
  `~/.jarvis-os/data/v1/cognition/sessions`
- `JARVIS_COGNITIVE_SESSION_DIR` is an exact final-path override; no `v1`
  segment is appended to it.

The path is independent of the current working directory. The directory is
created lazily on the first record write. The former unversioned directory is
not deleted or migrated.

## Resume Semantics

`ConversationSessionService.latest_active_session_snapshot()` selects only
ACTIVE sessions under the existing session lock. It chooses the maximum
deterministic `(updated_at, created_at, session_id)` key and returns a detached
snapshot or `None` without mutation.

`JarvisAppService.resumable_conversation_session_id()` exposes only the selected
id. An explicit Desktop session id has priority. Without an ACTIVE session the
Desktop starts with `None`, and the existing first conversational-turn path
creates a new session.

## Corruption And Failure Semantics

Valid records load independently of malformed JSON and unsupported schema
records. Safe rejected record ids remain observable through
`ConversationPersistenceLoadResult`; rejected file contents are not exposed.
Repository path configuration and directory I/O failures are not hidden.

Existing write-before-publish behavior remains unchanged for create, append,
and close. Persisted turns remain bounded/redacted projections: raw user text
and secrets are not stored, and assistant response text is never executed as a
command.

## Approved File Scope

- `app/app_service.py`
- `app/desktop_shell.py`
- `cognition/persistence.py`
- `cognition/sessions.py`
- `tests/unit/test_cognitive_persistence.py`
- `tests/unit/test_cognitive_session_persistence.py`
- `tests/unit/test_cognitive_app_service_integration.py`
- `tests/unit/test_desktop_shell.py`
- `tests/unit/test_cognitive_architecture.py`
- `.ai/tasks/TASK-123.md`
- `.ai/CHECKPOINT.md`
- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/ROADMAP.md`
- `docs/architecture/COGNITIVE_ARCHITECTURE.md`

## Out Of Scope

No new persistence engine, schema migration, common user-data abstraction,
retention, chat-history UI, MemoryPolicy integration, provider conversation,
background worker, shutdown lifecycle, command-routing change, dependency, CI,
staging, commit, or push is part of this task.

## Acceptance Criteria

- Standard Desktop composition is repository-backed while direct AppService
  construction remains in-memory.
- The latest ACTIVE session resumes deterministically; CLOSED sessions do not.
- Individual corrupt or unsupported records do not block valid recovery.
- Default and override paths have the specified lazy, versioned semantics.
- Restart tests prove bounded prior context with no provider, network, or
  execution call and `response_executed_as_command=False`.
- Persisted JSON contains no raw secret-bearing user text.
- Architecture ownership and TASK-115/TASK-119B/TASK-120/TASK-121 regressions
  remain intact.
- Required validation passes. The initial failed gate is preserved, and the
  separately authorized corrective phase performs exactly one new full run.

## Validation

- Focused RED with workspace basetemp:
  `13 failed, 145 passed`; every failure was missing TASK-123 functionality.
- Focused GREEN: `158 passed in 1.29s`.
- Related regression: `327 passed in 1.91s`.
- Compileall: passed.
- Non-GUI restart smoke: passed with one session id before/after recreation,
  three bounded context turns on the second request, schema version 1,
  redacted secret text, and zero provider, network, or execution use.
- Initial full acceptance gate, exactly one run of `python -m pytest -q`:
  `1 failed, 2475 passed, 2 skipped in 11.39s`.
- Failing test:
  `tests/unit/test_user_language_preference.py::test_desktop_shell_uses_appservice_only_for_language`.
  Its local `FakeService` does not implement
  `resumable_conversation_session_id()`, so `DesktopShellViewModel`
  initialization raises `AttributeError`.
- The initial phase stopped without rerunning the full suite or changing
  production after that failed gate.
- Corrective phase: the stale local AppService test double gained the required
  side-effect-free `resumable_conversation_session_id()` method returning
  `None`; production code was unchanged.
- Corrective targeted test: `1 passed in 0.29s`.
- Corrective related tests: `145 passed in 1.05s`.
- Corrective full acceptance, exactly one separately authorized run of
  `python -m pytest -q`: `2476 passed, 2 skipped in 9.23s`.
- TASK-123 acceptance is complete.

## Next Stage

TASK-124 - Desktop Interaction Worker and Shutdown is the next product-runtime
stage. Commit and push are not part of this TASK-123 phase, and TASK-124 has not
started.
