# TASK-124 - Desktop Interaction Worker and Shutdown

## Objective

Keep the Tk main loop responsive while standard Desktop typed turns, one-shot
voice requests, and workflow resume operations use one bounded interaction
lifecycle.

## Verified Baseline

- Baseline commit: `88e7a4daa9625d3cea61f790bef610049dc908fe`.
- Baseline tree: `c990fb290f2ad8fab7b2abbf477dd60666082d04`.
- TASK-123 is published and is a required dependency.
- Baseline acceptance: `2476 passed, 2 skipped in 9.23s`.

## Architecture Boundary

`DesktopInteractionWorker` owns only one thread, one interaction slot,
interaction identity, cooperative cancellation signalling, completion delivery,
and shutdown state. AppService remains the application facade. Cognition,
execution, workflow, provider, persistence, and Desktop presentation ownership
do not move into the worker.

## Worker Contract

The worker is lazy, serialized, and reusable. It creates one fixed-name
non-daemon thread on the first accepted submission, retains no backlog, rejects
work while an operation or unconsumed completion occupies the slot, and delivers
each completion once. Safe snapshots expose bounded lifecycle metadata only.

## Interaction Lifecycle

Accepted typed, voice, and workflow-resume operations receive a stable
`desktop-interaction-<uuid>` id. The same id protects submission, cancellation,
and completion application from stale or duplicate delivery. Desktop busy state
is a presentation projection, not execution activity or a new domain owner.

## Cancellation Semantics

Cancellation is cooperative only. An operation cancelled before its callable
starts, or a token-aware callable that acknowledges cancellation, may complete
as CANCELLED. A started opaque AppService call that returns normally remains
COMPLETED even when cancellation was requested late. There is no force-stop,
rollback, or direct execution/workflow cancellation call. Completion
publication is the cancellation linearization boundary: a request accepted
before publication is reflected in that completion, while a request after
publication is rejected without changing the token. Retained active metadata
until completion consumption does not imply that cancellation remains
available.

## Tk Thread Boundary

Worker perform helpers receive captured inputs, call only AppService, and do not
read or mutate `DesktopShellState`. Completion polling and all apply, widget,
render, refresh, `after`, and destroy calls remain on the Tk main thread.

## Shutdown Semantics

Idle close prevents submissions, stops the worker, and destroys the root once.
Busy close requests cooperative cancellation, keeps polling without blocking Tk,
consumes the completion without presenting a late user result, waits for the
non-daemon worker to stop safely, and then destroys once. `run()` also performs
shutdown and join after mainloop exits, then consumes any pending completion
without UI apply. During shutdown the worker can stop independently of
completion consumption while preserving that completion for exactly-once
retrieval. Busy close immediately projects the worker's authoritative
cancellation state. Desktop shutdown does not close the ACTIVE conversation
session, so TASK-123 resume remains available.

## Approved File Scope

The approved scope is the worker module, Desktop shell, their focused tests and
architecture regression, this task record, checkpoint, README, and the four
approved architecture/roadmap/Desktop documents. No AppService, cognition,
core, workflow, voice, memory, filesystem, or launcher file is changed.

## Out Of Scope

No new AppService API, provider conversation, memory integration, unified user
data, persistence migration, routing change, new voice/TTS capability,
background automation, queue, multiple worker, asyncio, forced termination,
telemetry, dependency, CI, staging, commit, or push is included.

## Acceptance Criteria

- One lazy serialized non-daemon thread serves all three Desktop GUI entry points.
- Duplicate work is rejected atomically with no backlog or double execution.
- Tk and `DesktopShellState` are changed only on the main thread.
- Cancellation and late-cancellation results are reported truthfully.
- Idle and busy shutdown wait for confirmed safe stop and never close the ACTIVE conversation.
- Existing synchronous ViewModel methods and domain ownership remain compatible.

## Validation

- Focused RED: two expected collection errors because
  `app.desktop_interaction_worker` did not yet exist.
- Pre-audit focused GREEN: `134 passed in 2.24s`.
- Pre-audit related regression: `386 passed, 1 skipped in 3.58s`.
- Compileall: passed for both production modules.
- Pre-audit non-GUI event-driven smoke: `4 passed in 0.82s`.
- Historical pre-audit full acceptance: `2500 passed, 2 skipped in 10.41s`.
- First audit remediation RED: `5 failed, 133 passed in 4.25s`, limited to the two
  reported shutdown/projection defects.
- First audit remediation focused GREEN: `138 passed in 1.94s`.
- First audit remediation related regression:
  `391 passed, 1 skipped in 3.71s`.
- First audit remediation compileall: passed.
- First audit remediation non-GUI smoke: `5 passed in 1.01s`.
- First post-remediation full acceptance:
  `2504 passed, 2 skipped in 20.64s` in its single authorized full pytest run.
- Second audit remediation controlled RED: `2 failed in 0.80s`, limited to
  cancellation after completion publication and its Desktop projection.
- Second audit remediation focused GREEN: `140 passed in 1.13s`.
- Second audit remediation related regression:
  `393 passed, 1 skipped in 5.03s`.
- Second audit remediation compileall: passed.
- Second audit remediation safe non-GUI smoke: `5 passed in 0.49s`.
- Second post-remediation full acceptance:
  `2506 passed, 2 skipped in 24.68s` in the single authorized full pytest run.
- Second audit remediation final whitespace gate: `git diff --check: exit 0`;
  Git reported only ordinary potential LF-to-CRLF conversion warnings, with no
  whitespace errors.
- Third audit remediation targeted regression:
  `tests/unit/test_desktop_interaction_worker.py::test_cancel_after_completion_publication_is_rejected_and_result_stays_truthful`
  passed in its single authorized run: `1 passed in 0.11s`.
- Final regression-contract strengthening is limited to the existing
  post-publication late-cancel worker nodeid and the final whitespace gate; no
  focused, related, or full pytest rerun is part of this phase.
- Worker tests use one failure-safe harness: every worker and operation-holding
  release event is registered; teardown releases test gates before cooperative
  cancel, shutdown, and bounded join, independently of preceding assertions.

## Next Stage

TASK-125 - Unified User Data and Persistence Health. Staging, commit, and push
are not part of this implementation phase.
