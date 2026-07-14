# TASK-055 - OpenAI Real Request Manual Verification / Model & Cost Guard

## Goal

Add model, cost, prompt-size, output-token, and safe manual verification support for the existing OpenAI one-shot real request gate.

## Context

TASK-054 completed the OpenAI one-shot request gate at stable commit `443af1a` with commit message `Add OpenAI one-shot request gate`.

`dry_run` remains the default provider. OpenAI is not enabled permanently.

## Files Changed

- `ai/openai_cost_guard.py`
- `ai/openai_request_gate.py`
- `ai/providers/openai_provider.py`
- `ai/__init__.py`
- `core/command_processor.py`
- `voice/voice_command_allowlist.py`
- `tests/unit/test_openai_cost_guard.py`
- `tests/unit/test_openai_request_gate.py`
- `tests/unit/test_openai_provider.py`
- `tests/unit/test_openai_one_shot_smoke.py`
- `tests/unit/test_command_processor.py`
- `tests/unit/test_voice_command_allowlist.py`
- `docs/OPENAI_MODEL_AND_COST_GUARD.md`
- `docs/OPENAI_ONE_SHOT_REQUEST_GATE.md`
- `docs/OPENAI_PROVIDER_ADAPTER.md`
- `docs/AI_PROVIDER_CONFIGURATION.md`
- `docs/AI_PROVIDER_ROUTER.md`
- `.ai/CHECKPOINT.md`

## Commands Added

- `статус openai guard`
- `статус openai cost guard`
- `лимиты openai`
- `лимит openai запроса`
- `openai guard status`
- `openai модель`
- `openai model`

## Safety Boundaries

- OpenAI is not enabled permanently.
- OpenAI is not the default provider.
- Tests use fake clients and do not make real network calls.
- `OPENAI_API_KEY` is not required for tests.
- API key values are never printed.
- Prompts and responses are not saved by default.
- Raw API responses are not written to disk.
- Memory, profile, files, voice history, and logs are not sent automatically.
- AI output is not executed as a command.
- Voice real OpenAI prompt commands are not allowlisted.

## Tests

```powershell
python -m pytest tests/unit/test_openai_cost_guard.py
python -m pytest tests/unit/test_openai_request_gate.py
python -m pytest tests/unit/test_openai_provider.py
python -m pytest tests/unit/test_openai_one_shot_smoke.py
python -m pytest tests/unit/test_command_processor.py
python -m pytest tests/unit/test_voice_command_allowlist.py
python -m pytest tests/unit/test_ai_provider_router.py
python -m pytest tests/unit/test_ai_provider_config.py
python -m pytest tests/unit/test_ai_provider_config_manager.py
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
статус openai
статус openai one shot
статус openai guard
лимиты openai
openai модель
проверить openai ключ
спроси ai: dry-run still works after cost guard
спроси openai: это не должно идти в сеть
openai реальный запрос: привет, кто ты?
openai one shot: test
симулируй распознавание: статус openai guard
симулируй распознавание: лимиты openai
симулируй распознавание: openai реальный запрос привет
ожидающая голосовая команда
нет
помощь
выход
```

## Optional Real-Key Verification

Only if the user intentionally sets a local key. Do not paste the key into chat, JARVIS commands, files, tests, or commits.

```powershell
$env:OPENAI_API_KEY = "PASTE_TEMPORARY_KEY_HERE"
$env:OPENAI_MODEL = "gpt-5.6"
python run.py
```

Inside JARVIS:

```text
статус openai one shot
статус openai guard
openai реальный запрос: Ответь одним коротким предложением на русском: подключение работает?
выход
```

After exit:

```powershell
Remove-Item Env:OPENAI_API_KEY
Remove-Item Env:OPENAI_MODEL
```

Real request may use account credits or limits. One short test is enough.

## Expected Result

OpenAI one-shot requests show model, `max_output_tokens`, cost warning, and safety footer. Missing key, invalid model, and oversized prompt cases refuse before network calls. `dry_run` remains default.

## Commit Message Suggestion

`Add OpenAI model and cost guard`
