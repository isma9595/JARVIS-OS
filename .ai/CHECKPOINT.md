# JARVIS-OS Checkpoint

- Project: JARVIS-OS
- Current stable stage: TASK-052 — AI Provider Configuration / API Key Safety Layer
- Last stable commit: 29e422c
- Last stable commit message: Add AI provider config safety layer
- Next stage: TASK-053 — OpenAI Provider Adapter / Responses API
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

TASK-050 is complete and stable at commit 9a5bc6b.

TASK-050A is complete and stable at commit a63af4f.

TASK-051 is complete and stable at commit e16a1d4.

TASK-052 is complete and stable at commit 29e422c.

TASK-053 is in progress for the OpenAI provider adapter / Responses API, disabled by default with no real network calls in tests.
