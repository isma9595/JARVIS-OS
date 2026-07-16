# TASK-082 Execution Journal, Cancellation & Idempotency

## Scope

TASK-082 adds one application-level execution-control boundary for AppService.
It does not add a second CommandProcessor, a second policy system, a workflow
engine, persistent storage, process killing, or provider execution.

## Operation Lifecycle

Execution requests follow this application-level lifecycle:

request -> operation registration -> intent resolution -> policy decision ->
clarification or confirmation when required -> execution at most once ->
terminal journal state.

Statuses are typed:

- `created`
- `awaiting_clarification`
- `awaiting_confirmation`
- `running`
- `succeeded`
- `failed`
- `cancelled`
- `denied`
- `duplicate_suppressed`

## Journal Fields

Each journal snapshot contains:

- operation id
- idempotency key
- source
- command id or action id
- safe request fingerprint
- status
- policy decision metadata
- created and updated timestamps
- cancellable flag
- duplicate suppressed flag
- safe result summary
- safe error code
- redacted metadata

Snapshots are immutable dataclasses and serialize through `to_dict()`.

## Redaction Rules

The journal stores metadata only. It does not store API keys, authorization
headers, credential values, raw audio, provider clients, full provider
responses, full document contents, arbitrary file contents, raw exceptions, GUI
objects, or microphone objects.

Known secret-like text is replaced with `[REDACTED]`. Long summaries are
bounded.

## Cancellation Semantics

Cancellation is cooperative and single-operation scoped. It sets a cancellation
token and moves a non-terminal operation to `cancelled`.

Cancellation while awaiting clarification clears clarification state.
Cancellation while awaiting confirmation clears confirmation state.
Cancellation after terminal completion is a safe no-op.

No forceful thread termination, process killing, or unsafe interruption is
introduced. Current short synchronous commands are not force-interrupted.

## Idempotency Rules

Each non-preview execution has an operation id, idempotency key, and safe
request fingerprint.

The same idempotency key with the same fingerprint returns the existing running
or terminal operation and marks the duplicate suppressed. It does not execute
again.

The same idempotency key with a different fingerprint is denied as an
idempotency conflict and executes nothing.

A new idempotency key represents a new intentional operation.

Preview does not create an operation and does not consume an idempotency key.

## Clarification And Confirmation Correlation

Clarification and confirmation are separate states. A clarification answer
continues the same operation id. A confirmation applies only to the pending
operation and its stored fingerprint, is single-use, and re-enters the policy
protected execution path.

Cancellation never counts as confirmation.

## AppService Integration

Desktop Shell typed execution, one-shot voice text execution, resolved intent
execution, provider request commands, and direct side-effect-capable
CommandProcessor delegation all pass through AppService operation registration
when invoked through AppService.

The coordinator does not execute commands, call providers, route actions, read
credentials, inspect audio, or make policy decisions.

## Bounded In-Memory Limitation

The journal is local, in-memory, deterministic, thread-safe, and bounded. It is
not a database and is not crash-recoverable. Persistent workflow history is
deferred until workflow contracts stabilize.

## Future Workflow Compatibility

The operation id, idempotency key, safe fingerprint, status, cancellation token,
and metadata snapshot are designed so future workflows can retry, correlate,
cancel, and inspect safe state without changing CommandProcessor semantics.

## Manual Smoke Steps

Run:

```powershell
python -m pytest tests\unit\test_execution_journal.py tests\unit\test_execution_coordinator.py tests\integration\test_task_082_execution_control.py
python -m pytest
python -W error::DeprecationWarning -m pytest
powershell -ExecutionPolicy Bypass -File scripts\health_check.ps1
git diff --check
git status --short
```

Manual behavior checks:

- `app contracts status` creates a succeeded operation.
- Repeating the same explicit idempotency key suppresses duplicate execution.
- Reusing the same key with different text is denied.
- `покажи статус` then `системы` keeps one operation id.
- `удали файл safe-test.txt` then `отмена` cancels and executes nothing.
- `удали System32` is denied and routes no dangerous action.
