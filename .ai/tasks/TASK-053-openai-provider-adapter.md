# TASK-053 — OpenAI Provider Adapter / Responses API

## Goal

Add a safe OpenAI provider adapter behind `AIProviderRouter` using the OpenAI Responses API pattern, without real network calls during tests and without enabling OpenAI by default.

## Context

TASK-052 completed the AI provider configuration and API key safety layer.

- Last stable commit: `29e422c`
- Last stable commit message: `Add AI provider config safety layer`
- `dry_run` remains active and default.

## Files Changed

- `ai/provider_config_manager.py`
- `ai/provider_router.py`
- `ai/providers/openai_provider.py`
- `ai/providers/__init__.py`
- `ai/__init__.py`
- `config/ai_providers.example.json`
- `core/command_processor.py`
- `voice/voice_command_allowlist.py`
- `tests/unit/test_openai_provider.py`
- `tests/unit/test_openai_provider_adapter_smoke.py`
- Existing AI config/router/command/voice tests
- `docs/OPENAI_PROVIDER_ADAPTER.md`
- `docs/AI_PROVIDER_CONFIGURATION.md`
- `docs/AI_PROVIDER_ROUTER.md`
- `.ai/CHECKPOINT.md`

## Commands Added

- `статус openai`
- `статус опенай`
- `openai status`
- `проверить openai ключ`
- `проверить ключ openai`
- `спроси openai: <текст>`
- `openai: <текст>`

## Safety Boundaries

- OpenAI is disabled by default.
- Network is disabled by default.
- Tests use fake HTTP clients only.
- `OPENAI_API_KEY` is checked by presence only.
- API key values are never printed.
- AI output is not routed to `ActionRouter`.
- AI output does not execute commands.
- Voice allowlist includes only OpenAI status and key-check commands.

## Tests

- Provider info/capability checks
- Disabled/missing-key/network-disabled errors
- Fake Responses API request mapping
- Response parsing
- HTTP/network/JSON parse safe errors
- Config/key status safety
- Router default remains `dry_run`
- CommandProcessor OpenAI status/key/ask commands
- Voice allowlist OpenAI read-only policy

## Manual Verification Commands

```powershell
python -m pytest tests/unit/test_openai_provider.py
python -m pytest tests/unit/test_ai_provider_config.py
python -m pytest tests/unit/test_ai_provider_config_manager.py
python -m pytest tests/unit/test_ai_provider_router.py
python -m pytest tests/unit/test_command_processor.py
python -m pytest tests/unit/test_voice_command_allowlist.py
python -m pytest tests/unit/test_ai_provider_router_smoke.py
python -m pytest
.\scripts\health_check.ps1
git status
```

## Expected Result

- `dry_run` remains default and active.
- OpenAI is visible as configured/disabled.
- `OPENAI_API_KEY` status is `PRESENT` or `MISSING` without printing the value.
- `спроси openai` does not call network by default.
- Voice OpenAI prompt commands require confirmation and still do not make a request.

## Commit Message Suggestion

`Add OpenAI provider adapter`
