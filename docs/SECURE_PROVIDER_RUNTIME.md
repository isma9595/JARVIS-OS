# Secure Provider Runtime

## Why This Layer Exists

TASK-077 connects Secure Key Storage to explicit AI provider runtime credential
resolution. The layer gives provider one-shot gates one safe place to resolve
credentials without teaching status, preview, conversational, or vertical
integration paths to decrypt secrets.

## Relationship To Secure Key Storage

Secure Key Storage remains the encrypted-at-rest foundation. `SecureProviderRuntime`
uses `ApiKeyManager` and `SecureKeyStore` metadata for status, and calls
`get_secret()` only from `resolve_credential()`, which is used by explicit
provider execution paths.

Status/list methods use `has_secret()` and environment presence checks only.
They do not return, print, serialize, or log raw key values.

## Relationship To Provider Adapters

Provider adapters keep their existing APIs and safety gates. The runtime bridge
is injected at the request-gate layer for OpenAI, Gemini, Groq, and GigaChat.
When a real one-shot command is explicitly invoked, the gate resolves one
credential and passes it through a temporary environment for that request.

Ollama and dry_run do not require API keys.

## Source Order

1. Secure store is preferred when available and a provider key exists.
2. Environment variable fallback is used when secure store has no key.
3. Missing credentials return a safe refusal and no provider call.
4. Local/no-key providers use `local/no_key`.

Supported credential providers:

- `openai` -> `OPENAI_API_KEY`
- `gemini` -> `GEMINI_API_KEY`
- `groq` -> `GROQ_API_KEY`
- `gigachat` -> `GIGACHAT_AUTH_KEY`
- `ollama` -> no API key
- `dry_run` -> no API key

## Safety Guarantees

- Status never decrypts or prints keys.
- Status/list/preview/vertical integration use no network.
- Status/list/preview/vertical integration call no providers.
- Real provider requests remain explicit-only one-shot commands.
- AI responses are not executed as commands.
- `ProviderRuntimeCredential.__repr__()` and `to_dict()` do not include `value`.
- Missing credentials are safe refusals, not crashes.
- No raw key input command is added.
- No live provider validation is added.

## Commands

- `статус provider runtime`
- `статус ai provider runtime`
- `статус runtime провайдеров`
- `статус runtime ключей ai`
- `provider runtime credentials`
- `runtime ключи ai`
- `статус runtime groq`
- `статус runtime openai`
- `статус runtime gemini`
- `статус runtime gigachat`
- `статус runtime ollama`

All commands are read-only: no secrets, no network, no provider calls.

## Future

- UI for adding/removing keys.
- Live provider validation with explicit confirmation.
- Per-provider enable/disable toggles.
- Async non-blocking provider jobs.
- Cross-platform keyring backend later.
