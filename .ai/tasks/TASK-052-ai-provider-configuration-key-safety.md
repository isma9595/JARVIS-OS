# TASK-052 — AI Provider Configuration / API Key Safety Layer

## Goal

Add a safe AI provider configuration and API key safety layer for future external providers such as Groq and Gemini, without making real external API calls.

## Context

TASK-051 completed the AI provider contracts and offline router foundation. Stable commit:

- `e16a1d4`
- `Add AI provider router foundation`

TASK-052 keeps `dry_run` as the only active provider and adds readiness reporting for future providers.

## Files Changed

- `ai/provider_config.py`
- `ai/provider_config_manager.py`
- `ai/provider_router.py`
- `ai/__init__.py`
- `core/command_processor.py`
- `voice/voice_command_allowlist.py`
- `config/ai_providers.example.json`
- `.gitignore`
- `docs/AI_PROVIDER_CONFIGURATION.md`
- `docs/AI_PROVIDER_ROUTER.md`
- tests under `tests/unit/`

## Commands Added

- `статус ai конфигурации`
- `статус ai ключей`
- `конфигурация ai провайдеров`
- `безопасность ai ключей`
- `проверить groq ключ`
- `проверить gemini ключ`

## Safety Boundaries

- No network calls.
- No real Groq/Gemini/OpenAI adapters.
- No API keys required.
- No full key values printed or logged.
- No prompts/responses persisted by this layer.
- No AI output execution.
- No AI connection to shell, files, email, browser, internet, automation, or continuous microphone listening.

## Tests

- `tests/unit/test_ai_provider_config.py`
- `tests/unit/test_ai_provider_config_manager.py`
- `tests/unit/test_command_processor.py`
- `tests/unit/test_voice_command_allowlist.py`
- `tests/unit/test_ai_provider_router.py`

## Manual Verification Commands

```powershell
python -m pytest tests/unit/test_ai_provider_config.py
python -m pytest tests/unit/test_ai_provider_config_manager.py
python -m pytest tests/unit/test_ai_provider_contracts.py
python -m pytest tests/unit/test_dry_run_ai_provider.py
python -m pytest tests/unit/test_ai_provider_router.py
python -m pytest tests/unit/test_command_processor.py
python -m pytest tests/unit/test_voice_command_allowlist.py
python -m pytest tests/unit/test_ai_provider_router_smoke.py
python -m pytest tests/unit/test_voice_cycle_smoke.py
python -m pytest
.\scripts\health_check.ps1
git status
```

Manual `run.py` commands:

- `статус ai`
- `статус ai конфигурации`
- `статус ai ключей`
- `конфигурация ai провайдеров`
- `безопасность ai ключей`
- `проверить groq ключ`
- `проверить gemini ключ`
- `список ai провайдеров`
- `спроси ai: тест после слоя конфигурации`
- `симулируй распознавание: статус ai ключей`
- `симулируй распознавание: проверить groq ключ`
- `симулируй распознавание: установить groq ключ abc123`
- `ожидающая голосовая команда`
- `нет`
- `помощь`
- `выход`

## Expected Result

- `dry_run` remains active.
- Groq and Gemini are disabled by default.
- Key status is shown safely as `PRESENT`, `MISSING`, or `NOT_REQUIRED`.
- No key values are displayed.
- No network calls are made.
- Voice safe status/key-check commands can auto-execute.
- Voice command to set a key is not allowlisted.

## Commit Message Suggestion

`Add AI provider config safety layer`
