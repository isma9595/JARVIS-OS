# JARVIS-OS Checkpoint

- Project: JARVIS-OS
- Current stable stage: TASK-024 - Codex Safety Instructions
- Last stable commit: 267d2c8
- Last stable commit message: Add Codex project safety instructions
- Next stage: TASK-025 - Microphone Listening Modes
- TASK-025 status: in progress

## Approved Workflow

ChatGPT plans -> User approves -> Codex executes -> User verifies -> Commit only after successful verification

## Verification Gates

1. JARVIS starts
2. Existing commands still work
3. New task result exists
4. Tests pass
5. User confirms the result

## Notes

TASK-024 is the current stable stage.

TASK-025 is limited to safe microphone listening mode state, documentation, and
tests. It must not enable real microphone capture, background listeners,
continuous recognition, Vosk activation, command processing changes, or
forbidden folders and files.
