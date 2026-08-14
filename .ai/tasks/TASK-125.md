# TASK-125 — Unified User Data and Persistence Health

## Status

Implementation and post-audit remediation are complete in the unstaged TASK-125
worktree. The initial full gate passed, a later read-only audit found four
migration/health edge cases, and their focused, related, compile, and new full
acceptance gates are green. TASK-126 and later work are not part of this task.
Staging, commit, and push are not part of this implementation phase.

## Objective

TASK-125 establishes one authoritative policy for resolving ordinary local
user-data paths, removes current-working-directory dependence from supported
Desktop and CLI launches, migrates only known deterministic legacy stores into
the canonical layout without deleting their sources, and exposes read-only
persistence health without disclosing paths, contents, identifiers, exception
details, or secrets.

## Verified Baseline

- Baseline commit: `7bc74d9d8f93947419ec443cfdd6bf4ed94db8d5`.
- Baseline tree: `3bf5cb5e72fb529f9581c6924fa6ae689d9b08df`.
- Baseline branch: `main`, equal to `origin/main` with divergence `0/0`.
- TASK-124 is published and the baseline worktree is clean.

## Dependencies And Preserved Boundaries

- TASK-123 provides repository-backed conversation persistence while
  `ConversationSessionService` remains the sole owner of conversation session
  lifecycle, ordering, and state.
- TASK-124 provides the Desktop interaction worker and shutdown boundary.
  TASK-125 does not change that worker or give it persistence ownership.
- TASK-121 `MemoryPolicy` remains stateless, storage-free, and disconnected from
  the existing runtime memory routes.
- TASK-122 is the source of the current normative roadmap numbering. The former
  `PlanPolicyEvaluator and Approval Records` use of TASK-125 is superseded
  unimplemented planning, not part of this task.

## Terminology

- **Canonical root**: the exact versioned root selected by `UserDataPaths` for
  ordinary local-data stores.
- **Canonical store**: the fixed default store path derived from the canonical
  root. It is authoritative only when no external per-store override is active.
- **Caller-supplied store override**: a store path supplied by an external
  caller before `UserDataPaths` defaults are derived or selected. The
  conversation environment variable described below is also an external
  per-store override.
- **Internal canonical injection**: the supported composition root passing a
  path derived from its `UserDataPaths` instance into an existing owner
  constructor or factory. This is default wiring, not a caller-supplied store
  override, and it does not skip migration.
- **Authoritative store**: the sole runtime store selected after precedence is
  applied: the effective caller-supplied override when one is active, otherwise
  the canonical store.
- **Legacy candidate**: one explicitly enumerated pre-TASK-125 location. A path
  discovered from CWD, recursive scanning, or an injected manager is not a
  legacy candidate.
- **Migration receipt**: the private, persisted, path-free provenance marker
  establishing that a canonical store has passed the TASK-125 adoption step.
  It is coordinator metadata, not a user-data store or a persistence owner.
- **Supported composition root**: the standard Desktop factory or CLI startup
  composition. Direct `JarvisAppService()` construction is not a supported
  persistence composition root.
- **Store owner**: the existing repository or manager that owns a store's
  contents and schema. `UserDataPaths`, migration, and health are not store
  owners.
- **Publication linearization point**: the successful safe no-clobber creation
  of the canonical filesystem entry. Receipt publication is a later, separate,
  recoverable provenance step.
- **Migration-attempt projection**: the immutable, privacy-safe result of one
  bounded coordinator attempt. It reports that attempt's stable internal/public
  code to the composition caller; it is not a persistence-health snapshot, is
  not persisted, and is never treated as mutable runtime truth.
- **Byte-identical**: identical immutable bytes for file stores, or the same
  set of relative regular-file names with identical bytes for a conversation
  directory. Semantically equal but differently serialized JSON is not
  byte-identical.

## Canonical Physical Layout

The user-data layout version is `v1`.

On Windows, the ordinary canonical root is:

```text
%LOCALAPPDATA%\JARVIS-OS\data\v1
```

When `LOCALAPPDATA` is absent or exactly empty, the fallback root is:

```text
~/.jarvis-os/data/v1
```

The root may be overridden with:

```text
JARVIS_USER_DATA_DIR
```

`JARVIS_USER_DATA_DIR` denotes the exact `v1` root, not its parent. An absent or
exactly empty value is treated as unset. A non-empty value must be an absolute
path. A relative value is rejected with stable safe code
`user_data_root_not_absolute`; a value that cannot be converted and lexically
normalized as a platform path is rejected with `user_data_root_invalid`. It is
never resolved against CWD. A derived store path that cannot be proven to
remain under the normalized root is rejected with
`user_data_path_outside_root`.

`LOCALAPPDATA` follows this exact controlled-environment contract:

- absent or exactly empty means unavailable and selects the home fallback;
- a non-empty absolute value is lexically normalized and used as the parent of
  `JARVIS-OS/data/v1`;
- a non-empty relative value raises `UserDataPathResolutionError` with exact
  code `local_app_data_not_absolute` and is never joined to or resolved through
  CWD;
- a non-empty value that cannot be converted or lexically normalized as a
  platform path raises exact code `local_app_data_invalid`;
- a present invalid value never silently selects the home fallback.

For these contracts, "cannot be converted or lexically normalized" means that
platform `Path` construction or side-effect-free lexical normalization raises
because of a value such as an embedded NUL; TASK-125 does not probe path
existence or link identity during resolution. The expanded home fallback must
also be absolute and lexically normalizable; otherwise resolution raises exact
code `user_data_root_unavailable` rather than using CWD.

All `UserDataPaths` resolution failures use the public
`UserDataPathResolutionError`. Its exact public attribute is `code: str`;
`str(error)` and `repr(error)` contain only the stable code and exception type,
not the rejected value or any resolved path. The resolver codes required by
this task are `user_data_root_not_absolute`, `user_data_root_invalid`,
`user_data_root_unavailable`, `local_app_data_not_absolute`,
`local_app_data_invalid`, `user_data_path_outside_root`, and
`project_root_not_absolute`.

The resolver expands the home fallback, normalizes the selected absolute root,
and derives only the fixed lexical segments below. It verifies lexical
containment with path-component semantics rather than string-prefix matching.
It returns absolute bounded paths and creates no directory or file. Resolution,
equality, and inspection of `UserDataPaths` are side-effect free. Filesystem
link/reparse safety is deliberately checked later by migration and health,
because a side-effect-free lexical resolver cannot prove filesystem identity.

The ordinary canonical store subpaths are exactly:

```text
conversation/sessions/
memory/memory.json
profiles/default_user.json
ideas/ideas.json
voice/vosk_settings.json
```

`UserDataPaths` is immutable. Each supported composition root resolves and
retains one instance for its coordinator, health service, and composition
wiring. That instance is the sole source of derived canonical `Path` values
passed through current owner constructors; owners are not required to accept or
retain the `UserDataPaths` object itself. Desktop and CLI started under the same
environment must produce equal path values. Object identity across separate
Python processes is neither required nor meaningful. Private receipt, lock, and
staging entries are coordinator metadata, not additional canonical stores.

## Root And Store Override Precedence

The ordinary root is selected in this order, with invalid present values failing
at their own step rather than falling through:

1. non-empty absolute `JARVIS_USER_DATA_DIR`, when present;
2. `%LOCALAPPDATA%\JARVIS-OS\data\v1`, when `LOCALAPPDATA` is non-empty and
   absolute;
3. `~/.jarvis-os/data/v1`.

Conversation persistence retains `JARVIS_COGNITIVE_SESSION_DIR` as an exact
per-store override. Its precedence is:

1. a caller-supplied constructor or factory override;
2. `JARVIS_COGNITIVE_SESSION_DIR`;
3. `UserDataPaths.conversation_sessions`.

For memory, profile, ideas, and Vosk settings, a caller-supplied constructor or
factory override has the same precedence and semantics over the corresponding
`UserDataPaths` value. `JARVIS_USER_DATA_DIR` selects the canonical root and is
not a per-store override.

TASK-125 preserves the current exact-path behavior of per-store overrides,
including a caller-controlled relative path. Such a relative external override
is intentionally not resolved by `UserDataPaths` and may retain legacy CWD
semantics. The CWD-independence guarantee applies to default canonical paths and
absolute external overrides; explicitly choosing a relative per-store override
opts out of that guarantee without making the path a migration candidate.

When a caller-supplied store override is active, or when
`JARVIS_COGNITIVE_SESSION_DIR` is active for conversation:

- migration, receipt handling, and canonical/legacy comparison for that store
  are skipped;
- the effective override is the only authoritative runtime store;
- before owner construction, the effective override and every existing
  ancestor used to reach it undergo the same no-follow physical-type,
  link/reparse, and safe-inspection gate as a canonical store;
- health checks only that effective override and does not inspect the default
  canonical, receipt, or legacy candidates;
- an absent effective override is `missing`;
- a present override is validated with the same store validator and yields
  `ready`, `corrupt`, `unsupported_version`, or `unavailable` as applicable;
- an unsafe/uninspectable override, or a present corrupt or unsupported
  override, blocks owner construction; a valid override is non-blocking;
- an absent override remains an explicitly selected initialization target and
  is non-blocking, so a later eager/lazy owner write may make a subsequent
  stateless health snapshot change from `missing` to `ready`.

An absolute override may be outside canonical/project root; no containment
under either default root is implied. A relative override retains its documented
CWD resolution. In both cases the resolved effective override itself is the
caller-authorized endpoint, but links/reparse points are never followed to
reach a different endpoint.

Passing `UserDataPaths.<store>` from the supported composition root into an
owner constructor is internal canonical injection. It must not be detected as
an external override and must not disable migration or receipt recovery.

Direct `JarvisAppService()` construction remains in-memory for cognition and
does not automatically resolve paths or run migration. Automatic local
persistence and migration are enabled only by the supported Desktop and CLI
composition roots.

## Deterministic Legacy Candidates

Migration may inspect only the following built-in candidates:

- conversation: the pre-TASK-125 versioned default location,
  `%LOCALAPPDATA%\JARVIS-OS\data\v1\cognition\sessions` or the corresponding
  `~/.jarvis-os/data/v1/cognition/sessions` fallback, computed from the legacy
  default rules without applying `JARVIS_COGNITIVE_SESSION_DIR`;
- memory: `<project_root>/memory/local/memory.json`;
- profile: `<project_root>/users/profiles/default_user.json`;
- ideas: `<project_root>/ideas/ideas.json`;
- Vosk settings: `<project_root>/config/local/vosk_settings.json`.

Production computes `project_root` exactly as:

```python
Path(platform_adapters.user_data_paths.__file__).resolve().parents[1]
```

Tests may inject only an explicit absolute `project_root`. A relative injected
value raises `UserDataPathResolutionError` with exact code
`project_root_not_absolute` and is never resolved through CWD. In an installed
layout, absence of a listed legacy path under this root means that candidate is
absent; no alternate installation, package, home, or CWD location is searched.
Historical CWD-relative copies of memory, profile, ideas, and Vosk settings
outside these deterministic project-root candidates are intentionally not
discovered.

The conversation-specific environment override is an active per-store
override, not a legacy candidate. The legacy conversation candidate is computed
by the existing pre-TASK-125 default resolver with
`JARVIS_COGNITIVE_SESSION_DIR` deliberately excluded.

The coordinator accepts a bounded, explicitly registered candidate collection
per store even though the built-in `v1` registry normally contains one
candidate for each store. This keeps `multiple_legacy_sources` deterministic if
a later reviewed specification adds another known location; discovered or
injected paths can never extend the collection implicitly.

TASK-125 prohibits:

- disk scanning or recursive discovery;
- searching arbitrary historical CWD locations;
- treating startup CWD as an implicit legacy root;
- migrating an arbitrary injected manager path;
- choosing a source by timestamp, size, directory enumeration order, or other
  heuristic;
- continuously reading from canonical and legacy stores after startup.

## Migration Trigger And Ownership

The migration coordinator is invoked explicitly:

1. after resolving the single composition-owned `UserDataPaths` instance;
2. before constructing any store owner;
3. only by supported Desktop and CLI composition roots.

The supported startup order is:

```text
resolve one UserDataPaths
resolve external per-store overrides
build the deterministic legacy registry
run the ordered coordinator decisions
finish required receipt publication or recovery
construct ordinary store owners with their authoritative paths
construct/project read-only health through AppService
```

Migration is not invoked from manager constructors,
`PersistenceHealthService`, direct `JarvisAppService()`, Desktop presentation,
or `DesktopInteractionWorker`.

The coordinator owns only the finite validate-and-publish attempt. It does not
own store contents, store lifecycle, runtime reads/writes, or health state.

Any blocking coordinator outcome prevents construction of all ordinary store
owners in that supported composition attempt. For default stores,
`not_required`, `migrated`, and `provenance_established` are non-blocking. For
an external override, the explicit owner-construction column in the ordered
table controls whether `skipped_external_override` is blocking; its code alone
does not make an invalid override safe. Health itself may still be invoked
read-only against an injected state for diagnostics, but cannot make a blocking
state non-blocking.

### Inter-Store Orchestration

The supported composition orchestrator evaluates ordinary stores fail-fast in
this exact stable order:

```text
conversation
memory
profile
ideas
vosk_settings
```

Each store evaluation is one independent, idempotent coordinator attempt and
projection. A default-store attempt acquires its own per-root/per-store lock
when migration/receipt state requires it; an active external-override preflight
does not create or acquire the skipped default-store migration lock. The
composition return value is an immutable `CompositionMigrationReport` with
exactly these public fields:

- `layout_version == "v1"`;
- `attempts`: an ordered tuple of `MigrationAttemptProjection` values forming a
  contiguous prefix of the stable store order;
- `completed: bool`;
- `blocking_store_id: str | None`: `None` when `completed is True`, otherwise the exact
  stable store ID of the final, blocking attempt in `attempts`.

If all five attempts are non-blocking, `attempts` contains all five entries,
`completed is True`, and `blocking_store_id is None`. On the first blocking
result, orchestration stops immediately: the blocking attempt is the last tuple
entry, later stores are not evaluated and receive no synthetic
`not_evaluated` result, `completed is False`, and no ordinary owner is
constructed.

Already completed per-store migration, canonical publication, or receipt
publication is never rolled back when a later store blocks. No delete, rename,
or compensating write is performed. A later supported startup re-evaluates the
stable order from `conversation`; completed stores resolve idempotently from
their published canonical/receipt state.

Therefore, if `conversation` migrates successfully and `memory` is corrupt, the
report contains exactly the `conversation` `migrated` projection followed by
the blocking `memory` `corrupt` projection; `profile`, `ideas`, and
`vosk_settings` are untouched, all ordinary owners remain unconstructed, and
the completed conversation migration remains published. `secure_keys` is not
part of this five-store orchestration because it has no TASK-125 migration.

The report and all representations obey the same privacy boundary as a
per-store projection. Stable store IDs and bounded counts are permitted; paths,
candidate identities, contents, exception text, and timing data are forbidden.

## Migration Provenance

For each default ordinary store, the coordinator reserves this private receipt:

```text
<canonical_root>/.migration/v1/<store_id>.json
```

Receipts apply only to `conversation`, `memory`, `profile`, `ideas`, and
`vosk_settings`. They never apply to the security-owned `secure_keys` store.
The exact receipt JSON is:

```json
{
  "layout_version": "v1",
  "store_id": "<stable_store_id>",
  "established": true
}
```

The object permits exactly those three keys and types:

- `layout_version` is the string `"v1"`;
- `store_id` is the exact expected stable store ID and must match the receipt
  selected for that store;
- `established` is the JSON boolean `true`, not integer `1` or any other value.

No field is optional and no unknown field is permitted. A receipt contains no
root, path, filename, user/home fragment, store content, record/profile/session
ID, digest, timestamp, candidate identity, exception text, traceback, or other
private value.

Receipt publication is atomic and no-clobber. It happens after successful
canonical publication or acceptance of a valid existing canonical, and before
store owners are constructed. Establishing provenance succeeds only when the
receipt itself has been published successfully. A canonical publication
followed by a receipt-publication failure is a recoverable incomplete attempt,
not a successful migration.

Receipt semantics are:

1. With a valid receipt and existing canonical, migration and every health probe
   whose initial receipt observation sees it validate only canonical. Retained
   legacy is not read, compared, or classified.
   Legitimate later canonical-only writes cannot create a false
   `canonical_legacy_conflict`.
2. With existing canonical and no receipt, canonical is validated first and
   deterministic legacy is inspected only after canonical is valid. No legacy,
   or one valid byte-identical legacy, permits atomic receipt establishment. A
   valid differing legacy conflicts; multiple, corrupt, and unsupported legacy
   states retain their exact ordered results below.
3. If a crash occurs after canonical publication but before receipt
   publication, a byte-identical legacy permits receipt recovery. If legacy is
   now absent, a valid canonical can also be safely adopted and receipted. A
   differing legacy remains a conflict. Owners are not created until recovery
   completes.
4. A valid receipt with missing canonical, or a correctly typed regular receipt
   file with invalid JSON, an invalid field/type/value, or the wrong
   store/layout, fails closed as `migration_state_invalid`. A receipt-path
   physical-type mismatch, link/reparse state, unsafe ancestor, or inspection
   failure is instead the operational result
   `migration_unavailable`/`unavailable`. Migration, repair, fallback, and owner
   creation do not proceed in either case.
5. When canonical and all deterministic legacy candidates are absent, the
   result is `not_required`, no receipt is created, and an owner may initialize
   canonical later. On the next supported startup, that valid canonical with no
   legacy may be adopted by atomically establishing its receipt.

After a valid receipt exists, retained legacy is only an unchanged archival
source copy. It no longer participates in runtime resolution, migration
classification, or any newly linearized health classification. An already
in-flight health probe whose initial observation selected the receipt-absent
branch may finish under the explicit health race rule below. Public health DTOs
do not reveal a receipt through an explicit presence field and never reveal its
location or contents. The safe `migration_state_invalid` code may reveal only
the bounded fact that private migration provenance is invalid.

## Ordered Migration And Health Precedence

Every ordinary-store migration and health classification follows this order. A
later step is never evaluated after an earlier matching branch. The coordinator
returns the internal migration result and a separate privacy-safe
migration-attempt projection. `PersistenceHealthService` independently applies
the read-only branches to the filesystem state visible at probe time; it does
not inherit, cache, or replay a coordinator result. A pre-write or pre-owner
health code shown below describes that observed state at that point, not a
promise that a later health snapshot will retain the same code after a
filesystem write or failed write attempt. The security-owned `secure_keys`
store has no canonical migration/receipt decision and follows only its dedicated
metadata matrix and DPAPI exception.

The immutable `MigrationAttemptProjection` exists only as the return value and
immediate startup diagnostic of one per-store coordinator invocation. It is never
persisted, reused by a later health call, or merged into a health snapshot. Its
complete public shape is `layout_version`, `store_id`, safe `code`, and
`blocking: bool`. Safe attempt codes are `not_required`, `migrated`,
`provenance_established`, `skipped_external_override`, `corrupt`,
`unsupported_version`, `canonical_legacy_conflict`,
`multiple_legacy_sources`, `migration_state_invalid`, and `unavailable`.
Internal `legacy_corrupt`, `legacy_unsupported_version`, and
`migration_unavailable` map to public attempt codes `corrupt`,
`unsupported_version`, and `unavailable`. The projection and all its
representations obey the privacy boundary below.

### 1. Active External Override

| Condition at pre-owner inspection | Coordinator result | Stateless health code for the same observed state | Owner construction |
| --- | --- | --- | --- |
| Effective override absent | `skipped_external_override` | `missing` | allowed; the override remains the explicit initialization target |
| Effective override valid | `skipped_external_override` | `ready` | allowed |
| Effective override corrupt | `skipped_external_override` | `corrupt` | blocked |
| A versioned effective override has a well-typed but unsupported version value | `skipped_external_override` | `unsupported_version` | blocked |
| Override has a top-level physical-type mismatch, link/reparse state, unsafe ancestor, or cannot be safely inspected | `migration_unavailable` | `unavailable` | blocked |

Only the override is inspected. Default receipt, canonical, and legacy paths are
not resolved for store-state decisions in this branch. The inspection occurs
before owner construction. If an absent override is subsequently initialized by
its owner, a later stateless health probe reports the newly observed state; it
does not replay the earlier `missing` result.

### 2. Receipt Exists

1. Safely inspect the receipt entry before canonical. A top-level physical-type
   mismatch, link/reparse state, unsafe ancestor, or inspection failure produces
   `migration_unavailable`/`unavailable`.
2. A correctly typed regular receipt file with invalid JSON, shape, field,
   type, value, store ID, or layout produces `migration_state_invalid` for
   migration and health.
3. A valid receipt with absent canonical also produces
   `migration_state_invalid`.
4. With valid receipt and existing canonical, validate only canonical:
   `not_required`/`ready` when valid, `corrupt`/`corrupt` when corrupt,
   `unsupported_version`/`unsupported_version` when its store supports versions,
   or `migration_unavailable`/`unavailable` on an operational failure.
5. Legacy existence and contents are completely ignored.

### 3. Receipt Absent And Canonical Absent

Before the coordinator or health counts existing deterministic candidates, it
performs a bounded no-follow presence/physical-type probe of every registered
candidate and every existing ancestor required to reach it. An absent candidate
does not count. If any candidate is a link/reparse point, has the wrong
top-level physical type, cannot be inspected safely, or is reached through an
unsafe ancestor, classification stops with coordinator result
`migration_unavailable` and stateless health `unavailable`. This safety result
takes precedence over `multiple_legacy_sources`. Only safely classified,
existing entries of the expected physical type participate in the count. The
coordinator validates store contents only when exactly one such candidate
exists; it does not choose or content-validate a source when more than one
exists.

| Safely classified existing deterministic legacy candidates | Validation | Migration result | Stateless health code before migration |
| --- | --- | --- | --- |
| `0` | none | `not_required` | `not_initialized` |
| more than `1` | none selected | `multiple_legacy_sources` | `multiple_legacy_sources` |
| exactly `1` | corrupt | `legacy_corrupt` | `corrupt` |
| exactly `1` | well-formed but unsupported schema/version | `legacy_unsupported_version` | `unsupported_version` |
| exactly `1` | valid | publish canonical copy, then receipt; final result `migrated` | `migration_required` until the coordinator completes, then `ready` |

The sole valid legacy is published with atomic copy-only no-clobber semantics.
The source is never changed. If canonical publication or receipt publication
cannot complete safely, the migration result and its migration-attempt
projection are `migration_unavailable`/`unavailable`, and no owner is created.
A later stateless health probe re-evaluates the actual filesystem state and may
return `migration_required`, `ready`, or another ordered state code; it does not
represent the failed attempt.

### 4. Receipt Absent And Canonical Exists

Canonical is validated before even counting legacy candidates:

| Canonical state | Migration result | Stateless health code for the same observed state | Legacy handling |
| --- | --- | --- | --- |
| corrupt | `corrupt` | `corrupt` | not inspected; no fallback |
| well-formed unsupported version | `unsupported_version` | `unsupported_version` | not inspected; no fallback |
| operationally unreadable/unsafe | `migration_unavailable` | `unavailable` | not inspected; no fallback |

Only after canonical is valid is deterministic legacy considered through the
same complete no-follow presence/physical-type probe defined in step 3. Any
unsafe or uninspectable registered candidate produces
`migration_unavailable`/`unavailable` before candidate count; only safe existing
entries of the expected type are counted.

| Safely classified existing legacy candidates | Legacy state | Migration result | Stateless health code before coordinator write |
| --- | --- | --- | --- |
| `0` | not applicable | establish receipt, then `provenance_established` | `ready` |
| more than `1` | not selected | `multiple_legacy_sources` | `multiple_legacy_sources` |
| exactly `1` | corrupt | `legacy_corrupt` | `corrupt` |
| exactly `1` | well-formed unsupported schema/version | `legacy_unsupported_version` | `unsupported_version` |
| exactly `1` | valid and byte-identical | establish receipt, then `provenance_established` | `ready` |
| exactly `1` | valid and differing | `canonical_legacy_conflict` | `canonical_legacy_conflict` |

Health never establishes the receipt. A valid canonical without receipt may be
reported `ready` only in the two non-conflicting adoption branches above; the
supported composition must still run the coordinator and publish the receipt
before constructing owners.

### 5. Operational Failure

Operational failures are classified in this exact order:

| Failure | Coordinator result | Migration-attempt projection | Independent stateless health snapshot |
| --- | --- | --- | --- |
| Unsafe/unreadable filesystem inspection, wrong top-level physical type, link/reparse state, or unsafe ancestor | `migration_unavailable` | `unavailable` | `unavailable` while the same inspection failure remains observable |
| Lock timeout before the attempt can evaluate or publish state | `migration_unavailable` | `unavailable` | recompute from filesystem through steps 1-4; do not replay the timeout |
| Permission denial, disk-full, or unsupported no-clobber primitive during staging/canonical publication | `migration_unavailable` | `unavailable` | recompute the unchanged pre-publication filesystem state through steps 1-4 |
| Canonical is published or adopted, but receipt publication fails | `migration_unavailable` | `unavailable` | recompute the now-visible canonical-without-receipt state through step 4 |

The migration-attempt projection is returned to the composition caller
separately from `PersistenceHealthService`; it is never inserted into or cached
as a store-health snapshot. Paths, OS error text, exception text, and traceback
are never projected. Every operational failure blocks owner construction for
all ordinary stores in that composition attempt. Invalid canonical is never
overwritten and never enables legacy fallback.

## Publication, TOCTOU, And Migration Concurrency

Migration is idempotent and copy-only. Its supported concurrency domain covers:

- threads in one process; and
- simultaneously running supported Desktop and CLI processes that use the same
  canonical root.

The coordinator uses a bounded per-root/per-store migration lock with a finite
timeout. Tests may inject a short finite timeout and a controlled lock adapter.
The lock protects only migration and receipt establishment; it does not extend
to normal runtime store operations. A foreign lock is never forcefully removed.
Any private lock entry must contain no user data and obey the link/reparse and
privacy rules below.

After acquiring the lock, an attempt re-evaluates receipt, canonical, and
allowed legacy state from the beginning. The canonical publication linearizes
at successful safe no-clobber creation of the canonical filesystem entry.
Receipt publication is a distinct later linearization point and recoverable
provenance step. A losing attempt re-evaluates the winner's published state and
never overwrites it. If the platform cannot supply the required safe no-clobber
primitive, the result is `migration_unavailable`.

For a file store:

- the source is opened without following links and read exactly once into an
  immutable byte snapshot;
- that exact snapshot is parsed and validated;
- those exact bytes, not re-read or reserialized data, are written to private
  staging and published;
- no partially written canonical file becomes visible.

For the conversation directory:

- immediate permitted entries are copied without following links into a unique
  private staging directory;
- staging contains only copied immutable entry bytes and is fully validated
  immediately before publication;
- the complete staging directory is published with one safe no-clobber
  filesystem operation;
- a partial canonical directory never becomes visible.

TASK-125 does not promise an atomic legacy-directory snapshot relative to an
uncoordinated external writer. It guarantees only that the staged snapshot it
publishes is complete and valid under the matrix below. General store
concurrency and multi-process safety of owners remain out of scope.

Only an attempt's own unpublished staging may be removed, on a best-effort
basis. Canonical and legacy are never deleted, renamed, replaced, rolled back,
or quarantined, and no partial canonical entry may remain.

## Link And Reparse Policy

Effective external overrides, legacy candidates, existing canonical entries,
receipts, staging entries, and migration locks must be regular non-link
filesystem entries of their exact expected file or directory type. Symlinks,
junctions, and Windows reparse points are not followed. Existing ancestors used
for I/O are checked so that a link/reparse cannot redirect reads or writes away
from the directly authorized endpoint or outside the normalized canonical root
or resolved project root that applies to the entry.

Any top-level file/directory type mismatch, detection of a link/reparse point,
or inability to perform a reliable no-follow/reparse check fails closed for the
coordinator as `migration_unavailable` with attempt projection `unavailable`.
When the same defect is in an override, canonical, receipt, or deterministic
legacy entry that stateless health is required to inspect, health is also
`unavailable`. Health never inspects private staging or migration-lock entries;
an unsafe staging/lock failure is visible only in the attempt projection, while
a later health snapshot independently recomputes public store state. For an
external override this gate occurs before owner construction and blocks an
unsafe owner. It does not impose canonical-root or project-root containment on
a directly specified override. A regular nested subdirectory inside an
otherwise safely opened conversation directory remains the separately defined
repository-content error `corrupt`; a nested link/reparse entry remains
`unavailable`.

Retained legacy is not selected for inspection or I/O by a coordinator or
health probe whose initial observation sees a valid receipt, and therefore
cannot trigger this policy even when it later becomes linked, unreadable,
wrongly typed, or otherwise unsafe. The only bounded exception is an already
in-flight health probe that linearized receipt absence before the valid receipt
was published.

`UserDataPaths` guarantees lexical containment only; migration, override
preflight, and health perform filesystem-level physical-type and link/reparse
validation immediately before I/O.

## Dual-Read Boundary

Runtime owners never dual-read and never use legacy as fallback. Bounded
inspection of deterministic legacy candidates is permitted only to the
migration coordinator and read-only health while a valid receipt is absent.
After a valid receipt is observed at coordinator evaluation or a health probe's
branch-selection point, that operation validates only canonical and ignores
retained legacy completely. An in-flight health probe that already linearized
receipt absence may finish its selected pre-receipt branch, but every subsequent
probe observes the receipt and is canonical-only.

Health recomputes a point-in-time advisory snapshot and stores no mutable
runtime truth. It never creates, establishes, repairs, replaces, or deletes a
receipt. After migration, canonical is the only normal write target for a
non-overridden store; an externally overridden store writes only to its
authoritative override.

## Store Validation Matrix

Validation is side-effect free and uses current owner/repository formats. It
does not instantiate an eager-writing manager, create a default, normalize or
reserialize a store, decrypt a secret, or add a schema field. Layout version
`v1` is not a store schema version.

For all JSON file stores, an invalid UTF-8 stream, malformed JSON, zero-byte
file, or non-object JSON top-level value inside a correctly typed regular file
is `corrupt`; permission/I/O/safe-inspection failure is `unavailable`. A
top-level directory where a store file or receipt file is expected, or a
top-level file where the conversation directory is expected, is never
`corrupt`: for an ordinary coordinator-controlled store or receipt it is
coordinator `migration_unavailable` and stateless health `unavailable`; for the
security-owned `secure_keys` store, which has no coordinator, health alone is
`unavailable`. A missing path is classified by precedence rather than as
corruption. JSON booleans are not integers for strict version fields.
Unknown-key and empty-object semantics are store-specific below. Migration
publishes the validated bytes unchanged.

Mixed failures use this deterministic validation order:

1. unsafe physical type, link/reparse state, permission/I/O failure, or an
   incomplete safe inspection is `unavailable` and takes precedence;
2. UTF-8, JSON, envelope, and key/type checks required to locate and type the
   declared version run next; their failure is `corrupt`;
3. a well-typed current version enables current-schema payload validation;
4. a well-typed non-current version is `unsupported_version` without applying
   current-version payload rules;
5. current-schema payload failure is `corrupt`; otherwise the store is valid.

For a conversation directory, all entries must first be safely readable. After
that complete inspection, any corrupt current-schema entry takes precedence
over any unsupported-version entry. Enumeration order never selects the code.

| Store ID | Physical type | Schema/version owner |
| --- | --- | --- |
| `conversation` | directory of session JSON files | conversation repository, schema integer `1` |
| `memory` | JSON file | `LocalMemoryManager`, version string `"0.1"` |
| `profile` | JSON file | `UserProfileManager`, no schema-version field |
| `ideas` | JSON file | `IdeaManager`, no schema-version field |
| `vosk_settings` | JSON file | `VoskSettingsManager`, no schema-version field |
| `secure_keys` | security-owned JSON file | secure-key subsystem, outer metadata version integer `1` |

Stores without a schema-version field never return `unsupported_version`
because an unknown key happens to be named `version`.

### Conversation

The store is a regular non-link directory. An absent default directory with no
legacy is `not_initialized`; an existing empty regular directory is valid and
`ready`.

The only permitted immediate repository entries are regular non-link files
named `<session_id>.json`, where `session_id` is non-empty and contains only
`A-Z`, `a-z`, `0-9`, `_`, `.`, or `-`. The filename must equal the JSON
`session_id` plus `.json`. There are no currently supported auxiliary,
recovery, nested, or temporary entries. Thus a non-JSON file, `*.tmp` entry,
unexpected regular entry, or subdirectory is `corrupt`; a link, junction, or
reparse entry is `unavailable`.

Each session file has exactly these required keys; unknown or missing keys are
`corrupt`:

| Key | Exact JSON contract |
| --- | --- |
| `schema_version` | integer, not boolean; `1` is supported |
| `session_id` | non-empty string satisfying the filename alphabet and matching the filename |
| `status` | string `"active"` or `"closed"` |
| `created_at`, `updated_at` | non-empty strings; no new datetime grammar is imposed |
| `turn_count` | integer, not boolean, at least `0`, equal to `len(turns)` |
| `last_turn_id` | `null` for no turns; otherwise non-empty string equal to the final turn ID |
| `turns` | list of turn objects described below |
| `revision` | integer, not boolean, at least `1` |

Each turn object has exactly these required keys; unknown or missing keys are
`corrupt`:

| Key | Exact JSON contract |
| --- | --- |
| `turn_id` | non-empty string |
| `sequence` | integer, not boolean, at least `1`; all entries must be contiguous `1..N` |
| `role` | string `"user"` or `"assistant"` |
| `source_classification` | normalized non-empty lowercase ASCII string, at most 64 characters, using only letters, digits, `_`, `.`, or `-` |
| `created_at` | non-empty string |
| `summary_text` | non-empty string of at most 160 characters |
| `content_classification` | `"bounded_redacted_summary"` or `"redacted_sensitive_content"` |
| `redaction_reason` | `null` or non-empty string |

Missing, wrongly typed, zero, or negative `schema_version` is `corrupt`.
An integer other than `1` is `unsupported_version`. Loader coercions such as
string `"1"` or boolean `true` are not valid migration sources. If a directory
contains both corrupt and unsupported records, `corrupt` takes precedence;
otherwise any unsupported record makes the directory `unsupported_version`.
The repository's existing partial runtime recovery remains unchanged, but
migration requires the complete directory snapshot to validate.

### Memory

The store is a regular non-link JSON file. The top-level value is an object with
these two required keys:

| Key | Exact JSON contract |
| --- | --- |
| `version` | non-empty string; only exact `LocalMemoryManager.STORAGE_VERSION == "0.1"` is supported |
| `items` | list; empty is valid; elements may be any JSON value because the current public `save_memory()` contract persists an arbitrary list |

Unknown top-level keys are accepted and copied unchanged because the current
loader ignores them; they are never projected by health. Missing, null, empty,
or non-string `version` is `corrupt`; any other non-empty string version is
`unsupported_version`. Missing or non-list `items` is `corrupt`. Exact version
`"0.1"` with an empty list is a valid empty store and `ready`. The layout
version `v1` is unrelated to memory schema version `"0.1"`.

### Profile

The store is a regular non-link JSON file whose top-level value is an object.
There are no required content keys: `{}` is a valid empty/default-bearing
profile and is `ready`. `create_profile()` normally emits `user_name`,
`preferred_name`, `assistant_name`, `language`, `age`, `main_use_cases`,
`communication_style`, `created_at`, and `updated_at`; generic
`save_profile()` accepts a mapping, preserves unknown keys, refreshes
`updated_at`, and adds `created_at` only when its current value is falsey.

Consequently every listed and unknown key is optional and may contain any valid
JSON value under the current generic load/save owner contract. Whole-file
migration must not apply `validate_assistant_name()`, which is only a setter
contract and is not applied by generic load/save or `create_profile()`.
Unknown keys are accepted and copied unchanged. A `version` key is ordinary
profile data and never yields `unsupported_version`. Malformed JSON or a
non-object JSON top level inside the expected regular file is `corrupt`. A
wrong top-level physical type or unsafe/unreadable I/O is unambiguously
`unavailable` under the global physical-type precedence.

### Ideas

The store is a regular non-link JSON file with an object top level. `ideas` is
optional; absence means the current loader's empty list. When present, `ideas`
must be a list. An empty list and `{}` are valid empty stores and `ready`.
Elements may be any JSON value because current public `save_ideas()` accepts an
arbitrary iterable and performs no element validation.

`add_idea()` normally emits objects with `id`, `title`, `description`, `source`,
`status`, `priority`, `created_at`, and `updated_at`, but that shape is not a
whole-store invariant of `save_ideas()`. Unknown top-level keys are accepted
and copied unchanged. A non-list `ideas` value is `corrupt` rather than being
silently coerced to empty. A `version` key is ordinary unknown data and never
yields `unsupported_version`.

### Vosk Settings

The store is a regular non-link JSON file with an object top level. Both known
keys are optional; `{}` is valid and `ready` because runtime defaults apply.

| Key | Missing semantics | Present-value contract |
| --- | --- | --- |
| `model_path` | no configured model | `null` or a non-empty, non-whitespace string |
| `language` | default `"ru"` | non-empty, non-whitespace string |

Unknown keys are accepted and copied unchanged. A relative or otherwise
non-canonical `model_path` string remains data; validation does not resolve it,
read it, check its existence, or initialize a model. A present invalid known
value is `corrupt` rather than being silently dropped by the lenient loader. A
`version` key is ordinary unknown data and never yields
`unsupported_version`.

### Secure Keys Metadata Only

`secure_keys` is a regular non-link JSON file at its security-owned location;
it has no migration candidate or receipt. When the Windows DPAPI backend is
available, an absent file is `not_initialized`; backend/platform inability to
inspect safely is `unavailable`.

The no-decrypt metadata probe validates the current writer envelope. The outer
object permits exactly these required keys; unknown or missing keys are
`corrupt`:

| Key | Exact JSON contract |
| --- | --- |
| `version` | integer, not boolean; exact `1` is supported |
| `backend` | exact string `"windows-dpapi"` |
| `entries` | object; empty is valid and `ready` |

Missing, wrongly typed, zero, or negative `version` is `corrupt`; another
positive integer is `unsupported_version`. Each `entries` value must be an
object with exactly `provider`, `secret_name`, `encrypted_value`, `masked_hint`,
`source`, and `updated_at`. Unknown or missing entry keys are `corrupt`.

- the entry-map key must equal `<provider>::<secret_name>`;
- `provider` and `secret_name` are non-empty results of the owner's
  trim-and-lower normalization; every character must satisfy Python
  `str.isalnum()` or be `_`/`-`, so no new ASCII-only restriction is imposed;
- `encrypted_value` is a non-empty string beginning `dpapi:` whose non-empty
  suffix is syntactically valid strict Base64; the probe may validate and
  immediately discard encrypted bytes but never calls DPAPI decrypt;
- `masked_hint` is a string beginning `***` with at most four following
  characters;
- `source` is the exact string `"stored"`;
- `updated_at` is a non-empty string.

For `secure_keys`, `ready` means only that the security backend is available and
the no-decrypt envelope metadata validates; it does not assert that any secret
can be decrypted or accepted by a provider. The probe may compute only
aggregate entry counts. Provider names, secret names,
map keys, encrypted values, masked hints, timestamps, and validation details are
never retained in or projected through public health data.

### Missing And Empty-State Semantics

- `not_initialized` means an effective default store is absent and no
  deterministic legacy candidate exists before the first owner write,
  regardless of whether the current manager happens to initialize eagerly or
  lazily.
- `missing` means an authoritative caller-configured override is absent.
- A sole valid legacy with no canonical/receipt is `migration_required` for
  read-only health until the coordinator completes; it is neither `missing` nor
  `not_initialized`.
- An existing empty store receives its store-specific valid/`ready` result from
  this matrix and is never automatically `not_initialized`.

## Read-Only Persistence Health

`PersistenceHealthService` is a read-only advisory projection. It does not own
persistence, determine runtime truth, cache mutable store state, or repair data.
It receives the resolved default paths, effective overrides, deterministic
candidate registry, and side-effect-free validators; it does not construct
store owners to rediscover them.

The service never receives or stores the preceding coordinator attempt as
health truth. A migration-attempt projection and a health snapshot are distinct
public values even when their safe codes happen to match. After a lock timeout,
publication failure, owner initialization, or other state change, health
recomputes only the currently observable filesystem state through the ordered
read-only branches. It may therefore differ from the earlier attempt projection
without contradicting it.

For each non-overridden ordinary store, health safely observes the receipt entry
exactly once before canonical or legacy inspection. Completion of that initial
receipt observation is the branch-selection linearization point for that health
snapshot:

- if a valid receipt exists at that point, the probe follows the receipt branch
  and never inspects retained legacy;
- if the receipt is absent at that point, the in-flight probe completes the
  pre-receipt branch selected by that observation, even if another supported
  process atomically publishes a valid receipt before legacy inspection ends;
- the in-flight pre-receipt probe is therefore permitted to inspect deterministic
  legacy selected before receipt publication, while the next health call sees
  the receipt and follows canonical-only precedence;
- invalid/unsafe receipt state observed initially returns its exact ordered code
  without repair or fallback.

Health does not restart, poll, or perform an unbounded final recheck. This rule
linearizes receipt precedence only; it does not promise an atomic snapshot of a
legacy directory relative to an uncoordinated external writer. The resulting
snapshot remains advisory and may be stale immediately after its branch-selection
point.

It must not:

- create a directory, file, default record, or temporary artifact;
- invoke migration;
- establish, repair, replace, or delete a migration receipt;
- construct eager-writing `IdeaManager`;
- mutate manager, repository, or store state;
- decrypt DPAPI content;
- initialize or call a provider, network, microphone, Vosk model/runtime, TTS,
  GUI, or other hardware boundary.

The stable store IDs are:

```text
conversation
memory
profile
ideas
vosk_settings
secure_keys
```

The minimum public health codes are:

```text
ready
not_initialized
missing
migration_required
corrupt
unsupported_version
canonical_legacy_conflict
multiple_legacy_sources
migration_state_invalid
unavailable
```

Their meanings are fixed by the ordered table and matrix above:

- `ready`: the authoritative store exists and validates.
- `not_initialized`: default canonical and deterministic legacy are absent
  before an owner write.
- `missing`: the active authoritative external override is absent.
- `migration_required`: canonical and receipt are absent while exactly one
  valid deterministic legacy source awaits the supported coordinator.
- `corrupt`: the ordered authoritative or pre-receipt source is structurally
  malformed under its store matrix.
- `unsupported_version`: a versioned store has a well-typed but unsupported
  schema/version under its matrix.
- `canonical_legacy_conflict`: receipt is absent and valid canonical differs
  byte-for-byte from the sole valid legacy candidate.
- `multiple_legacy_sources`: after the complete safety probe succeeds, the
  ordered pre-receipt branch finds more than one safely classified existing
  deterministic legacy candidate of the expected physical type.
- `migration_state_invalid`: a correctly typed regular receipt file has invalid
  JSON/shape/fields, belongs to the wrong store/layout, or is valid but exists
  without canonical; unsafe or wrongly typed receipt filesystem entries are
  `unavailable` instead.
- `unavailable`: safe inspection or the required platform/filesystem/security
  boundary is unavailable.

Migration may retain the internal codes `legacy_corrupt`,
`legacy_unsupported_version`, and `migration_unavailable`. When health
independently observes the same persistent inspection state, its corresponding
codes are `corrupt`, `unsupported_version`, and `unavailable`. A transient
write/lock failure is exposed only through the separate migration-attempt
projection; health does not replay it. Health follows the same state ordering
but never performs the writes described in coordinator branches. With a valid
receipt it never inspects legacy. With no receipt it may perform only the
bounded deterministic inspection required by the ordered table.

## Health Privacy Boundary

A public health snapshot may contain only:

- layout version;
- stable store ID;
- stable status/code;
- safe schema or layout metadata;
- aggregate counters.

The same restriction covers health snapshots, per-store migration-attempt
projections, `CompositionMigrationReport` and its nested attempts,
receipt-derived projections, DTO fields and nested values, `repr`, `str`,
`to_dict`, AppService projection, status cards, logs produced by this feature,
and error messages returned through this feature. They must not contain:

- canonical root or any other root;
- absolute or relative paths;
- filenames;
- username or home-directory fragments;
- record, session, profile, or other user-data identifiers;
- JSON or other persisted contents;
- setting values;
- legacy candidate identity or path, project root, staging path, receipt path,
  lock path/identity, or publication target;
- content digest, fingerprint, equality evidence, or receipt internals;
- secrets, encrypted values, masked hints, hashes of secrets, or secret
  fragments;
- raw OS error, exception text, exception representation, or traceback.

Health failures are represented only by stable safe codes and bounded counts.
Health is a point-in-time advisory snapshot and does not replace store-owner
state or guarantee the result of a later write.

## DPAPI Security-Owned Exception

`%APPDATA%/JARVIS-OS/secure_keys.json` is not relocated in TASK-125. Its
location remains owned by the security subsystem and is the documented
exception to the ordinary unified local-data root.

- DPAPI encryption at rest and the prohibition on plaintext fallback remain
  unchanged.
- Health may use only the no-decrypt metadata probe defined in the matrix. It
  never calls DPAPI decrypt, provider resolution, or key-listing APIs.
- Internal security ownership may retain its storage location, but public
  `ApiKeyManager` text/status, AppService status, `AppStatusCard`, and health DTO
  must no longer contain `storage_path` or an equivalent path field/value.
- Secure-key contents are never a migration source for TASK-125.
- No migration receipt is created for `secure_keys`.
- DPAPI relocation requires a separate future task and a dedicated migration
  contract.

## Composition And Runtime Ownership

- Desktop and CLI each resolve one `UserDataPaths` instance per process
  composition root.
- The same in-process instance is supplied to the migration coordinator and is
  the sole source of internal canonical paths passed to ordinary store owners.
- Passing a derived path into an owner is internal canonical injection, not an
  external override.
- External per-store overrides are resolved before migration and remain the
  sole authoritative paths for their stores.
- Every required migration/receipt decision completes before any ordinary store
  owner is constructed.
- `ConversationSessionService` remains the sole owner of session lifecycle.
- Each existing repository/manager remains the sole owner of its store contents
  and schema.
- `JarvisAppService` remains the application facade.
- Desktop never reads a persistence store directly.
- `DesktopInteractionWorker` receives no paths, migration API, health ownership,
  or persistence responsibility and is not modified.
- Health is exposed only through AppService and a privacy-safe
  `AppStatusCard`; Tk and other Desktop UI code require no store access.

## Vosk Composition Wiring

TASK-125 uses existing injection points and does not modify
`core/command_processor.py`:

1. Each supported Desktop/CLI composition creates one `VoskSettingsManager`
   with `UserDataPaths.vosk_settings` through internal canonical injection, or
   with the authoritative caller override when active.
2. That manager is passed through the existing
   `VoiceInputManager(..., vosk_settings_manager=...)` injection point.
3. The composition attaches that `VoiceInputManager` through the existing
   `CommandProcessor.set_voice_input_manager(...)` entry point before exposing
   the service. This prevents Vosk preflight/model-status paths from falling
   back to an independently constructed `VoskLocalBackend`.
4. The same manager is passed through
   `OneShotVoskRealRecognition(..., settings_manager=...)`.
5. The ready `OneShotVoskRealRecognition` is passed through
   `CommandProcessor(..., one_shot_vosk_real_recognition=...)`.
6. Supported TASK-125 composition roots therefore never use
   `CommandProcessor`'s default one-shot Vosk self-construction.

No microphone capture, Vosk model load, dependency download, or hardware access
is performed by this wiring. `tests/unit/test_command_processor.py` remains a
related regression unless the existing injection contract unexpectedly fails;
such a failure is a stop condition, not authority to expand scope.

## RED Regression Scenarios

The following deterministic regressions are required before their corresponding
production changes:

1. Two supported launches from different CWDs resolve identical default path
   values, and identical values for the same absolute external overrides;
   deliberately relative per-store overrides are excluded from this assertion.
2. Desktop and CLI under the same environment resolve identical path values.
3. The resolver returns absolute bounded paths and creates nothing.
4. Resolver environment edge cases have exact CWD-independent outcomes:
   a. relative non-empty `JARVIS_USER_DATA_DIR` raises
      `user_data_root_not_absolute`, and an unconvertible value raises
      `user_data_root_invalid`;
   b. absent or exactly empty `LOCALAPPDATA` selects the absolute home fallback;
   c. non-empty relative `LOCALAPPDATA` raises
      `local_app_data_not_absolute`;
   d. unconvertible or lexically unnormalizable `LOCALAPPDATA` raises
      `local_app_data_invalid` rather than falling back;
   e. an unusable non-absolute home fallback raises
      `user_data_root_unavailable`;
   f. none of these error branches resolves a value through CWD.
5. A derived store path cannot escape the canonical root.
6. With receipt and canonical absent, exactly one safely classified valid
   legacy store is copied, yielding coordinator `migrated`, pre-coordinator
   health `migration_required`, and post-receipt health `ready`.
7. Existing canonical data is never overwritten.
8. With receipt absent, valid canonical and one safely classified valid but
   differing legacy produce `canonical_legacy_conflict` without a write.
9. With receipt absent and valid canonical or absent canonical, more than one
   safely classified existing legacy source of the expected type produces
   `multiple_legacy_sources` and no source is selected automatically.
10. With receipt/canonical absent, one safely classified corrupt legacy yields
    migration `legacy_corrupt`, health `corrupt`, and creates no canonical.
11. With receipt/canonical absent, one safely classified well-formed but
    unsupported legacy yields migration `legacy_unsupported_version`, health
    `unsupported_version`, and creates no canonical.
12. Migration concurrency and inter-store orchestration are deterministic:
    a. with receipt/canonical absent and one safely classified valid legacy,
       two concurrent attempts for the same root/store both acquire the lock
       within their finite timeout; the exact result multiset is one `migrated`
       and one `not_required`, both projections are non-blocking, final health
       is `ready`, canonical and receipt are each published once, the source is
       unchanged, and no partial/overwrite is visible;
    b. in stable inter-store order, valid legacy conversation migrates first and
       corrupt memory blocks second; the report contains exactly those two
       projections, has `completed is False` with
       `blocking_store_id == "memory"`, later stores are untouched, no ordinary
       owner is constructed, and the completed conversation migration is not
       rolled back.
13. Legacy source is never deleted or renamed.
14. Health probing creates no filesystem object.
15. Health does not construct eager-writing `IdeaManager`.
16. Health DTO, `repr`, `str`, and `to_dict` disclose no private data.
17. Secure-key status contains no `storage_path`.
18. Health does not decrypt DPAPI or call provider/hardware boundaries.
19. Conversation partial recovery and lifecycle ownership remain unchanged.
20. Direct `JarvisAppService()` remains cognition-in-memory.
21. Desktop worker lifecycle and shutdown behavior remain unchanged.
22. Explicit manager paths retain their priority.
23. `JARVIS_COGNITIVE_SESSION_DIR` retains exact-path compatibility.
24. After migration, canonical is the only ordinary runtime write target.
25. Successful migration followed by a canonical-only runtime write and a new
    supported startup does not create a false conflict.
26. A valid receipt plus valid canonical makes migration return `not_required`
    and health return `ready` while ignoring differing, corrupt, unsupported,
    linked, unreadable, or additional retained legacy entries completely. In a
    controlled race, health first observes receipt/canonical absent and fully
    validates one legacy as the sole valid source, then pauses before publishing
    its snapshot while another process publishes canonical and receipt. The
    in-flight probe completes its already selected result as
    `migration_required`; the next probe observes the receipt and is `ready`
    without inspecting retained legacy.
27. A crash between canonical publication and receipt publication recovers the
    receipt when the retained legacy is byte-identical.
28. A valid receipt without canonical is `migration_state_invalid`.
29. A correctly typed regular receipt file with invalid JSON, fields, types,
    values, store ID, or layout yields `migration_state_invalid` for migration
    and health and is not repaired automatically; an unsafe or wrongly typed
    receipt entry is covered separately by scenario 41.
30. A caller-supplied external override is distinguished from internal
    canonical injection: valid and absent overrides skip default migration and
    allow owner construction, present corrupt/unsupported overrides block
    ordinary owner construction for that composition attempt, and internal
    canonical injection follows the normal receipt/migration table.
31. At pre-owner inspection, an absent authoritative external override yields
    coordinator `skipped_external_override` and health `missing`; owner
    initialization is allowed, and a later stateless health probe may then be
    `ready`.
32. With receipt, default canonical, and all deterministic legacy candidates
    absent before the first owner write, migration returns `not_required` and
    health returns `not_initialized`.
33. Valid canonical without receipt or legacy atomically establishes a receipt
    before owners are created.
34. Valid canonical without receipt and with one valid differing legacy is
    `canonical_legacy_conflict`.
35. Valid canonical without receipt and with one corrupt legacy is
    `legacy_corrupt` for migration and `corrupt` for health.
36. Valid receipt plus valid canonical ignores corrupt or unsupported retained
    legacy.
37. With receipt absent, invalid canonical takes precedence over legacy count
    and never enables fallback: corrupt current-schema canonical yields
    `corrupt`/`corrupt`; well-formed unsupported canonical yields
    `unsupported_version`/`unsupported_version`; unsafe or unreadable canonical
    yields `migration_unavailable`/`unavailable`.
38. With receipt and canonical absent, after the complete safety probe succeeds,
    more than one existing regular non-link legacy candidate of the expected
    type produces `multiple_legacy_sources` for migration and health.
39. Production `project_root` equals
    `Path(platform_adapters.user_data_paths.__file__).resolve().parents[1]`;
    an injected absolute test root is CWD-independent and a relative test root
    raises `UserDataPathResolutionError` with exact code
    `project_root_not_absolute`.
40. File migration publishes the exact validated immutable source snapshot.
41. A top-level wrong physical type, symlink, junction, reparse point, unsafe
    ancestor, or uninspectable entry selected by ordered precedence fails closed
    without being followed: canonical/receipt cases, and legacy cases only when
    receipt is absent at coordinator evaluation or the health branch-selection
    point, yield coordinator `migration_unavailable`, attempt projection
    `unavailable`, and stateless health `unavailable` as applicable; an unsafe
    external override yields the same codes and blocks owner construction for
    that composition attempt; staging/lock cases yield the same
    coordinator/attempt codes but are not inspected or replayed by later health;
    in a selected mixed candidate set this safety result wins before
    `multiple_legacy_sources`. A retained unsafe legacy ignored after a valid
    receipt is observed is explicitly outside this scenario and remains covered
    by scenario 26.
42. Lock timeout, permission denial, disk-full, or unavailable no-clobber
    publication returns coordinator `migration_unavailable` and migration-
    attempt projection `unavailable` without partial canonical or owner
    construction. A subsequent stateless health probe independently returns the
    ordered code for the filesystem state it then observes and does not replay
    the transient failure.
43. Conversation directory matrix is tested with exact placement and state:
    a. sole empty regular legacy with no receipt/canonical is valid, gives
       no corruption code, migrates as `migrated`, and changes health from
       `migration_required` to `ready` after receipt publication;
    b. empty valid canonical with no receipt/legacy is adopted as
       `provenance_established` with health `ready`;
    c. an unexpected regular file, temporary file, or regular nested directory
       in canonical yields `corrupt`/`corrupt`, while the same defect in the sole
       legacy source with no receipt/canonical yields
       `legacy_corrupt`/`corrupt`;
    d. a corrupt current-schema session in canonical yields
       `corrupt`/`corrupt`, while the same sole legacy defect yields
       `legacy_corrupt`/`corrupt` when receipt/canonical are absent;
    e. a well-formed session with integer schema other than `1` in canonical
       yields `unsupported_version`/`unsupported_version`, while the same sole
       legacy defect with no receipt/canonical yields
       `legacy_unsupported_version`/`unsupported_version`;
    f. a link/reparse entry in the canonical or sole legacy directory currently
       selected for validation yields
       `migration_unavailable`/`unavailable` and takes precedence over content
       classification.
44. Supported composition injects the canonical Vosk path through existing
    `VoiceInputManager`, `OneShotVoskRealRecognition`, and `CommandProcessor`
    entry points, attaches the voice manager through
    `set_voice_input_manager(...)`, and avoids all `CommandProcessor` default
    Vosk construction.

Tests must use temporary roots, controlled environment mappings, bounded
synchronization for thread/process concurrency, controlled no-clobber and
failure adapters, and no probabilistic sleep/stress loop. Link/reparse tests
must skip with an explicit platform capability reason only when the platform
cannot create the fixture; the production inability still maps to unavailable.
Tests must not read or write real user AppData, repository legacy data,
provider credentials, models, microphone, TTS, or documents. Every branch in
the ordered decision table and validation matrix requires an unambiguous
expected coordinator result, migration-attempt projection, and/or stateless
health code as applicable.

## Acceptance Criteria

- Supported Desktop and CLI default canonical paths, and absolute external
  overrides, are independent of CWD for all five ordinary stores. A deliberately
  relative caller override retains its documented legacy CWD semantics.
- Root resolution, precedence, fixed subpaths, and safe failures match this
  specification exactly.
- Absent/empty, absolute, relative, and malformed `LOCALAPPDATA` values follow
  their exact fallback/error branches without CWD resolution or silent fallback
  from a present invalid value.
- Resolution and health are side-effect free.
- Caller-supplied overrides and internal canonical injection are distinguished;
  every active override skips default migration/receipt logic and remains the
  only authoritative store.
- Every external override is physically inspected without following links
  before owner construction. Unsafe, corrupt, or unsupported existing
  overrides block ordinary owner construction for that composition attempt; an
  absent override remains an allowed explicit initialization target.
- Migration is deterministic, validate-first, snapshot-based, atomic,
  no-clobber, copy-only, idempotent, and limited to enumerated legacy
  candidates.
- Every registered legacy candidate receives a complete no-follow
  presence/physical-type probe before candidate count; any unsafe candidate
  produces `migration_unavailable`/`unavailable` before
  `multiple_legacy_sources` can apply.
- Each ordered branch produces its exact stable result; invalid canonical is
  never overwritten and legacy is never a runtime fallback.
- Successful canonical migration/adoption is complete only after its exact
  private receipt is atomically published.
- A valid receipt causes canonical-only validation, so later legitimate
  canonical writes never become false legacy conflicts.
- Crash recovery between canonical and receipt publication follows the exact
  byte-identical/no-legacy rules without constructing owners early.
- Bounded migration locking covers supported threads and processes without
  claiming general cross-process safety for mutable stores.
- Composition evaluates the five ordinary stores fail-fast in the fixed order,
  returns the exact immutable prefix report, never evaluates stores after the
  first blocker, never constructs any ordinary owner after a blocker, and never
  rolls back an already completed per-store migration.
- File and directory publication, TOCTOU snapshot rules, and link/reparse
  failures match this specification and expose no partial canonical.
- A top-level wrong physical type for an ordinary coordinator-controlled entry
  is always `migration_unavailable`/`unavailable`; `secure_keys` has health
  `unavailable` without a migration result. Only malformed contents inside a
  correctly typed entry are eligible for `corrupt`.
- The full store-validation matrix is implemented without inventing schema
  fields or treating layout `v1` as a store version.
- Corrupt, unsupported, conflicting, multiple-source, invalid-provenance,
  migration-required, missing, not-initialized, and unavailable states are
  safely observable with the specified precedence.
- Existing caller path injection and the conversation environment override
  remain compatible.
- Public health surfaces contain no path, filename, user-data identifier,
  content, receipt detail, digest, secret, exception, or traceback.
- A migration-attempt projection and a stateless health snapshot remain
  separate values; transient attempt failure is never cached or replayed as
  health, and later health reflects only the filesystem state it observes.
- Health linearizes receipt-branch selection at its first safe receipt
  observation: an in-flight absent-receipt probe may finish that branch, while
  every subsequent probe that observes the published receipt is canonical-only.
- Store content/schema ownership, conversation lifecycle ownership, AppService
  facade ownership, and Desktop main-thread presentation ownership do not move.
- Direct `JarvisAppService()` stays cognition-in-memory.
- DPAPI storage is not relocated or decrypted by health.
- Supported Vosk composition uses existing injection signatures; default
  construction in `CommandProcessor` is not used and that file is unchanged.
- No provider, network, GUI, microphone, Vosk model, TTS, or hardware operation
  is introduced or required.
- TASK-124 worker and shutdown contracts remain unchanged.

## Approved Production Scope

New production files:

- `platform_adapters/user_data_paths.py`;
- `platform_adapters/user_data_migration.py`;
- `app/persistence_health.py`.

Expected production modifications:

- `platform_adapters/__init__.py`;
- `app/app_contracts.py`;
- `app/app_service.py`;
- `cognition/persistence.py`;
- `core/kernel.py`;
- `run.py`;
- `memory/memory_manager.py`;
- `users/user_profile.py`;
- `ideas/idea_manager.py`;
- `voice/vosk_settings_manager.py`;
- `security/api_key_manager.py`.

`security/secure_key_store.py` may change only if a focused RED proves that a
side-effect-free, no-decrypt metadata probe cannot be supplied through its
existing contract. Such a change may expose only safe metadata and must not
relocate, decrypt, rewrite, migrate, or weaken the secure store.

The private receipt contract, receipt validation/publication, bounded
per-root/per-store migration locking, staging, and recovery belong inside
`platform_adapters/user_data_migration.py`; they do not create another
persistence owner or authorize another production file.

`UserDataPathResolutionError` belongs inside
`platform_adapters/user_data_paths.py`. The internal coordinator result and its
immutable privacy-safe migration-attempt projection belong inside
`platform_adapters/user_data_migration.py`. The fixed five-store fail-fast
orchestrator and `CompositionMigrationReport` also belong in that module; they
do not authorize another service or production file. Any AppService-facing
DTO/projection uses the already approved `app/app_contracts.py`. Separating
these attempt results from `app/persistence_health.py` does not create another
service or owner.

`core/command_processor.py`, `app/desktop_interaction_worker.py`,
`app/desktop_shell.py`, and `run_desktop.py` are not production modification
scope for TASK-125.

No other production file is approved without a separately reviewed scope
amendment.

## Approved Test Scope

New tests:

- `tests/unit/test_user_data_paths.py`;
- `tests/unit/test_user_data_migration.py`;
- `tests/unit/test_persistence_health.py`;
- `tests/integration/test_task_125_unified_user_data.py`.

Existing tests that may receive focused TASK-125 assertions:

- `tests/unit/test_cognitive_persistence.py`;
- `tests/unit/test_cognitive_session_persistence.py`;
- `tests/unit/test_memory_manager.py`;
- `tests/unit/test_user_profile.py`;
- `tests/unit/test_user_language_preference.py`;
- `tests/unit/test_language_manager.py`;
- `tests/unit/test_idea_manager.py`;
- `tests/unit/test_vosk_settings_manager.py`;
- `tests/unit/test_api_key_manager.py`;
- `tests/unit/test_secure_key_store.py`;
- `tests/unit/test_app_contracts.py`;
- `tests/unit/test_app_service.py`;
- `tests/unit/test_cognitive_app_service_integration.py`;
- `tests/unit/test_kernel.py`;
- `tests/unit/test_desktop_shell.py`;
- `tests/unit/test_cognitive_architecture.py`.

Receipt, precedence, publication, process/thread locking, TOCTOU, candidate
pre-count safety, per-store attempt projections, fail-fast inter-store reports,
and link/reparse RED belong in `test_user_data_migration.py`. Resolver,
override identity, exact `JARVIS_USER_DATA_DIR`/`LOCALAPPDATA`/project-root
errors, and fallback behavior belong in `test_user_data_paths.py`.
Receipt-linearization races, receipt-aware read-only behavior, independent
stateless recomputation, and privacy belong in `test_persistence_health.py`.
External-override pre-owner blocking, composition ownership, and Vosk injection
belong in the TASK-125 integration, AppService, and Kernel tests.

Related tests executed without modification include:

- `tests/unit/test_command_processor.py`;
- `tests/unit/test_voice_input_manager.py`;
- `tests/unit/test_one_shot_vosk_real_recognition.py`;
- `tests/integration/test_task_078_one_shot_voice_to_answer.py`;
- `tests/integration/test_task_087_startup_lazy_initialization.py`.

A related test may be modified only if a TASK-125 RED proves its existing
contract fixture must be updated. A failing unrelated test is not authority to
broaden production scope.

## Approved Documentation Scope

- `.ai/tasks/TASK-125.md`;
- `.ai/CHECKPOINT.md`;
- `README.md`;
- `docs/ARCHITECTURE.md`;
- `docs/DESKTOP_APP_SHELL.md`;
- `docs/ROADMAP.md`;
- `docs/architecture/COGNITIVE_ARCHITECTURE.md`.

Documentation is updated only after focused and related GREEN and records only
checks actually run.

## Explicitly Out Of Scope

- `app/desktop_interaction_worker.py` or any worker/background/async redesign;
- changes to `app/desktop_shell.py` or `run_desktop.py`;
- changes to `core/command_processor.py`; existing Vosk injections must be used;
- goal planning, `PlanPolicyEvaluator`, plan approval records, or planner
  redesign;
- `MemoryPolicy` integration or memory-candidate approval;
- execution, policy, coordinator, workflow, or command-routing semantics;
- provider configuration persistence or provider runtime changes;
- provider/network, real GUI, microphone, Vosk model, TTS, or hardware work;
- cloud sync, retention, backup framework, or release packaging;
- general cross-process locking for mutable stores;
- runtime legacy polling, owner-level dual-read, or permanent canonical/legacy
  comparison after a valid receipt;
- arbitrary install-root, package-root, home, or historical CWD discovery;
- following or migrating through symlinks, junctions, or reparse points;
- a general migration journal, receipt database, quarantine, rollback, or
  crash-recovery framework beyond the exact per-store receipt;
- automatic quarantine, deletion, rename, or destructive legacy cleanup;
- DPAPI relocation;
- TASK-126 or any later task;
- changes to the document-workflow filesystem adapter.

## Implementation And Validation Order

The implementation is test-first and proceeds in this order:

1. Add focused RED for resolver, exact environment-error/fallback, and privacy
   contracts.
2. Implement `UserDataPaths` only.
3. Add focused RED for the ordered migration table, receipt/provenance,
   immutable snapshots, link/reparse handling, no-clobber publication, bounded
   thread/process concurrency, and fixed fail-fast inter-store orchestration.
4. Implement migration and receipt handling only.
5. Add focused RED for health ordering, receipt branch-selection races,
   store-validation matrix, side effects, DPAPI metadata, and privacy.
6. Implement health only.
7. Integrate supported Desktop and CLI composition roots, including existing
   Vosk injection points.
8. Run the focused matrix.
9. Run one related regression matrix.
10. Update approved documentation after GREEN.
11. Run exactly one new full `python -m pytest -q` acceptance.

The focused matrix is expected to cover the three new unit modules, the new
TASK-125 integration module, all modified store tests, AppService contracts and
integration, Kernel composition, Desktop composition projection, and cognitive
architecture regression. It includes every ordered branch, receipt recovery,
receipt/health race linearization, both concurrency domains through bounded
deterministic harnesses, fail-fast inter-store ordering and no-rollback state,
link/reparse policy, all store matrix edge cases, and privacy
`repr`/`str`/`to_dict` checks.

The related matrix is expected to include conversation session persistence,
user-language behavior, command processor compatibility, voice-input/Vosk
settings compatibility, secure-key boundaries, Desktop shell regression, and
startup lazy-initialization regression.

The full pytest run is mandatory because TASK-125 changes default path
resolution, Desktop/CLI composition, the AppService contract, and migration
behavior. It runs once only after focused and related GREEN. After that gate,
only documentation of factual results and read-only Git scope/whitespace audits
are permitted; production or test fixes would invalidate the gate and require
a separately authorized remediation plan.

Real GUI, microphone, TTS, Vosk model, provider/network, and hardware checks are
not required and must not be used as acceptance evidence for this task.

## Failure And Stop Conditions

- A preflight mismatch stops the implementation before edits.
- A RED that passes on the current baseline must be corrected before production
  work; it is not valid regression evidence.
- An unrelated test failure stops the phase rather than broadening scope.
- A migration ambiguity, unidentified legacy location, or need to relocate
  DPAPI stops implementation for owner review.
- An incomplete store-validation matrix or an ambiguous expected branch code
  stops implementation before RED work.
- Inability to implement exact `LOCALAPPDATA` error/fallback semantics, the
  fixed fail-fast five-store report, or the initial-receipt health
  linearization stops implementation rather than selecting another behavior.
- Inability to keep migration-attempt projection separate from stateless health,
  or to apply the external-override safety gate before owner construction,
  stops implementation before composition work.
- Failure of the verified Vosk injection signatures, or a need to modify
  `core/command_processor.py`, stops implementation for a scope review.
- Inability to prove the exact project-root anchor, enforce no-follow/reparse
  checks, provide finite migration locking, or implement safe no-clobber
  publication on the supported target stops implementation rather than
  weakening the contract.
- Any need for runtime legacy fallback, a persistent journal beyond the exact
  receipt, another production file, or broader manager locking requires an
  explicit scope amendment.
- Source/staging state that cannot be validated safely maps to unavailable and
  must never be published merely to keep startup progressing.
- A required production file outside the approved scope requires an explicit
  scope amendment before modification.
- Any full-suite failure ends that acceptance attempt; it is not rerun or fixed
  without a new authorized remediation phase.

## Validation

- The pre-existing migration RED evidence was preserved: migration collection
  produced `117 errors in 8.79s` while the migration module was absent.
- Persistence-health RED: `18 failed in 0.44s`, all caused by the intentionally
  absent `app.persistence_health` module.
- Composition RED after correcting one test-only baseline assumption:
  `4 failed, 1 passed in 0.37s`, limited to missing TASK-125 factory/CLI wiring.
- CLI first-launch ordering regression: `1 failed in 0.34s` before the factory
  accepted profile setup ahead of kernel construction; the focused regression
  then passed with `1 passed in 0.52s`.
- Focused matrix: `570 passed, 2 skipped in 5.40s`.
- Related regression: `507 passed in 2.74s`.
- Compileall for the changed production modules completed with exit code `0`.
- The single full acceptance passed: `2669 passed, 4 skipped in 13.41s`.
- A subsequent read-only audit found an absent-leaf unsafe-ancestor bypass,
  failure to create a fresh multi-level canonical hierarchy, incomplete JSON
  parser-failure classification, and an unbound receipt-observation state.
- Post-audit remediation RED: `8 failed, 134 passed, 2 skipped in 2.36s`, with
  every failure limited to those four findings.
- Post-audit regression GREEN: `142 passed, 2 skipped in 1.84s`; final focused
  matrix: `578 passed, 2 skipped in 6.25s`; related regression:
  `507 passed in 2.92s`; compileall exit code `0`.
- The single post-audit full acceptance passed:
  `2677 passed, 4 skipped in 18.42s`.

## Next Stage

TASK-126 is not started by TASK-125 specification or implementation work.
Staging, commit, and push require separate explicit approval after acceptance.
