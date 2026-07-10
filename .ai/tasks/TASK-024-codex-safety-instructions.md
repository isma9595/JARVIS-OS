# TASK-024 - Codex Safety Instructions

## Task ID

TASK-024

## Task Title

Codex Safety Instructions

## Goal

Add persistent project-level safety instructions for Codex so future
Codex-assisted tasks do not break JARVIS-OS, do not create random files, and do
not make independent architecture decisions.

## Why This Matters

JARVIS-OS is stable after TASK-023. Future implementation work must preserve
that stability by keeping Codex constrained to approved tasks, approved files,
explicit user control, tests, and safe commits.

## Files Changed

- `AGENTS.md`
- `.ai/CHECKPOINT.md`
- `.ai/tasks/TASK-024-codex-safety-instructions.md`

## Safety Rules Added

- JARVIS-OS is a controlled assistant project.
- The user is the owner and final controller.
- ChatGPT is the architect and task planner.
- Codex is only the implementation assistant.
- Codex must execute only approved tasks.
- Codex must not make architecture decisions independently.
- Codex must not delete existing features.
- Codex must not rewrite existing modules unless explicitly approved.
- Codex must not create unrelated files.
- Codex must not modify forbidden folders or files named by a task.
- Codex must keep changes small, reviewable, and testable.
- Codex must preserve backwards compatibility.
- Codex must not enable unsafe automation, always-on microphone listening,
  automatic downloads, automatic installs, or destructive actions unless
  explicitly approved.
- Codex must run relevant tests when possible.
- Codex must provide exact manual verification commands.
- Codex must show changed files.
- Codex must not commit or push automatically.
- If tests fail, Codex must stop and report the failure instead of hiding it.
- If a task requires architecture changes, Codex must stop and ask for approval.
- If user instructions conflict with project safety rules, Codex must choose
  safety and ask for clarification.

## What Was Intentionally Not Changed

- No runtime behavior was changed.
- No voice recognition logic was changed.
- No core modules were changed.
- No forbidden folders or files were modified.
- No automatic downloads, installs, microphone listening, or destructive
  automation were enabled.
- No commit or push was performed.

## Verification Commands

```powershell
python -m pytest
.\scripts\health_check.ps1
```

## Expected Result

- `AGENTS.md` exists in the repository root.
- Codex has persistent project safety instructions.
- JARVIS-OS behavior is unchanged.
- The full test suite passes.
- Health check passes.
- Commit happens only after user verification.

## Commit Message Suggestion

```text
Add Codex project safety instructions
```
