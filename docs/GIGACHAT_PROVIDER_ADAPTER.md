# GigaChat Provider Adapter

## TASK-060 Language Policy

GigaChat real one-shot prompts pass through the shared AI provider language policy
before the chat request. The default is Russian-first, while explicit user language
requests and translation targets are respected. No memory/profile/files/logs or
secrets are added, `dry_run` remains default, and responses are not executed.

## Purpose

GigaChat is registered as a Russia-friendly fallback provider after Groq. It is
disabled by default and can make a real request only through an explicit
one-shot command.

## Authorization Flow

- Set `GIGACHAT_AUTH_KEY` in the environment only.
- OAuth endpoint: `https://ngw.devices.sberbank.ru:9443/api/v2/oauth`.
- OAuth scope defaults to `GIGACHAT_API_PERS`.
- Access tokens are cached in memory only and are never written to disk.
- Tokens are treated as short-lived, about 30 minutes.

Optional environment variables:

- `GIGACHAT_MODEL`, default `GigaChat`.
- `GIGACHAT_SCOPE`, allowed: `GIGACHAT_API_PERS`, `GIGACHAT_API_B2B`, `GIGACHAT_API_CORP`.

## Safety

- `dry_run` remains the default provider.
- GigaChat is not enabled permanently.
- Auth key and access token values are never printed.
- AI responses are returned as text and are not executed as commands.
- Memory, profile, files, voice history, logs, and workspace content are not sent automatically.
- Tests use fake clients only.
- Free/paid quota may vary by account, scope, and model.

## Commands

- `статус gigachat`
- `проверить gigachat ключ`
- `статус gigachat token`
- `статус gigachat guard`
- `лимиты gigachat`
- `gigachat модель`
- `статус gigachat request shape`
- `спроси gigachat: <текст>` safe no-network refusal
- `gigachat реальный запрос: <текст>` explicit one-shot
- `сбер реальный запрос: <текст>` explicit one-shot

## Manual Real-Key Test

PowerShell local-only example:

```powershell
$env:GIGACHAT_AUTH_KEY = "PASTE_TEMPORARY_AUTH_KEY_HERE"
$env:GIGACHAT_MODEL = "GigaChat"
$env:GIGACHAT_SCOPE = "GIGACHAT_API_PERS"
python run.py
```

Inside JARVIS:

```text
статус gigachat
статус gigachat token
статус gigachat request shape
gigachat реальный запрос: Ответь одним коротким предложением на русском: подключение работает?
выход
```

After exit:

```powershell
Remove-Item Env:GIGACHAT_AUTH_KEY
Remove-Item Env:GIGACHAT_MODEL
Remove-Item Env:GIGACHAT_SCOPE
```

Do not paste the auth key into chat logs or JARVIS commands.

## Troubleshooting

- Missing key: set `GIGACHAT_AUTH_KEY` in the environment.
- OAuth 401/403: auth key or scope is not accepted.
- 404: model may be invalid or unavailable.
- 422: request validation or context issue.
- 429: quota or rate limit.
- Token expired: the next explicit one-shot obtains a fresh token.
- TLS/certificate/network error: local network or certificate trust issue.
