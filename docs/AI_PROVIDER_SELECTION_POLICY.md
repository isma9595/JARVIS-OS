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
## TASK-064 Ollama Update

Ollama is now implemented as a local-only explicit one-shot provider. For private/offline prompts the policy recommends `ollama -> dry_run`: Ollama if the user wants real local intelligence and has a local runtime/model ready, otherwise `dry_run` as the safest no-AI/no-service fallback.

Policy recommendations do not call Ollama. Safe next steps are `список ollama моделей` and `ollama реальный запрос: <text>`. No external network or API key is required.
# AI Context Privacy Preflight

Provider selection now uses the context privacy classifier. Private/offline prompts recommend `ollama -> dry_run`; secret-like prompts recommend redaction/manual handling; raw file, memory, screen, audio, and log context does not recommend external providers.
## TASK-066 Fallback Execution

Selection policy remains recommendation-only. For safe multi-provider retry use
`fallback ai запрос: <text>`. For compare/synthesis use consensus. Private or
offline fallback execution remains `ollama -> dry_run`.
## TASK-067 Live Verification Polish

The selection policy remains read-only for status/matrix/recommendation output.
Fallback execution is separate and explicit-only: use `план ai fallback: <text>`
to inspect the chain and `fallback ai запрос: <text>` to execute it. Ordinary
provider commands do not retry automatically.

Live verification commands are documented in
`docs/AI_PROVIDER_LIVE_VERIFICATION.md`.
