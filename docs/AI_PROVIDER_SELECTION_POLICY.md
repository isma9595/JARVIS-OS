# AI Provider Selection Policy

## Purpose

TASK-063 adds a deterministic recommendation-only policy for choosing an AI
provider by situation. The policy does not call providers, does not route
network requests, does not execute responses, and does not store prompts or
responses.

## Provider Roles

- `dry_run`: offline deterministic default. No key, no network, predictable
  tests. Limited answer quality.
- `groq`: fast external model for concise general answers. Requires
  `GROQ_API_KEY` and explicit one-shot command.
- `gigachat`: Russian/Russia-friendly external fallback. Requires
  `GIGACHAT_AUTH_KEY` and explicit one-shot command.
- `openai`: strong reasoning/code external provider when available. Requires
  `OPENAI_API_KEY` and explicit one-shot command.
- `gemini`: alternative/general external provider. Requires `GEMINI_API_KEY`
  and explicit one-shot command.
- `ollama`: planned future local/offline provider. Not implemented and not
  selectable as an implemented provider in TASK-063.

## Fallback Matrix

- General/fast: `groq -> gigachat -> openai -> gemini -> dry_run`
- Russian/Russia-oriented: `gigachat -> groq -> openai -> gemini -> dry_run`
- Code/strong reasoning: `openai -> groq -> gemini -> gigachat -> dry_run`
- Private/offline: `dry_run` now, planned `ollama` later
- Consensus: explicit command only, no automatic consensus call

## Safety Rules

- Manual session selection wins and is not overwritten.
- Consensus remains explicit-only.
- `dry_run` remains the default provider.
- External providers require explicit one-shot commands.
- Policy/status/recommendation calls do not use the network.
- Memory, profile, files, and logs are not sent.
- API keys and tokens are never printed or stored.
- Provider responses are never executed as commands.

## Commands

- `статус ai fallback`
- `статус ai selection policy`
- `статус выбора ai`
- `матрица ai провайдеров`
- `политика выбора ai`
- `какой ai выбрать: быстро ответь на вопрос`
- `какой ai выбрать: это приватный файл`
- `какой ai выбрать: сравни ответы нескольких ии`

Recommendation commands only recommend the next explicit command, such as
`выбрать ai provider groq`, `groq реальный запрос: <text>`,
`gigachat реальный запрос: <text>`, `консенсус ai: <text>`, or
`спроси ai: <text>`. They do not execute those commands.

## Limitations

- Recommendation is deterministic and based on safe prompt metadata.
- Cloud model availability is not validated online.
- Providers are not called automatically.
- Real fallback execution is intentionally left for a later task.
