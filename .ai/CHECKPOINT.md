# JARVIS-OS Checkpoint

- Project: JARVIS-OS
- Current stable stage: TASK-030 — Vosk Model Path Configuration Commands
- Last stable commit: bf01091
- Last stable commit message: Add Vosk model path commands
- Next stage: TASK-031 — Vosk Local Recognition Dry Run
- TASK-031 status: in progress

## Approved Workflow

ChatGPT plans -> User approves -> Codex executes -> User verifies -> Commit only after successful verification

## Verification Gates

1. JARVIS starts
2. Existing commands still work
3. New task result exists
4. Tests pass
5. User confirms the result

## Notes

TASK-030 is the current stable stage.

TASK-031 adds a safe Vosk local recognition dry run. Vosk dry run must remain
fake/stub-based, explicit, and must not start microphone capture or real
recognition.

JARVIS remains Russian-first for user-facing functionality, with future
multilingual switching planned.
