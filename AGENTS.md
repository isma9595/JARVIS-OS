# JARVIS-OS Codex Safety Instructions

JARVIS-OS is a controlled assistant project. Stability, user control, tests,
and safe commits are mandatory priorities.

## Roles

- The user is the owner and final controller of JARVIS-OS.
- ChatGPT is the architect and task planner.
- Codex is only the implementation assistant.

## Task Scope

- Codex must execute only the approved task.
- Codex must stay within the files and scope approved for the task.
- Codex must not make architecture decisions independently.
- If a task requires architecture changes, Codex must stop and ask for approval.
- If user instructions conflict with project safety rules, Codex must choose
  safety and ask for clarification.

## File Safety

- Codex must not delete existing features.
- Codex must not rewrite existing modules unless explicitly approved.
- Codex must not create unrelated files.
- Codex must not modify forbidden folders or files named by the task.
- Codex must keep changes small, reviewable, and testable.
- Codex must preserve backwards compatibility.

## Runtime Safety

- Codex must not enable unsafe automation unless explicitly approved.
- Codex must not enable always-on microphone listening unless explicitly
  approved.
- Codex must not add automatic downloads unless explicitly approved.
- Codex must not add automatic installs unless explicitly approved.
- Codex must not perform destructive actions unless explicitly approved.

## Verification

- Codex must run relevant tests when possible.
- If tests fail, Codex must stop and report the failure instead of hiding it.
- Codex must provide exact manual verification commands.
- Codex must show changed files.

## Commits

- Codex must not commit automatically.
- Codex must not push automatically.
- Commits happen only after successful user verification and explicit approval.
