# JARVIS-OS Checkpoint

- Project: JARVIS-OS
- Current stable stage: TASK-036 - Real Vosk Model Path Setup Manual Verification
- Last stable commit: 0817450
- Last stable commit message: Real Vosk Model Path Setup Manual Verification
- Next stage: TASK-037
- Status for TASK-037: not started

## Approved Workflow

ChatGPT plans -> User approves -> Codex executes -> User verifies -> Commit only after successful verification

## Verification Gates

1. JARVIS starts
2. Existing commands still work
3. New task result exists
4. Tests pass
5. User confirms the result

## Notes

TASK-036 keeps the real local Vosk model path as a user-controlled manual setting. It must not enable real recognition, microphone capture, model loading, downloads, installs, cloud audio, continuous listening, or command execution from recognized text.

TASK-036A fixes unit test isolation so tests do not depend on the user's local Vosk settings file.

JARVIS remains Russian-first for user-facing functionality, with future multilingual switching planned.
