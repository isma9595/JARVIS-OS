# JARVIS-OS Checkpoint

- Project: JARVIS-OS
- Current stable stage: TASK-025 - Microphone Listening Modes
- Last stable commit: 9c5eae2
- Last stable commit message: Add microphone listening modes
- Next stage: TASK-026 - Microphone Mode Commands
- TASK-026 status: in progress

## Approved Workflow

ChatGPT plans -> User approves -> Codex executes -> User verifies -> Commit only after successful verification

## Verification Gates

1. JARVIS starts
2. Existing commands still work
3. New task result exists
4. Tests pass
5. User confirms the result

## Notes

TASK-025 is the current stable stage.

TASK-026 connects Russian-first text commands to the existing safe microphone
listening mode state. It must not enable real microphone capture, background
listeners, continuous recognition, Vosk activation, automatic downloads, or
automatic installs.

JARVIS remains Russian-first for user-facing functionality, with future
multilingual switching planned.
