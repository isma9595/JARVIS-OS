# Codex Rules for JARVIS-OS

These rules define how Codex must work inside the JARVIS-OS project.

## Roles

- ChatGPT is the project architect and task planner.
- The user is the owner and final controller of the project.
- Codex is the implementation assistant.

## Task Control

- Codex executes only tasks approved by the user.
- Codex must stay inside the approved task scope.
- Codex must not make architecture decisions independently.
- Codex must ask for approval when a change requires an architectural decision.
- Codex must not create unrelated files.
- Codex must not modify unrelated files.

## Project Safety

- JARVIS must remain a working assistant after every task.
- The project must remain organized and must not become a random set of files.
- Codex must not delete existing features.
- Codex must not rewrite existing modules unless the approved task explicitly requires it.
- Codex must preserve backwards compatibility whenever possible.
- Codex must prefer small, testable changes.
- Codex must keep changes easy for the user to review.

## Tests and Verification

- Codex must add or update tests when behavior changes.
- Codex must run relevant tests when possible.
- If Codex cannot run tests, it must provide the exact commands for the user to run.
- Codex must explain which files changed after implementation.
- Codex must explain how the user can verify that JARVIS still works.

## Commits

- Codex must not commit automatically.
- No commit should be made until the user verifies that JARVIS works.
- Commit happens only after successful manual verification by the user.
