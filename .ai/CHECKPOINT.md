# JARVIS-OS Checkpoint

- Current stable stage: TASK-060 — AI Provider Language Policy / Russian-First Responses
- Last stable commit: 61c10da
- Next stage: TASK-061 — AI Provider Session Pinning / Manual Model Selection
- Status: in progress

## Approved Workflow

ChatGPT plans -> User approves -> Codex executes -> User verifies -> Commit only after successful verification

## Verification Gates

1. JARVIS starts
2. Existing commands still work
3. New task result exists
4. Tests pass
5. User confirms the result
