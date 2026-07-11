# JARVIS-OS Checkpoint

- Project: JARVIS-OS
- Current stable stage: TASK-029 — Vosk Manual Setup Commands
- Last stable commit: 97cb6ec
- Last stable commit message: Add Vosk manual setup commands
- Next stage: TASK-030 — Vosk Model Path Configuration Commands
- TASK-030 status: in progress

## Approved Workflow

ChatGPT plans -> User approves -> Codex executes -> User verifies -> Commit only after successful verification

## Verification Gates

1. JARVIS starts
2. Existing commands still work
3. New task result exists
4. Tests pass
5. User confirms the result

## Notes

TASK-029 is the current stable stage.

TASK-030 adds Russian-first Vosk model path configuration commands. Vosk model
path commands must remain configuration-only and must not install, download,
load models, start recognition, or start microphone capture.

JARVIS remains Russian-first for user-facing functionality, with future
multilingual switching planned.
