# TASK-121 - MemoryPolicy Foundation

## Objective

Add a deterministic, stateless, immutable, and side-effect-free memory policy
boundary that evaluates fully formed personal-memory requests and returns only
safe, serializable policy decisions.

## Architectural Boundary

`MemoryPolicy` owns memory eligibility decisions only. It does not own memory
records, persistence, approvals, sessions, workflows, execution operations,
provider context, user profiles, or Desktop state.

Only `MemorySubjectKind.USER_FACT` is supported. Profile preferences,
conversation sessions, workflow state, execution operations, Desktop
diagnostics, and provider context remain under their existing authoritative
owners.

The policy:

- performs no file, repository, provider, network, workflow, execution, clock,
  or runtime-state access;
- receives detached existing-record summaries from its caller;
- never reads `LocalMemoryManager` or any other storage;
- treats approval as an already verified input fact and stores no pending
  approval state;
- returns a duration rule and never computes `expires_at`;
- validates every record id as a string of 1 through 128 ASCII characters:
  the first character is `[A-Za-z0-9]`, subsequent characters are
  `[A-Za-z0-9._:-]`, whitespace and control characters are forbidden, and the
  supplied form must already be Unicode NFKC-normalized;
- applies a dedicated anchored record-id credential guard after the opaque-id
  grammar check, rejecting credential/secret labels separated by any allowed
  id separator before an id can enter a decision;
- never exposes raw keys, values, existing records, or secret fragments in its
  decision projection.

## Accepted Decision Matrix

### UPSERT

- Safe explicit user facts are allowed and retained until the user forgets
  them.
- Inferred facts without verified approval require approval and receive the
  bounded candidate retention of 86400 seconds.
- Approved inferred facts are allowed and retained until forgotten.
- System- or provider-derived facts are rejected without verified approval and
  allowed with verified approval.
- Secret-like content is always rejected, including when approval is present.
  Deterministic guards cover structural credential labels, English and Russian
  password forms, token/API-key/private-key forms, and bearer authorization.
- Exact normalized duplicates are no-op mutations and identify the matching
  existing record.
- Same-key different-value writes supersede the unique existing record.
- Multiple same-key records are rejected as ambiguous.

### DELETE_EXACT

- A unique exact target record id is allowed.
- Missing, unknown, or ambiguous exact targets are rejected.
- No textual or semantic target guessing is permitted.

### DELETE_ALL

- Without verified approval, deletion requires approval.
- With verified approval, deletion is allowed.
- The policy creates and stores no confirmation state.

## Invariants

- Contracts and decisions are immutable.
- Mutable list, dict, set, bytearray, or nested mutable containers supplied in
  any scalar field of any frozen DTO are programmer misuse and raise
  `TypeError` during construction. The check recursively traverses tuple and
  frozenset containers. Caller-owned `existing_records` and `reason_codes`
  collections are snapshotted to tuples before storage. Unsupported immutable
  scalar types may be constructed but evaluate fail closed.
- Repeated evaluation of equal input returns an equal decision.
- Normalization is Unicode-aware and deterministic.
- No semantic similarity, fuzzy matching, embeddings, provider classification,
  or literal command phrase routing is used.
- Malformed and unknown inputs fail closed.
- Memory sensitivity is a separate memory-domain enum and does not reuse
  `AIContextSensitivity`.
- Existing `LocalMemoryManager` secret validation remains unchanged as defense
  in depth.

## Production Scope

- `cognition/memory_policy.py`
- `cognition/__init__.py`

## Test Scope

- `tests/unit/test_cognitive_memory_policy.py`
- focused update to `tests/unit/test_cognitive_architecture.py` for the approved
  module and forbidden dependency boundary

## Out Of Scope

- AppService, Desktop, CommandProcessor, provider, session, workflow, or
  execution integration
- Memory persistence or storage changes
- `MemoryService`
- durable `MemoryCandidate`
- automatic fact extraction
- migration of remember, recall, forget, or forget-all commands
- changes to user profile ownership
- changes to AI context privacy policy
- runtime diagnostics or operation metadata

## Acceptance Criteria

- All required enums and immutable DTOs are publicly exported from
  `cognition`.
- Decisions contain stable reason codes and JSON-safe primitives only.
- Candidate retention is exactly 86400 seconds without clock access.
- Secret, authority, malformed, duplicate, supersession, exact-delete, and
  delete-all rules match the accepted matrix.
- Policy imports no storage, provider, workflow, execution, filesystem, or
  clock owners.
- Existing memory, cognition, AppService, Desktop, TASK-119B, and TASK-120
  behavior remains unchanged.
- Focused and related regression tests pass.
- Exactly one final full `python -m pytest -q` passes after production and test
  code is final.
- `python -m compileall` for the production module and `git diff --check` pass.
- No commit or push is performed.

## Validation

- Preflight: `main`, `HEAD == origin/main ==
  db21ed45ba35d9a97db42bd27a6dd60de33b2658`, clean worktree.
- Initial foundation contract-first red: expected collection failure because
  the `MemoryPolicy` public API did not yet exist (`1 error`).
- Safety-review regression red after adding tests and before production fixes:
  `103 failed, 97 passed`.
- Final-review regression red for record-id separators and remaining mutable
  request fields: `66 failed, 259 passed`.
- Focused green:
  `python -m pytest -q tests/unit/test_cognitive_memory_policy.py
  tests/unit/test_cognitive_architecture.py` - `325 passed`.
- Existing memory/runtime regressions - `56 passed`.
- Cognition session/context/provider-boundary regressions - `310 passed`.
- AppService/Desktop/TASK-078 through TASK-084 regressions - `660 passed`.
- Production compileall:
  `python -m compileall -q cognition/memory_policy.py` - passed.
- `git diff --check` - passed; Git emitted only line-ending conversion
  warnings for existing tracked files.
- Superseded pre-review full suite: `2200 passed, 2 skipped`; invalidated by
  safety-review production and test changes.
- Superseded first post-review-fix full suite:
  `2333 passed, 2 skipped in 8.60s`; invalidated by final-review production and
  test changes.
- Final post-review-fix full suite: `python -m pytest -q` -
  `2458 passed, 2 skipped in 8.76s`.
- No manual Desktop smoke was run because TASK-121 has no runtime integration.
- No commit or push was performed.

## Next Stages

- TASK-122 - MemoryService read adapter over the existing memory storage.
- TASK-123 - durable MemoryCandidate and approval flow.
- TASK-124 - migration of explicit memory commands.

These stages are not implemented by TASK-121.
