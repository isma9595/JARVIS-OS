# JARVIS-OS Checkpoint

- Project: JARVIS-OS
- Current stable stage: TASK-037 — First Real One-Shot Vosk Recognition
- Last stable commit: f0d429b
- Last stable commit message: Fix one-shot Vosk audio payload extraction
- Next stage: TASK-037A — Audio Capture Dependency Readiness
- Status: in progress

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

TASK-037 allows real microphone capture only after an explicit one-shot recognition command. It must not enable continuous listening, background listeners, cloud audio, automatic command execution, downloads, installs, or model commits.

TASK-037A is diagnostics only. It must not install packages automatically and must not change microphone safety behavior.

JARVIS remains Russian-first for user-facing functionality, with future multilingual switching planned.
