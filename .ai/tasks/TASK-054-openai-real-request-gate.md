# TASK-054 - OpenAI Real Request Gate / One-Shot Network Permission

## Goal

Add a safe one-shot real OpenAI request gate using the existing `OpenAIProvider` adapter and `AIProviderRouter`.

## Context

TASK-053 completed the OpenAI provider adapter at stable commit `7864740` with message `Add OpenAI provider adapter`.

OpenAI remains disabled by default, `dry_run` remains default, and normal OpenAI prompts still do not call the network.

## Commands Added

- `статус openai one shot`
- `статус openai real request`
- `статус реального openai запроса`
- `openai реальный запрос: <текст>`
- `реальный openai запрос: <текст>`
- `openai one shot: <text>`

## Safety Boundaries

- Do not enable OpenAI permanently.
- Do not make OpenAI the default provider.
- Do not persist provider state, prompts, responses, or raw API responses.
- Do not print API key values.
- Do not send memory, profile, files, voice history, or logs automatically.
- Do not route AI output to `ActionRouter`.
- Do not add one-shot real request commands to the voice safe allowlist.
- Do not run network calls in tests.

## Tests

- `tests/unit/test_openai_request_gate.py`
- `tests/unit/test_openai_one_shot_smoke.py`
- `tests/unit/test_openai_provider.py`
- `tests/unit/test_command_processor.py`
- `tests/unit/test_voice_command_allowlist.py`

## Manual Verification Commands

```powershell
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
git status
```

Manual `run.py` without key:

```text
статус openai
статус openai one shot
проверить openai ключ
спроси ai: dry-run still works
спроси openai: это не должно идти в сеть
openai реальный запрос: привет, кто ты?
openai one shot: test
симулируй распознавание: статус openai one shot
симулируй распознавание: openai реальный запрос привет
ожидающая голосовая команда
нет
помощь
выход
```

## Expected Result

Without `OPENAI_API_KEY`, one-shot requests are not sent. With a key, only the explicit one-shot typed command can make one request through `OpenAIProvider` with `allow_network=True` for that call only.

`dry_run` remains default and OpenAI responses are never executed as commands.

## Commit Message Suggestion

`Add OpenAI one-shot request gate`
