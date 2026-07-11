# JARVIS-OS Checkpoint

- Project: JARVIS-OS
- Current stable stage: TASK-028 — Vosk Model Setup and Local Recognition Gate
- Last stable commit: 19a7c59
- Last stable commit message: Add Vosk recognition gate
- Next stage: TASK-029 — Vosk Manual Setup Commands
- TASK-029 status: in progress

## Approved Workflow

ChatGPT plans -> User approves -> Codex executes -> User verifies -> Commit only after successful verification

## Verification Gates

1. JARVIS starts
2. Existing commands still work
3. New task result exists
4. Tests pass
5. User confirms the result

## Notes

TASK-028 is the current stable stage.

TASK-029 adds Russian-first manual Vosk setup/status commands. Vosk setup
commands must remain read-only and safe: they must not install packages,
download models, load models, start recognition, start microphone capture, or
change settings silently.

JARVIS remains Russian-first for user-facing functionality, with future
multilingual switching planned.
