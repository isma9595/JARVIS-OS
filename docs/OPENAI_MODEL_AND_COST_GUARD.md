# OpenAI Model And Cost Guard

## Purpose

TASK-055 adds a model, prompt-size, output-token, and cost-warning guard around the existing OpenAI one-shot real request gate.

It does not enable OpenAI permanently, does not make OpenAI the default provider, and does not add multi-turn chat, memory sending, streaming, tools, or file upload.

## Guard Limits

- Model source: `OPENAI_MODEL` environment variable when present and safe; otherwise the default model.
- Default model: `gpt-5.6`
- Prompt length limit: 1200 characters.
- Default `max_output_tokens`: 128.
- Hard `max_output_tokens` cap: 512.
- Timeout: 30 seconds.

The guard rejects empty prompts, oversized prompts, empty model names, model names with spaces or path separators, very long model names, and model strings that look like API keys or long tokens.

## Cost Warning

Real OpenAI API calls may use paid credits or account limits.

TASK-055 does not calculate exact cost. Exact estimates require a tested pricing-table abstraction. The user-facing warning intentionally says the request may use account credits or limits rather than giving a dollar or ruble estimate.

## Manual Verification

Use a temporary PowerShell environment variable. Replace placeholders locally. Do not paste the key into JARVIS commands, chat logs, Markdown files, tests, or commits.

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

One short real request is enough. Manual real-key verification is optional and may use account credits or limits.

## Safety Boundaries

- API key values are never printed.
- API keys must not be committed or shared in plaintext.
- Prompts and responses are not saved by default.
- Raw API responses are not written to disk.
- The response is returned as text only and is not executed as a command.
- Memory, profile, local files, voice history, and logs are not sent automatically.
- `dry_run` remains the default provider after the one-shot request.

## Future

- Usage parsing if the API response includes usage data.
- Exact cost estimator after a tested pricing-table abstraction exists.
- Rate limit guard.
- Provider enable/disable settings.
