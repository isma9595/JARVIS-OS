# OpenAI One-Shot Request Gate

## Purpose

TASK-054 adds a safe, explicit one-shot gate for real OpenAI requests. The gate exists so a typed command can make exactly one request through the existing `OpenAIProvider` adapter without enabling OpenAI permanently.

## One-Shot Model

- OpenAI remains disabled by default in provider configuration.
- `dry_run` remains the default AI provider.
- A real request is allowed only by an explicit typed command:
  - `openai реальный запрос: <текст>`
  - `реальный openai запрос: <текст>`
  - `openai one shot: <text>`
- `спроси openai: <текст>` and `openai: <текст>` still return a safe no-network message.
- The gate creates a temporary enabled OpenAI config only for the single request.
- The temporary enabled state is not persisted.

## API Key

OpenAI uses `OPENAI_API_KEY` from the environment.

The key must be set outside the repository. JARVIS reports only `PRESENT` or `MISSING`; the key value is never printed, committed, logged, or written to disk.

Do not paste the key into a JARVIS command.

## Privacy And Execution Boundaries

- No memory, user profile, local files, voice history, or logs are sent automatically.
- Prompts and responses are not persisted by default.
- Raw API responses are not saved to disk.
- The response is returned as plain text.
- The response is not executed as a command and is not routed to `ActionRouter`.
- No streaming, tools, file uploads, background calls, or continuous listening are enabled.

## Status Command

Use:

```text
статус openai one shot
```

The status reports whether the one-shot gate can request now, whether `OPENAI_API_KEY` is `PRESENT` or `MISSING`, that OpenAI is not permanently enabled, and that `dry_run` remains default.

## Manual Real-Key Test

Only run this intentionally. Real API usage may incur cost and requires network access.

```powershell
$env:OPENAI_API_KEY = "paste-key-here-temporarily"
python run.py
openai реальный запрос: Ответь одним коротким предложением на русском: ты подключен?
выход
Remove-Item Env:OPENAI_API_KEY
```

Do not write the key into any file. Do not paste the key into chat logs. Do not commit the key.

## Tests

Unit tests use fake HTTP clients only. They do not require `OPENAI_API_KEY` and do not make network calls.

```powershell
python -m pytest tests/unit/test_openai_request_gate.py
python -m pytest tests/unit/test_openai_one_shot_smoke.py
python -m pytest tests/unit/test_openai_provider.py
python -m pytest tests/unit/test_command_processor.py
python -m pytest tests/unit/test_voice_command_allowlist.py
```

## Future

- Provider enable/disable controls
- Model selection
- Cost and rate limit guard
- Prompt safety and context policy

## TASK-055 Model And Cost Guard Update

TASK-055 adds `OpenAIRequestCostGuard` before the real one-shot request. The guard resolves the model from `OPENAI_MODEL` when present and safe, otherwise uses `gpt-5.6`; enforces a 1200 character prompt limit; sets `max_output_tokens` to 128; and keeps a hard cap of 512.

The one-shot Responses API body is limited to `model`, `input`, and guarded `max_output_tokens`. No memory, profile, files, logs, tools, streaming, or previous response context are added.

Additional read-only commands:

```text
статус openai guard
статус openai cost guard
лимиты openai
лимит openai запроса
openai guard status
openai модель
openai model
```

Manual verification should use temporary local PowerShell environment variables only:

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

Real API usage may consume account credits or limits. Do not paste the key into chat, JARVIS commands, files, tests, or commits.
