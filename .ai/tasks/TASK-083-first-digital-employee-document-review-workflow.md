# TASK-083 — First Digital Employee: Local Document Review Workflow

## Scope

TASK-083 adds one concrete workflow:

`local .txt review -> deterministic issues -> proposed revision -> user confirmation -> save verified copy`

Supported input is a local regular `.txt` file encoded as UTF-8 or UTF-8 with
BOM. The file size limit is 1 MiB. The workflow rejects missing files,
directories, symbolic links, UNC/network paths, unsupported extensions, binary
files, invalid UTF-8, oversized files, existing output files, and source/output
path equality.

DOCX, RTF, PDF, Office automation, cloud documents, AI proofreading, semantic
rewriting, file picker UI, and general workflow orchestration are deferred.

## Command

Exact AppService command syntax:

```text
проверить документ <absolute-local-path>
```

Example:

```text
проверить документ C:\JARVIS-OS\task083-sample.txt
```

Preview is metadata-only. It does not read the file, create an operation, or
write anything. It reports that execution will require local file reading and
that saving a reviewed copy requires later confirmation.

## Deterministic Review Rules

The workflow detects and proposes only conservative formatting fixes:

- trailing spaces or tabs on ordinary lines;
- three or more consecutive empty lines, reduced to two;
- missing final newline;
- mixed line endings, normalized to the dominant detected convention where
  practical.

It does not change spelling, grammar, legal meaning, punctuation meaning,
names, dates, numbers, email addresses, URLs, file paths, quoted text, or
document semantics.

Issues are exposed as typed safe summaries with:

- `issue_code`;
- `line_number`;
- Russian description;
- `fix_available`;
- safe metadata only.

Complete source and revised document contents are not stored in the execution
journal.

## Lifecycle

Review lifecycle:

```text
created -> running -> awaiting_confirmation -> running -> succeeded
```

Cancellation lifecycle:

```text
created/running/awaiting_confirmation -> cancelled
```

Unsafe input or policy denial transitions to `failed` or `denied` according to
the existing AppService/ExecutionCoordinator conventions.

The same `operation_id` is preserved across review, confirmation, and
cancellation. Duplicate confirmation cannot save twice because pending workflow
state is single-use.

## Output

The output path is a deterministic sibling file:

```text
<source-stem>.jarvis-reviewed.txt
```

Example:

```text
task083-sample.txt -> task083-sample.jarvis-reviewed.txt
```

The workflow never modifies the original. It refuses to overwrite an existing
output file. Saving uses a temporary sibling file, flushes it, renames it to the
new target, verifies the saved bytes, and verifies that the source hash remains
unchanged.

## Policy

TASK-083 uses the TASK-081 policy boundary:

- `file_read` for the analysis step;
- `file_write` for saving the reviewed copy.

Document reading is allowed only after explicit workflow execution. Saving a
new file requires explicit confirmation. The Desktop Shell and voice path still
enter through AppService and do not call `ActionRouter` or bypass policy.

## Idempotency

TASK-083 uses the TASK-082 ExecutionCoordinator and ExecutionJournal. The same
idempotency key and fingerprint return the existing operation result without a
second read/write execution. The same idempotency key with a different
fingerprint is denied and writes nothing.

Journal metadata is redacted and bounded. It stores workflow IDs, filenames,
hashes, byte counts, issue codes, and operation state, but never full source or
revised document content, provider responses, credentials, raw audio, GUI
objects, or internal clients.

## Manual Smoke Procedure

1. Create a UTF-8 `.txt` file with trailing spaces, three or more empty lines,
   and no final newline.
2. Run:

   ```text
   проверить документ C:\absolute\path\sample.txt
   ```

3. Verify status is `awaiting_confirmation`, issues are shown in Russian, and
   `<stem>.jarvis-reviewed.txt` does not exist.
4. Run:

   ```text
   да
   ```

5. Verify the same operation ID succeeds, the output file exists, saved and
   verified are `yes`, and the original file hash is unchanged.
6. Repeat with `отмена` after review and verify no output is created.

## Known Limitations

This is intentionally not a workflow engine. TASK-084 will extract reusable
workflow-runner abstractions after this scenario proves the requirements.

The workflow handles local `.txt` only. Rich document formats and cloud
documents need different parsers, richer previews, and format-preserving save
semantics, so they are out of scope for TASK-083.

