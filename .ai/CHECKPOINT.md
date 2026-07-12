# JARVIS-OS Checkpoint

- Project: JARVIS-OS
- Current stable stage: TASK-034 — One-Shot Capture to Vosk Recognition Bridge
- Last stable commit: 6d707f7
- Last stable commit message: Add one-shot Vosk recognition bridge
- Next stage: TASK-035 — Vosk Model Installation & Readiness Verification
- Status for TASK-035: in progress

## Approved Workflow

ChatGPT plans -> User approves -> Codex executes -> User verifies -> Commit only after successful verification

## Verification Gates

1. JARVIS starts
2. Existing commands still work
3. New task result exists
4. Tests pass
5. User confirms the result

## Notes

TASK-035 adds safe manual Vosk model installation guidance and readiness verification only. It must not enable real recognition, microphone capture, model loading, downloads, installs, cloud audio, continuous listening, or command execution from recognized text.

JARVIS remains Russian-first for user-facing functionality, with future multilingual switching planned.
