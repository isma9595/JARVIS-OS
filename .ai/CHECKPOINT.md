# JARVIS-OS Checkpoint

- Project: JARVIS-OS
- Current stable stage: TASK-023 - Real Vosk Speech Recognition Bootstrap
- Last stable commit: 99de2db
- Last stable commit message: Add Vosk readiness bootstrap
- Next stage: TASK-024 - Codex Safety Instructions
- TASK-024 status: in progress

## Approved Workflow

ChatGPT plans -> User approves -> Codex executes -> User verifies -> Commit only after successful verification

## Verification Gates

1. JARVIS starts
2. Existing commands still work
3. New task result exists
4. Tests pass
5. User confirms the result

## Notes

TASK-023 is the current stable stage.

TASK-024 is limited to project-level Codex safety instructions and checkpoint
documentation. It must not change runtime behavior, voice recognition logic,
core modules, or forbidden folders and files.
