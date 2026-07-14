# TASK-059 - GigaChat Provider Adapter / Russia-Friendly Fallback

## Goal

Add a safe GigaChat provider adapter behind `AIProviderRouter` as a
Russia-friendly fallback provider after Groq.

## Context

- Previous stable task: TASK-058C - Groq Python HTTP Transport Compatibility Fix.
- Stable commit: `ca51313`.
- Stable commit message: `Fix Groq Python transport compatibility`.

## Files Changed

- `ai/gigachat_cost_guard.py`
- `ai/gigachat_token_manager.py`
- `ai/gigachat_request_gate.py`
- `ai/providers/gigachat_provider.py`
- `ai/provider_config_manager.py`
- `ai/provider_router.py`
- `core/command_processor.py`
- `voice/voice_command_allowlist.py`
- `config/ai_providers.example.json`
- `docs/GIGACHAT_PROVIDER_ADAPTER.md`
- `docs/AI_PROVIDER_ROUTER.md`
- `docs/AI_PROVIDER_CONFIGURATION.md`
- `docs/GROQ_PROVIDER_ADAPTER.md`
- `tests/unit/test_gigachat_*.py`
- Existing AI provider/router/command/voice tests.

## Commands Added

- `статус gigachat`
- `статус гигачат`
- `статус сбер ai`
- `проверить gigachat ключ`
- `проверить гигачат ключ`
- `проверить сбер ключ`
- `статус gigachat token`
- `статус gigachat guard`
- `лимиты gigachat`
- `gigachat модель`
- `статус gigachat request shape`
- `спроси gigachat: <текст>`
- `гигачат: <текст>`
- `спроси сбер: <текст>`
- `gigachat реальный запрос: <текст>`
- `сбер реальный запрос: <текст>`
- `gigachat one shot: <текст>`

## Safety Boundaries

- GigaChat remains disabled by default.
- `dry_run` remains default.
- Real requests are explicit one-shot only.
- Auth key and OAuth token values are never printed.
- Tokens are cached in memory only.
- Prompts, responses, files, memory, profile, logs, and voice history are not
  sent automatically.
- AI responses are not executed as commands.
- Tests use fake clients only.

## Tests

Run:

```powershell
python -m pytest tests/unit/test_gigachat_cost_guard.py
python -m pytest tests/unit/test_gigachat_token_manager.py
python -m pytest tests/unit/test_gigachat_provider.py
python -m pytest tests/unit/test_gigachat_request_gate.py
python -m pytest tests/unit/test_gigachat_one_shot_smoke.py
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

Inside JARVIS:

```text
статус gigachat
проверить gigachat ключ
статус gigachat token
статус gigachat guard
лимиты gigachat
gigachat модель
статус gigachat request shape
спроси gigachat: это не должно идти в сеть
gigachat реальный запрос: привет, кто ты?
спроси ai: dry-run still works after GigaChat adapter
выход
```

Expected without key:

- Key status is `MISSING`.
- No auth key or token value is printed.
- Normal GigaChat ask does not call the network.
- One-shot refuses safely without `GIGACHAT_AUTH_KEY`.
- `dry_run` still works.

## Optional Real-Key Test

Use placeholders only:

```powershell
$env:GIGACHAT_AUTH_KEY = "PASTE_TEMPORARY_AUTH_KEY_HERE"
$env:GIGACHAT_MODEL = "GigaChat"
$env:GIGACHAT_SCOPE = "GIGACHAT_API_PERS"
python run.py
```

Then:

```text
gigachat реальный запрос: Ответь одним коротким предложением на русском: подключение работает?
выход
```

Cleanup:

```powershell
Remove-Item Env:GIGACHAT_AUTH_KEY
Remove-Item Env:GIGACHAT_MODEL
Remove-Item Env:GIGACHAT_SCOPE
```

## Commit Message Suggestion

`Add GigaChat provider adapter`
