# TASK-058 — Groq Provider Adapter / Free-Tier Fallback

## Goal

Add a safe Groq provider adapter behind `AIProviderRouter` as the next free-tier fallback provider after Gemini free-tier availability was blocked by location.

## Context

- TASK-056 added the Gemini provider adapter.
- Stable commit before this task: `83b15da` (`Add Gemini provider adapter`).
- OpenAI remains optional/paid and live testing previously returned `429`.
- Gemini live testing returned a location availability error.
- Groq is added as disabled, explicit one-shot only.

## Files Changed

- `ai/groq_cost_guard.py`
- `ai/providers/groq_provider.py`
- `ai/groq_request_gate.py`
- `ai/provider_config_manager.py`
- `ai/provider_router.py`
- `ai/__init__.py`
- `core/command_processor.py`
- `voice/voice_command_allowlist.py`
- `config/ai_providers.example.json`
- Groq tests and provider docs

## Commands Added

- `статус groq`
- `статус грок`
- `проверить groq ключ`
- `проверить ключ groq`
- `статус groq guard`
- `статус groq cost guard`
- `лимиты groq`
- `groq модель`
- `groq model`
- `спроси groq: <text>`
- `groq: <text>`
- `groq реальный запрос: <text>`
- `реальный groq запрос: <text>`
- `groq one shot: <text>`

## Safety Boundaries

- Groq is not enabled permanently.
- Groq is not the default provider.
- `dry_run`, OpenAI, and Gemini support remain.
- Tests do not perform real network calls.
- `GROQ_API_KEY` is optional for tests and never printed.
- Local memory/profile/files/logs/workspace content are not sent automatically.
- Groq responses are not executed as commands.

## Tests

```powershell
python -m pytest tests/unit/test_groq_cost_guard.py
python -m pytest tests/unit/test_groq_provider.py
python -m pytest tests/unit/test_groq_request_gate.py
python -m pytest tests/unit/test_groq_one_shot_smoke.py
python -m pytest tests/unit/test_ai_provider_config.py
python -m pytest tests/unit/test_ai_provider_config_manager.py
python -m pytest tests/unit/test_ai_provider_router.py
python -m pytest tests/unit/test_command_processor.py
python -m pytest tests/unit/test_voice_command_allowlist.py
python -m pytest
.\scripts\health_check.ps1
git diff --check
git status
```

## Manual Verification Without Key

```powershell
python run.py
```

Expected result: Groq status is safe, key is `MISSING`, no network request is sent for normal Groq ask, one-shot refuses safely without a key, and `dry_run` still works.

## Optional Real-Key Test

Use placeholders only. Never commit a real key.

```powershell
$env:GROQ_API_KEY = "PASTE_TEMPORARY_KEY_HERE"
$env:GROQ_MODEL = "llama-3.1-8b-instant"
python run.py
Remove-Item Env:GROQ_API_KEY
Remove-Item Env:GROQ_MODEL
```

## Expected Result

Groq is available as a disabled external provider and explicit one-shot fallback. `dry_run` remains default. No keys leak. No AI output executes as a command.

## Commit Message Suggestion

Add Groq provider adapter
