# TASK-051 - AI Provider Core Contracts / Router Foundation

## Goal

Start the AI Brain / Provider Router Foundation cycle with safe, modular AI provider contracts and a deterministic offline dry-run router.

## Context

TASK-050A - Manual Voice Command Polish is the current stable stage.

- Last stable commit: `a63af4f`
- Last stable commit message: `Polish manual voice commands`

## Files Changed

- `ai/__init__.py`
- `ai/provider_contracts.py`
- `ai/provider_router.py`
- `ai/providers/__init__.py`
- `ai/providers/dry_run_provider.py`
- `core/command_processor.py`
- `voice/voice_command_allowlist.py`
- `docs/AI_PROVIDER_ROUTER.md`
- `.ai/CHECKPOINT.md`
- `tests/unit/test_ai_provider_contracts.py`
- `tests/unit/test_dry_run_ai_provider.py`
- `tests/unit/test_ai_provider_router.py`
- `tests/unit/test_ai_provider_router_smoke.py`
- `tests/unit/test_command_processor.py`
- `tests/unit/test_voice_command_allowlist.py`

## Commands Added

- `статус ai`
- `статус ии`
- `статус искусственного интеллекта`
- `статус ai провайдеров`
- `статус ии провайдеров`
- `ai status`
- `список ai провайдеров`
- `список ии провайдеров`
- `ai провайдеры`
- `ии провайдеры`
- `провайдеры ai`
- `спроси ai: <текст>`
- `спроси ии: <текст>`
- `ai: <текст>`
- `ии: <текст>`
- `ai кратко: <текст>`
- `ии кратко: <текст>`
- `ai резюме: <текст>`
- `ии резюме: <текст>`
- `ai классифицируй: <текст>`
- `ии классифицируй: <текст>`

## Safety Boundaries

- No real Groq, Gemini, OpenAI, or other external API calls.
- No network requests.
- No API key reads.
- No package installs or downloads.
- No autonomous execution.
- AI responses are not executed as commands.
- AI output does not bypass `CommandProcessor` or `ActionRouter`.
- AI is not connected to files, shell, email, browser, internet, local memory, user profile, voice history, or continuous microphone listening.
- Voice allowlist includes only read-only AI status/provider-list commands, not broad prompt commands.

## Tests

- `tests/unit/test_ai_provider_contracts.py`
- `tests/unit/test_dry_run_ai_provider.py`
- `tests/unit/test_ai_provider_router.py`
- `tests/unit/test_ai_provider_router_smoke.py`
- Updated command processor and voice allowlist tests.

## Manual Verification Commands

```powershell
python -m pytest tests/unit/test_ai_provider_contracts.py
python -m pytest tests/unit/test_dry_run_ai_provider.py
python -m pytest tests/unit/test_ai_provider_router.py
python -m pytest tests/unit/test_command_processor.py
python -m pytest tests/unit/test_voice_command_allowlist.py
python -m pytest tests/unit/test_voice_cycle_smoke.py
python -m pytest tests/unit/test_voice_cycle_status.py
python -m pytest
.\scripts\health_check.ps1
git status
python run.py
```

Manual `run.py` checks:

- `статус ai`
- `статус ии`
- `список ai провайдеров`
- `список ии провайдеров`
- `спроси ai: привет, кто ты?`
- `ai: объясни что такое dry-run режим`
- `ai кратко: Это длинный тестовый текст. Он нужен только для проверки локального сокращения без внешнего провайдера.`
- `ai классифицируй: python код для теста`
- `симулируй распознавание: статус ai`
- `симулируй распознавание: спроси ai привет`
- `ожидающая голосовая команда`
- `нет`
- `помощь`
- `выход`

## Expected Result

- `dry_run` is the only active AI provider.
- Status/list commands show offline deterministic router state.
- Ask/summarize/classify commands work offline.
- No network or API keys are required.
- AI answers are never executed as commands.
- Broad AI voice queries are not safe-allowlisted.
- Tests and health check pass.

## Commit Message Suggestion

`Add AI provider router foundation`
