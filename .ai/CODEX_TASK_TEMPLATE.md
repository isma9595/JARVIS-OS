# Codex Task Template

## Task ID

TASK-XXX

## Task title

Short task name.

## Goal

Describe the exact technical goal.

## Why this matters

Explain why the change is needed and what risk or limitation it addresses.

## Allowed files/folders

- `path/to/allowed/file_or_folder`

## Forbidden files/folders

- `path/to/forbidden/file_or_folder`

## Required changes

- List the exact changes Codex must make.

## Safety rules

- Keep JARVIS-OS working.
- Do not change architecture unless explicitly approved.
- Do not delete existing features.
- Do not create unrelated files.
- Prefer small, testable changes.
- Preserve backwards compatibility.

## Tests to run

```powershell
pytest
```

## Manual verification steps

1. Start JARVIS-OS.
2. Confirm existing commands still work.
3. Confirm the new task result exists.
4. Run the health check.

```powershell
.\scripts\health_check.ps1
```

## Expected result

Describe the exact result the user should see after the task is complete.

## Rollback plan

Describe how to safely undo the task if verification fails.

## Commit message

Short imperative commit message.
