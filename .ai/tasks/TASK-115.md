# TASK-115 - Conversation Session Persistence

## Objective

Add a safe persistence boundary for cognitive conversation sessions so
approved session metadata and bounded/redacted turn representations can survive
process restart.

## Task-Numbering Rationale

TASK-114 was completed as the documentation-only roadmap-alignment task in
commit `cc4cafdd468ed2177e2bed4ccfabaeb6f8cfeac5`. The production persistence
implementation is therefore recorded as TASK-115.

`docs/ROADMAP.md` required a small numbering correction: TASK-114 remains the
completed alignment task, TASK-115 is Conversation Session Persistence,
Conversation Context & Response Composition moves to TASK-116, and downstream
roadmap entries shift consistently to avoid duplicate task numbers.

## Scope

- Add `cognition/persistence.py` as a narrow persistence boundary.
- Add versioned persisted conversation session and turn-summary DTOs.
- Add a local one-file-per-session JSON repository.
- Extend `ConversationSessionService` with optional repository injection,
  restart loading, persistence diagnostics, and durable create/append/close
  writes.
- Add optional AppService composition injection for a session repository.
- Add focused unit, integration-style, and architecture regression tests.
- Make minimal roadmap and roadmap-summary documentation corrections.

## Non-Goals

- No Conversation Context & Response Composition implementation.
- No `IntentInterpreter`, `ReferenceResolver`, or clarification migration.
- No `UserGoal`, `GoalService`, `CognitivePlanner`, or plan policy work.
- No `MemoryPolicy`, cognitive memory, or knowledge service.
- No provider-assisted summarization, provider calls, or network access.
- No command, workflow, execution, memory, voice, activity, Desktop, or CLI
  behavior changes.
- No execution/workflow persistence.
- No background automation, proactive suggestions, streaming, database
  storage, or schema migration beyond recognizing and rejecting unsupported
  versions.

## Ownership Model

- `ConversationSessionService` remains the sole cognitive session lifecycle,
  ordering, and authoritative in-memory state owner.
- Persistence adapters store and load detached records only.
- `CognitiveInteractionService` remains orchestration-only and owns no
  repository, session cache, or durable state.
- `JarvisAppService` remains the public application facade and only wires the
  optional repository through composition.
- Cognition persistence imports no Desktop, provider, workflow, execution,
  memory, platform adapter, or AppService concrete implementation owners.

## Persistence Boundary

`ConversationSessionRepository` is a protocol with:

- `load_records()`;
- `save_record(record)`;
- `delete_record(session_id)`;
- `close()`.

The boundary does not generate turn sequence numbers, decide lifecycle state,
append turns, maintain a mutable session cache, call interaction orchestration,
or call execution/workflow services.

## Persisted Schema

Schema version: `1`.

`PersistedConversationSessionRecord` fields:

- `schema_version`;
- `session_id`;
- `status`;
- `created_at`;
- `updated_at`;
- `turn_count`;
- `last_turn_id`;
- `turns`;
- `revision`.

`PersistedConversationTurnSummary` fields:

- `turn_id`;
- `sequence`;
- `role`;
- `source_classification`;
- `created_at`;
- `summary_text`;
- `content_classification`;
- `redaction_reason`.

Records are frozen, explicitly versioned, JSON-safe, deterministic through
sorted JSON serialization, detached from service-owned mutable records, and
validated before loading into service state. There is no arbitrary metadata
dictionary.

## Sensitive-Text Policy

Raw turn text is not persisted as a `text` field. Persistence stores only a
bounded deterministic `summary_text` projection.

The projection:

- normalizes whitespace;
- applies the existing `safe_cognitive_text(...)` redaction helper;
- treats existing `[REDACTED]` markers as sensitive;
- replaces obvious secret-like content with `[redacted sensitive content]`;
- bounds non-sensitive summaries to `MAX_PERSISTED_TURN_SUMMARY_LENGTH`;
- stores source as a normalized source classification;
- stores no command payloads, credentials, tokens, provider prompts,
  arbitrary metadata, or execution handles.

Known limitation: this is deterministic local redaction for obvious
secret-like patterns only. It does not claim comprehensive secret detection or
semantic summarization.

## Consistency Model

For repository-backed sessions, `ConversationSessionService` uses a
write-before-publish model under the session lock:

1. Build a candidate internal record from current authoritative state plus the
   requested mutation.
2. Serialize and persist a detached record through the repository.
3. Publish the mutation into the authoritative in-memory session map only
   after persistence succeeds.

This avoids reporting a durable mutation that was not stored. Pure in-memory
service construction remains supported when no repository is supplied.

## Restart-Loading Semantics

On repository-backed initialization, `ConversationSessionService` loads
recoverable records into its in-memory state. Valid sessions recover with
stable ids, status, turn count, last turn id, ordered turn summaries, and
correct next sequence behavior. Closed sessions remain closed.

Recovered turn text is the persisted safe summary, not the original raw text.

## Corruption Strategy

`LocalConversationSessionRepository` uses one JSON file per session and partial
safe recovery:

- valid records are loaded;
- malformed records are rejected independently;
- unsupported schema records are rejected independently;
- corrupt or unsupported record ids are exposed through
  `ConversationPersistenceLoadResult`;
- corrupt contents are not included in diagnostics;
- invalid data never becomes authoritative session state.

## Failure Semantics

- Load failures use typed cognition persistence errors.
- Write failures raise `ConversationPersistenceWriteError`.
- Persistence failures are not silently swallowed.
- A failed create does not publish a session.
- A failed turn append does not publish the unstored turn.
- A failed close does not publish the closed state.

## Storage Location And Configuration

`LocalConversationSessionRepository` stores one UTF-8 JSON file per session.
Writes create parent directories, write to a sibling `.tmp` file, and atomically
replace the authoritative file with `os.replace(...)`.

Default storage is outside source-controlled paths:

- `JARVIS_COGNITIVE_SESSION_DIR` when set;
- otherwise `%LOCALAPPDATA%/JARVIS-OS/cognition/sessions` on Windows-style
  environments;
- otherwise `~/.jarvis-os/cognition/sessions`.

Tests inject temporary directories.

## Test Evidence

- `python -m pytest -q tests/unit/test_cognitive_persistence.py tests/unit/test_cognitive_session_persistence.py tests/unit/test_cognitive_contracts.py tests/unit/test_cognitive_interaction_service.py tests/unit/test_cognitive_app_service_integration.py tests/unit/test_cognitive_architecture.py`
  - Result: 42 passed.
- `python -m pytest -q tests/unit/test_cognitive_persistence.py tests/unit/test_cognitive_session_persistence.py tests/unit/test_cognitive_contracts.py tests/unit/test_cognitive_interaction_service.py tests/unit/test_cognitive_app_service_integration.py tests/unit/test_cognitive_architecture.py tests/unit/test_app_service.py tests/unit/test_app_contracts.py tests/unit/test_conversational_loop.py`
  - Result: 158 passed.
- Final `python -m pytest -q`
  - Result: 1840 passed, 2 skipped.
  - Process note: the full suite was run once, then persisted schema
    validation was tightened to reject unexpected fields and overlong
    summaries, requiring a second full-suite run. Both full `python -m pytest
    -q` runs passed with `1840 passed, 2 skipped`. No third full-suite run was
    performed during finalization.
- `git diff --check` completed with exit code 0. Git reported Windows
  line-ending conversion warnings for changed files, but no whitespace errors.

## Acceptance Criteria

- Sessions safely survive restart through repository-backed service
  construction.
- Raw sensitive turn text is not persisted by default.
- Persisted data is bounded, redacted, versioned, and validated.
- `ConversationSessionService` remains the sole lifecycle and ordering owner.
- Persistence remains a replaceable storage adapter.
- Invalid data cannot become authoritative session state.
- Corruption behavior is observable and deterministic.
- Persistence failures do not silently lose acknowledged mutations.
- Existing command and workflow behavior remains unchanged.
- No provider, network, execution, memory, Desktop, or platform dependency
  enters cognition persistence.
- Focused tests pass.
- Full-suite validation passed. The full suite ran twice because schema
  validation was tightened after the first run, and both full runs passed.
- `git diff --check` passes.
- Repository architecture boundaries remain healthy.

## Known Limitations

- Persisted summaries are conservative deterministic projections, not semantic
  summaries.
- Unsupported schema versions are rejected; no migration is implemented.
- Conversation persistence does not recover execution, workflow, goal,
  memory, provider, or Desktop state.
- TASK-115 did not add semantic summarization, comprehensive secret detection,
  provider/network use, Desktop changes, or workflow/execution persistence.
