# TASK-066 — Safe Automatic Fallback Execution / Controlled Provider Retry

## Goal

Add safe, explicit, controlled AI fallback execution mode.

## Context

TASK-065 completed the AI context privacy boundary. Stable commit:
`782dc2b` (`Add AI context privacy boundary`).

## User Requirements

- Fallback execution is explicit-only.
- Ordinary provider commands do not auto-retry.
- Privacy boundary, language policy, session pinning, provider gates, and
  consensus separation remain enforced.
- Provider responses are never executed as commands.
- Prompts, responses, secrets, files, memory, logs, screen, and audio are not
  stored or sent automatically.

## Files Changed

- `ai/provider_fallback_executor.py`
- `ai/__init__.py`
- `core/command_processor.py`
- `voice/voice_command_allowlist.py`
- `ai/provider_selection_policy.py`
- `tests/unit/test_ai_provider_fallback_executor.py`
- `tests/unit/test_command_processor.py`
- `tests/unit/test_voice_command_allowlist.py`
- `tests/unit/test_ai_provider_selection_policy.py`
- `docs/AI_PROVIDER_FALLBACK_EXECUTION.md`
- Related AI provider docs
- `.ai/CHECKPOINT.md`

## Commands Added

- `статус ai fallback execution`
- `статус ai retry`
- `статус fallback ai`
- `статус безопасного fallback`
- `статус ai fallback executor`
- `план ai fallback: <text>`
- `план fallback ai: <text>`
- `ai fallback plan: <text>`
- `показать ai fallback: <text>`
- `fallback ai запрос: <text>`
- `ai fallback запрос: <text>`
- `безопасный fallback ai: <text>`
- `controlled ai retry: <text>`
- `ai retry запрос: <text>`

## Safety Boundaries

- No automatic fallback for ordinary provider commands.
- No external provider default.
- No privacy or language bypass.
- No consensus invocation.
- No prompt/response persistence.
- No secret echo.
- No response execution.
- No model pull/install/download/payment automation.

## Tests

Run:

```powershell
python -m pytest tests/unit/test_ai_provider_fallback_executor.py
python -m pytest tests/unit/test_command_processor.py
python -m pytest tests/unit/test_voice_command_allowlist.py
python -m pytest tests/unit/test_ai_provider_selection_policy.py
python -m pytest tests/unit/test_ai_context_privacy_policy.py
python -m pytest
.\scripts\health_check.ps1
git diff --check
git status
```

## Manual Verification

Run `python run.py` without external keys and verify status, plan, and explicit
fallback commands. Private prompts should avoid external providers. Secret
prompts should redact secrets and block real/local providers. Voice fallback
status should auto-execute; plan and execute should require confirmation.

## Expected Result

JARVIS can perform bounded explicit fallback execution safely, while dry_run
remains default and ordinary provider commands keep existing behavior.

## Commit Message Suggestion

Add safe AI fallback execution
