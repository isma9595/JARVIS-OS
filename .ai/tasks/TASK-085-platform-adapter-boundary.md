# TASK-085 — Platform Adapter Boundary Based on Real Workflow

## Scope

TASK-085 extracts only the local file operations used by the TASK-083 document
review workflow behind a typed filesystem port. The document workflow still owns
document rules: `.txt` support, UTF-8/BOM behavior, size policy, issue
detection, output naming, confirmation behavior, workflow steps, and Russian
messages.

## Boundary

`workflows.document_review.LocalTextDocumentReviewWorkflow` depends on
`LocalFileSystemPort` from `platform_adapters.contracts`.

The port is responsible for:

- safe local path inspection;
- absolute/local/UNC/symlink metadata;
- bounded byte reads;
- same-path comparison;
- sibling path construction using local path rules;
- create-new atomic output writes;
- saved byte verification;
- cleanup of incomplete temporary files;
- safe typed filesystem errors.

The adapter is not responsible for:

- document issue codes;
- whitespace or newline rules;
- workflow step names;
- AppService, policy, confirmation, command processing, providers, or GUI state.

## Windows-First Adapter

`platform_adapters.local_filesystem.WindowsLocalFileSystemAdapter` is the current
production implementation. It uses Python filesystem primitives with
Windows-compatible behavior and rejects UNC/network paths. It accepts only local
absolute paths for document workflow reads and writes.

## Composition

`JarvisAppService` is the production composition root:

`JarvisAppService -> LocalTextDocumentReviewWorkflow -> LocalFileSystemPort`

Desktop Shell and voice continue to depend only on AppService. Tests can inject
counting or in-memory filesystem ports directly into AppService or the workflow.
There is no global adapter, service locator, or GUI-created adapter.

## Atomic Write Guarantees

The production adapter creates a temporary sibling file, writes bytes, flushes
and fsyncs where practical, creates the final target only if it does not already
exist, verifies final bytes, and removes temporary files on controlled failure.
Existing output files are never overwritten and the source path is rejected as a
target.

## Safe Errors

Raw OS exceptions are converted to `LocalFileSystemError` with safe codes such
as `network_path_denied`, `path_not_absolute`, `file_not_found`,
`symlink_denied`, `target_exists`, `source_target_conflict`, `write_failed`, and
`verification_failed`. User-facing DTOs receive existing document workflow
errors and safe Russian messages, not raw exception strings.

## Direct Filesystem Prohibition

`workflows/document_review.py` must not call direct filesystem write/read
primitives such as `open`, `Path.read_bytes`, `Path.write_bytes`, `os.rename`,
`os.replace`, `os.remove`, or `unlink`. A regression test checks this with AST
inspection.

## Known Limitations

This task does not implement Linux, macOS, mobile, remote filesystem, cloud
storage, network shares, DOCX, RTF, PDF, file picker, process control, clipboard,
notifications, or a general platform framework.

Future Linux compatibility should add a separate adapter implementing the same
port and preserving the same workflow-level guarantees.

## Manual Smoke

```powershell
python -m pytest tests\unit\test_local_filesystem_adapter.py tests\unit\test_document_review_workflow.py tests\integration\test_task_085_platform_adapter_boundary.py
python -m pytest tests\smoke\test_assistant_smoke.py -q
python -m pytest
python -W error::DeprecationWarning -m pytest
powershell -ExecutionPolicy Bypass -File scripts\health_check.ps1
git status --short
git diff --stat
```

## Permanent Verification Order

1. Focused task tests.
2. Permanent assistant smoke.
3. Full pytest.
4. Strict DeprecationWarning pytest.
5. Health check.
6. Git diff checks.
