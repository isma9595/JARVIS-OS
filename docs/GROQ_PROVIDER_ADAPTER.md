# Groq Provider Adapter

TASK-058 adds Groq as the next free-tier fallback candidate after Gemini live availability was blocked by location/free-tier access.

## Safety Model

- Groq is disabled by default.
- `dry_run` remains the default provider.
- Real Groq requests are explicit one-shot only.
- API keys are read only from environment variables.
- Key values are never printed, logged, or written to disk.
- Groq responses are returned as text and are not executed as commands.
- Memory, profile, files, logs, voice history, and workspace content are not sent automatically.
- Tests use fake clients only and do not make network calls.

## Configuration

- API key env var: `GROQ_API_KEY`
- Optional model env var: `GROQ_MODEL`
- Default model: `llama-3.1-8b-instant`
- Optional stronger model: `llama-3.3-70b-versatile`
- API base URL: `https://api.groq.com/openai/v1`
- Chat completions endpoint: `POST https://api.groq.com/openai/v1/chat/completions`

Create the key in Groq Console and set it only in the environment. Do not paste the key into chat, JARVIS commands, docs, tests, or config files.

## Commands

- `статус groq`
- `статус грок`
- `проверить groq ключ`
- `проверить ключ groq`
- `статус groq guard`
- `лимиты groq`
- `groq модель`
- `спроси groq: <текст>` safe no-network response
- `groq реальный запрос: <текст>` explicit one-shot request
- `groq one shot: <текст>` explicit one-shot request

## Manual Check Without Key

```powershell
python run.py
```

Inside JARVIS:

```text
статус groq
проверить groq ключ
статус groq guard
лимиты groq
groq модель
спроси groq: это не должно идти в сеть
groq реальный запрос: привет, кто ты?
выход
```

Expected: key status is `MISSING`, no key value is printed, normal Groq ask does not call the network, one-shot refuses safely without a key, and `dry_run` remains default.

## Optional Real-Key Test

This is not required for task completion.

```powershell
$env:GROQ_API_KEY = "PASTE_TEMPORARY_KEY_HERE"
$env:GROQ_MODEL = "llama-3.1-8b-instant"
python run.py
```

Inside JARVIS:

```text
статус groq
статус groq guard
groq реальный запрос: Ответь одним коротким предложением на русском: подключение работает?
выход
```

After exit:

```powershell
Remove-Item Env:GROQ_API_KEY
Remove-Item Env:GROQ_MODEL
```

## Troubleshooting

- Missing key: set `GROQ_API_KEY` in the environment.
- Auth error `401/403`: check that the key is valid and active.
- Rate/quota `429`: Groq free/developer limits may vary by account and model.
- Invalid model: unset `GROQ_MODEL` or use a safe model ID such as `llama-3.1-8b-instant`.
- Network error: retry later or verify local connectivity.
