# AI Provider Router

## Purpose

TASK-051 starts the AI Brain / Provider Router Foundation cycle. The goal is to define stable provider contracts and a deterministic local router before any real Groq, Gemini, OpenAI, or other external adapter is connected.

## Architecture

- `ai/provider_contracts.py` defines request, response, provider info, capability, safety, and provider protocol types.
- `ai/provider_router.py` registers providers, tracks the default provider, routes by capability, and returns safe structured errors.
- `ai/providers/dry_run_provider.py` is the only active provider for TASK-051.
- `core/command_processor.py` exposes typed status and dry-run AI commands, but AI output is returned only as text.

## Provider Contracts

Current contracts:

- `AIProviderCapability`: `CHAT`, `SUMMARY`, `CLASSIFICATION`, `CODE`, `VISION`, `TOOL_PLANNING`
- `AIProviderSafetyLevel`: `OFFLINE_DETERMINISTIC`, `LOCAL_ONLY`, `EXTERNAL_API`
- `AIRequest`: prompt, task type, language, optional max chars, metadata
- `AIResponse`: text, provider/model/capability/safety fields, error flag and message
- `AIProviderInfo`: provider metadata
- `AIProvider`: `get_info`, `supports`, `generate`

For TASK-051, only `CHAT`, `SUMMARY`, and `CLASSIFICATION` are active in the dry-run provider. `VISION` and `TOOL_PLANNING` are future markers only.

## Router

`AIProviderRouter` starts with `dry_run` as the default provider. It can:

- list providers
- report status in Russian
- set a known provider as default
- route by capability
- generate through the selected provider
- return safe errors for invalid requests or unsupported capabilities

The router is deterministic and does not perform network calls.

## Dry-Run Provider

`DryRunAIProvider` is offline and deterministic:

- provider: `dry_run`
- model: `jarvis-dry-run-v0`
- safety: `offline_deterministic`
- capabilities: `chat`, `summary`, `classification`

It does not use API keys, network, tools, local files, memory, user profile, or voice history.

## Commands

- `статус ai`
- `статус ии`
- `список ai провайдеров`
- `список ии провайдеров`
- `спроси ai: <текст>`
- `спроси ии: <текст>`
- `ai: <текст>`
- `ии: <текст>`
- `ai кратко: <текст>`
- `ии кратко: <текст>`
- `ai резюме: <текст>`
- `ии резюме: <текст>`
- `ai классифицируй: <текст>`
- `ии классифицируй: <текст>`

## Safety Boundaries

- No real external AI providers are connected.
- No network is used.
- No API keys are required or read.
- AI output is never executed as a command.
- AI output is not wired into `ActionRouter`.
- AI is not connected to shell, files, email, browser, internet, automation, or continuous microphone listening.
- Prompts and responses are not persisted by this foundation.
- Broad voice AI query commands are not allowlisted.

Allowed read-only voice commands:

- `статус ai`
- `статус ии`
- `список ai провайдеров`
- `список ии провайдеров`

## Future Providers

Future adapters can sit behind the same contracts:

- Groq
- Gemini
- other providers

Future work:

- API key manager
- provider config
- real external provider adapters
- prompt safety layer
- model routing by task type
- context policy and privacy controls
