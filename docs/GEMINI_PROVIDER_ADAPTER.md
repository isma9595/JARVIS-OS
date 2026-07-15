# Gemini Provider Adapter

## TASK-060 Language Policy

Gemini real one-shot prompts pass through the shared AI provider language policy before
the API request. The default is Russian-first, while explicit user language requests
and translation targets are respected. `dry_run` remains default, Gemini is not enabled
permanently, and no memory/profile/files/logs or secrets are added.

## Purpose

TASK-056 adds a safe Gemini adapter behind `AIProviderRouter` for controlled free-tier-first testing.

Gemini is disabled by default. `dry_run` remains the default AI provider.

## Free-Tier-First Safety

- Gemini API keys are created in Google AI Studio.
- Use `GEMINI_API_KEY` for the key.
- Optionally use `GEMINI_MODEL`; default is `gemini-2.5-flash-lite`.
- Free tier, quota, rate limits, and model availability may vary by account, region, and model.
- The key value is never printed.
- Prompts and responses are not saved by default.
- Raw API responses are not written to disk.
- Memory, profile, files, logs, and voice history are not sent automatically.
- Gemini output is returned as text and is not executed as a command.
- Tests use fake HTTP clients only and do not call Google network.

## Commands

- `статус gemini`
- `статус джемини`
- `проверить gemini ключ`
- `проверить ключ gemini`
- `статус gemini guard`
- `лимиты gemini`
- `gemini модель`
- `спроси gemini: <текст>`: safe no-network refusal
- `gemini: <текст>`: safe no-network refusal
- `gemini реальный запрос: <текст>`: explicit one-shot real request
- `реальный gemini запрос: <текст>`: explicit one-shot real request
- `gemini one shot: <текст>`: explicit one-shot real request

`спроси ai: <текст>` still uses `dry_run`.

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
выход
```

Expected without key:

- Gemini status shows `GEMINI_API_KEY` as `MISSING`.
- No key value is printed.
- Normal Gemini ask does not call the network.
- Gemini one-shot refuses safely without a key.
- `dry_run` still works.
- OpenAI commands still work as before.

## Optional Real-Key Test

This is optional and not required for task completion.

Do not paste a key into chat, JARVIS commands, tracked files, or docs.

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

## Troubleshooting

- Missing key: set `GEMINI_API_KEY` in the environment and restart JARVIS.
- Invalid model: unset `GEMINI_MODEL` or use a simple Gemini model name without spaces or path separators.
- Quota/rate limit: free tier limits may vary by account, region, and model.
- Network error: one-shot reports a safe network error without printing the key or raw response.

## TASK-058 Note

Gemini live checks may fail when Google API location or free-tier availability is blocked. In that case Groq is the next disabled, one-shot fallback candidate.
