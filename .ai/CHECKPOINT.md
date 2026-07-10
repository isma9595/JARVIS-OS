# JARVIS-OS Checkpoint

- Project: JARVIS-OS
- Current stable stage: TASK-026 — Microphone Mode Commands
- Last stable commit: 96a5989
- Last stable commit message: Add microphone mode commands
- Next stage: TASK-027 — One-Shot Microphone Capture
- TASK-027 status: in progress

## Approved Workflow

ChatGPT plans -> User approves -> Codex executes -> User verifies -> Commit only after successful verification

## Verification Gates

1. JARVIS starts
2. Existing commands still work
3. New task result exists
4. Tests pass
5. User confirms the result

## Notes

TASK-026 is the current stable stage.

TASK-027 adds a safe one-shot microphone capture foundation. One-shot
microphone capture must remain explicit, bounded, and non-continuous. It must
not enable real startup capture, always-on listening, continuous recognition,
Vosk activation, automatic downloads, or automatic installs.

JARVIS remains Russian-first for user-facing functionality, with future
multilingual switching planned.
