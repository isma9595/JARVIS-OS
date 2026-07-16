# TASK-084 — Workflow Runner Extraction

## Scope

TASK-084 extracts the reusable lifecycle from the local document review workflow
into a small in-memory linear workflow runner.

The runner supports only an ordered list of declared steps. It is not a planner,
DAG engine, scheduler, persistence layer, rollback engine, plugin marketplace,
or dynamic workflow generator.

## Model

Each workflow has:

- `workflow_id`;
- one existing `operation_id` from `ExecutionCoordinator`;
- typed local workflow state owned by the consumer;
- ordered `WorkflowExecutableStep` entries;
- safe serializable snapshots.

Step statuses are `pending`, `running`, `awaiting_confirmation`, `succeeded`,
`failed`, `cancelled`, and `skipped`.

Workflow statuses are `created`, `running`, `awaiting_confirmation`,
`succeeded`, `failed`, `cancelled`, and `denied`.

## Pause And Resume

A confirmation-required step is paused before its side effect. Resume continues
the same in-memory run using the same `operation_id`. Terminal workflows are not
re-entered into execution, so duplicate confirmation cannot replay a completed
write.

## Cancellation

Cancellation is cooperative through the existing cancellation token. Cancelling
a workflow marks the existing operation cancelled and prevents remaining steps.
Terminal cancellation is a safe no-op.

## Progress

Progress is deterministic from completed declared steps. It never falls outside
0-100. Awaiting confirmation does not mark the pending side-effect step
completed. Successful workflows end at 100.

## Failure Handling

Step exceptions are caught at the workflow boundary and converted to safe
Russian messages and safe error codes. Raw exceptions, credentials, complete
document text, provider clients, GUI objects, file handles, and audio are never
placed in runner snapshots.

## Policy And Execution Integration

The runner uses the existing TASK-081 `PolicyDecisionBoundary` and TASK-082
`ExecutionCoordinator` / `ExecutionJournal`. It does not create a second policy
system or journal. Idempotency remains owned by AppService and the coordinator.

## Document Review Migration

The TASK-083 local `.txt` document workflow is the first consumer. Document
validation, UTF-8 decoding, issue detection, revision generation, output naming,
atomic write, hashing, and source-preservation checks remain in
`workflows/document_review.py`.

The document workflow declares these runner steps:

- `validate_source`;
- `read_source`;
- `analyze_document`;
- `prepare_revision`;
- `write_output`;
- `verify_output`;
- `verify_source_unchanged`.

## Safe Metadata Rules

Snapshots contain only redacted metadata such as workflow id, operation id,
current step id/name, completed step ids, progress, and safe filenames/counts.
Complete document content, revised content, credentials, raw audio, provider
clients, GUI objects, file handles, raw exceptions, `CommandProcessor`, and
`ActionRouter` are excluded.

## Manual Smoke Steps

1. Run `python -m pytest tests\unit\test_workflow_runner.py`.
2. Run `python -m pytest tests\integration\test_task_084_workflow_runner.py`.
3. Create a temporary UTF-8 `.txt` file.
4. Execute `проверить документ <absolute-path>`.
5. Confirm that the response is `awaiting_confirmation`, progress is below
   100, and no output exists.
6. Execute `да`.
7. Confirm that the same operation succeeds, progress is 100, output exists,
   and the original file is unchanged.
8. Repeat with `отмена` and confirm no output is written.

## Deferred

Planner behavior, DAGs, parallel execution, persistent workflow storage,
crash recovery, rollback, background scheduling, distributed execution,
workflow marketplaces, GUI redesign, new file formats, and new providers remain
non-goals.
