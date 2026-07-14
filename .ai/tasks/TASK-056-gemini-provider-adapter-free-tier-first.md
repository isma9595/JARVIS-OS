# TASK-056 - Gemini Provider Adapter / Free-Tier First

## Goal

Add a safe Gemini provider adapter behind `AIProviderRouter`, prepared for Gemini API free-tier testing, without enabling Gemini permanently and without making real network calls in tests.

## Context

- TASK-055 is the current stable stage.
- Last stable commit: `d1d1dcd`
- Last stable commit message: `Add OpenAI model and cost guard`
- `dry_run` remains the default provider.
- OpenAI remains optional and unchanged.

## Files Changed

- `ai/gemini_cost_guard.py`
- `ai/providers/gemini_provider.py`
- `ai/gemini_request_gate.py`
- `ai/__init__.py`
- `ai/provider_config_manager.py`
- `ai/provider_router.py`
- `ai/providers/__init__.py`
- `core/command_processor.py`
- `voice/voice_command_allowlist.py`
- `config/ai_providers.example.json`
- `docs/GEMINI_PROVIDER_ADAPTER.md`
- `docs/AI_PROVIDER_ROUTER.md`
- `docs/AI_PROVIDER_CONFIGURATION.md`
- `.ai/CHECKPOINT.md`
- new and updated unit tests under `tests/unit/`

## Commands Added

- `статус gemini`
- `статус джемини`
- `проверить gemini ключ`
- `проверить ключ gemini`
- `статус gemini guard`
- `статус gemini cost guard`
- `лимиты gemini`
- `gemini модель`
- `gemini model`
- `спроси gemini: <текст>`
- `gemini: <текст>`
- `gemini реальный запрос: <текст>`
- `реальный gemini запрос: <текст>`
- `gemini one shot: <текст>`

## Safety Boundaries

- Gemini is not enabled permanently.
- Gemini is not the default provider.
- `dry_run` remains default.
- OpenAI support remains.
- Tests use fake clients only.
- No tests require `GEMINI_API_KEY`.
- API key values are not printed or persisted.
- Memory, profile, files, logs, and voice history are not sent automatically.
- Gemini output is not executed as a command.
- Voice allowlist includes only read-only Gemini status/key/guard/model commands.

## Verification

```powershell
python -m pytest tests/unit/test_gemini_cost_guard.py
python -m pytest tests/unit/test_gemini_provider.py
python -m pytest tests/unit/test_gemini_request_gate.py
python -m pytest tests/unit/test_gemini_one_shot_smoke.py
python -m pytest tests/unit/test_ai_provider_config.py
python -m pytest tests/unit/test_ai_provider_config_manager.py
python -m pytest tests/unit/test_ai_provider_router.py
python -m pytest tests/unit/test_command_processor.py
python -m pytest tests/unit/test_voice_command_allowlist.py
```

## Manual Verification Without Key

```powershell
python run.py
```

Inside JARVIS:

```text
статус gemini
проверить gemini ключ
статус gemini guard
лимиты gemini
gemini модель
спроси gemini: это не должно идти в сеть
gemini реальный запрос: привет, кто ты?
gemini one shot: test
спроси ai: dry-run still works after Gemini adapter
статус openai
статус openai guard
помощь
выход
```

## Optional Real-Key Test

```powershell
$env:GEMINI_API_KEY = "PASTE_TEMPORARY_KEY_HERE"
$env:GEMINI_MODEL = "gemini-2.5-flash-lite"
python run.py
```

Inside JARVIS:

```text
статус gemini
статус gemini guard
gemini реальный запрос: Ответь одним коротким предложением на русском: подключение работает?
выход
```

After exit:

```powershell
Remove-Item Env:GEMINI_API_KEY
Remove-Item Env:GEMINI_MODEL
```

## Expected Result

- Gemini status is safe and offline.
- Key checks show only `PRESENT` or `MISSING`.
- Safe Gemini ask does not call network.
- Explicit Gemini one-shot calls network only when key, model, prompt length, and output token guard pass.
- Gemini is not persisted as enabled.
- `dry_run` remains default.
- AI responses are not executed as commands.

## Commit Message Suggestion

`Add Gemini provider adapter`
