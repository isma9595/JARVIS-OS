# JARVIS-OS Checkpoint

- Project: JARVIS-OS
- Current stable stage: TASK-031 — Vosk Local Recognition Dry Run
- Last stable commit: d005f5e
- Last stable commit message: Add Vosk recognition dry run
- Next stage: TASK-032 — Command Smoke Test Polish
- Status for TASK-032: in progress

## Approved Workflow

ChatGPT plans -> User approves -> Codex executes -> User verifies -> Commit only after successful verification

## Verification Gates

1. JARVIS starts
2. Existing commands still work
3. New task result exists
4. Tests pass
5. User confirms the result

## Notes

TASK-031 is the current stable stage.

TASK-032 is command polish based on live run.py smoke test; no real recognition
or microphone capture should be enabled.

JARVIS remains Russian-first for user-facing functionality, with future
multilingual switching planned.
