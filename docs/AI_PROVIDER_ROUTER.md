# AI Provider Router

## Purpose

TASK-051 starts the AI Brain / Provider Router Foundation cycle. The goal is to define stable provider contracts and a deterministic local router before any real Groq, Gemini, OpenAI, or other external adapter is connected.

## Architecture

- `ai/provider_contracts.py` defines request, response, provider info, capability, safety, and provider protocol types.
- `ai/provider_router.py` registers providers, tracks the default provider, routes by capability, and returns safe structured errors.
- `ai/providers/dry_run_provider.py` is the active default provider.
- `ai/providers/openai_provider.py` is registered as a disabled external adapter in TASK-053.
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

The router defaults to `dry_run`. It does not enable OpenAI network access by selecting or listing providers.

## Configuration Safety Layer

TASK-052 adds `ai/provider_config.py` and `ai/provider_config_manager.py` for safe readiness reporting. The config layer lists `dry_run`, `groq`, `gemini`, and `openai`, keeps external providers disabled by default, checks only environment variable presence, and never displays API key values.

See `docs/AI_PROVIDER_CONFIGURATION.md` for key safety rules and commands.

## Dry-Run Provider

`DryRunAIProvider` is offline and deterministic:

- provider: `dry_run`
- model: `jarvis-dry-run-v0`
- safety: `offline_deterministic`
- capabilities: `chat`, `summary`, `classification`

It does not use API keys, network, tools, local files, memory, user profile, or voice history.

## OpenAI Adapter

`OpenAIProvider` follows the Responses API pattern:

- endpoint: `POST https://api.openai.com/v1/responses`
- key env var: `OPENAI_API_KEY`
- body: `model`, `input`
- network: disabled unless a provider instance is explicitly created with `allow_network=True`

The adapter is visible through the router, but `dry_run` remains the default provider. `set_default_provider("openai")` does not enable network.

TASK-054 adds an OpenAI one-shot request gate outside default routing. It can make one explicit typed request through `OpenAIProvider` with `allow_network=True`, but it does not change the router default and does not enable OpenAI permanently.

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
- `статус openai`
- `проверить openai ключ`
- `спроси openai: <текст>`
- `openai: <текст>`

## Safety Boundaries

- OpenAI is registered but disabled by default.
- No network is used by default.
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
- `статус openai`
- `проверить openai ключ`

## Future Providers

Future adapters can sit behind the same contracts:

- Groq
- Gemini
- OpenAI real request gate

Future work:

- API key manager
- provider config
- real external provider adapters
- prompt safety layer
- model routing by task type
- context policy and privacy controls

## TASK-055 Update

The OpenAI one-shot gate now has a model/cost guard, but it still sits outside normal default routing. A real one-shot request creates a temporary `allow_network=True` provider instance for exactly one request and does not change `AIProviderRouter`.

After a one-shot request, `dry_run` remains the default provider.
