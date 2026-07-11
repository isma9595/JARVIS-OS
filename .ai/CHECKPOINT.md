# JARVIS-OS Checkpoint

- Project: JARVIS-OS
- Current stable stage: TASK-027 — One-Shot Microphone Capture
- Last stable commit: 26c14b4
- Last stable commit message: Add one-shot microphone capture
- Next stage: TASK-028 — Vosk Model Setup and Local Recognition Gate
- TASK-028 status: in progress

## Approved Workflow

ChatGPT plans -> User approves -> Codex executes -> User verifies -> Commit only after successful verification

## Verification Gates

1. JARVIS starts
2. Existing commands still work
3. New task result exists
4. Tests pass
5. User confirms the result

## Notes

TASK-027 is the current stable stage.

TASK-028 adds safe Vosk model setup checks and a local recognition gate. Vosk
local recognition must remain gated by explicit setup checks and user
activation.

JARVIS remains Russian-first for user-facing functionality, with future
multilingual switching planned.
