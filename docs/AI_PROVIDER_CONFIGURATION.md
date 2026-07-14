# AI Provider Configuration

## Purpose

TASK-052 adds an offline-safe configuration and API key readiness layer for future providers such as Groq and Gemini. TASK-053 adds OpenAI as a disabled external provider config and adapter. Status/key checks still do not make network calls.

## Provider Config Model

The model lives in `ai/provider_config.py`:

- `AIProviderConfig` describes a provider name, type, default model, enabled flag, API key environment variable name, safety level, and notes.
- `AIProviderConfigStatus` reports readiness without exposing secrets.
- `AIProviderKeyStatus` is `NOT_REQUIRED`, `MISSING`, `PRESENT`, or `INVALID_REFERENCE`.
- `AIProviderRuntimeState` is `DRY_RUN_ONLY`, `DISABLED`, `MISSING_KEY`, `CONFIGURED`, or `ERROR`.

`api_key_env_var` must be an environment variable name only. Obvious secret-looking values such as `sk-...`, long token-like strings, spaces, or invalid environment variable names are rejected.

## Environment Variables

Future external providers use environment variables:

- Groq: `GROQ_API_KEY`
- Gemini: `GEMINI_API_KEY`
- Gemini model override: `GEMINI_MODEL`
- OpenAI: `OPENAI_API_KEY`

JARVIS only checks whether the variable exists and is non-empty. It never prints the key value and does not validate keys by network.

For now, `OPENAI_API_KEY` is used only by the explicit OpenAI one-shot request gate. `GEMINI_API_KEY` is used only by the explicit Gemini one-shot request gate. `GEMINI_MODEL` is optional and is validated as a model name, not a key. Status and key-check commands remain offline.

## Secret Safety

- Never put API keys in code, docs, tests, tracked JSON, or commits.
- Never commit secrets.
- Use environment variables for keys.
- JARVIS reports `PRESENT` or `MISSING`, not the actual value.
- This stage does not persist prompts, responses, provider keys, or provider outputs.

## Config Files

Tracked example:

- `config/ai_providers.example.json`

Ignored local paths:

- `.env`
- `.env.*`
- `*.env`
- `*.key`
- `config/ai_providers.local.json`
- `config/secrets.json`
- `config/secrets/`
- `secrets/`

The example file must not contain real secrets.

## Commands

- `статус ai конфигурации`
- `статус ai ключей`
- `конфигурация ai провайдеров`
- `безопасность ai ключей`
- `проверить groq ключ`
- `проверить gemini ключ`
- `проверить openai ключ`
- `статус openai`

These commands are Russian-first, read-only, deterministic, and offline. Voice auto-execution is allowlisted only for the safe read-only status/help/key-check commands.

## Current Limitations

- No real Groq provider.
- No real Gemini provider.
- OpenAI adapter exists but is disabled by default.
- No network calls during config/status/key checks.
- No API keys are required.
- Keys are checked only by environment variable presence.
- `dry_run` remains the only active AI provider.

## Future

- Groq adapter.
- Explicit OpenAI real request gate.
- Provider enable/disable commands.
- Optional encrypted local secrets or OS keyring support if needed.

## TASK-055 Update

OpenAI one-shot model selection is controlled only by the temporary environment variable `OPENAI_MODEL`. If it is missing, the guard uses `gpt-5.6`.

`OPENAI_MODEL` is validated as a model name, not a secret. Empty values, spaces, path separators, long token-like strings, and key-looking values such as `sk-...` are rejected. The model is not written to tracked config, and no command is added to save or permanently set it.

## TASK-056 Update

Gemini now has a disabled provider adapter and one-shot request gate. The default model is `gemini-2.5-flash-lite`, and the key must come from `GEMINI_API_KEY`.

The adapter remains disabled by default. `dry_run` remains default. Free tier, quota, rate limits, and available models may vary by account, region, and model.

## TASK-058 Update

Groq uses `GROQ_API_KEY` for the API key and optional `GROQ_MODEL` for one-shot model selection. The default Groq model is `llama-3.1-8b-instant`. Groq remains disabled by default, `dry_run` remains default, and key/status checks stay offline and never print key values.

## TASK-059 Update

GigaChat uses `GIGACHAT_AUTH_KEY` for the Authorization key, optional
`GIGACHAT_MODEL` for one-shot model selection, and optional `GIGACHAT_SCOPE`
for OAuth scope. The default model is `GigaChat`, and the default scope is
`GIGACHAT_API_PERS`.

OAuth access tokens are cached in memory only, never written to disk, and never
printed. GigaChat remains disabled by default, `dry_run` remains default, and
status/key/token checks stay offline.
