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
