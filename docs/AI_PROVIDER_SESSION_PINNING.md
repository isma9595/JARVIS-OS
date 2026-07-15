# AI Provider Session Pinning

TASK-061 adds runtime-only AI provider/model selection for explicit one-shot use.

Supported user commands:

- `статус ai сессии`
- `активная ai модель`
- `текущая ai модель`
- `список ai моделей`
- `список ai провайдеров`
- `выбрать ai provider <provider>`
- `выбрать ai провайдер <provider>`
- `выбрать ai модель <provider> <model>`
- `ai реальный запрос: <text>`
- `выбранная ai модель запрос: <text>`
- `продолжи через ту же модель: <text>`
- `продолжи через выбранную модель: <text>`
- `сбросить ai сессию`

Safety rules:

- Selection is runtime-only and is not persisted.
- Selection does not require a key and does not call the network.
- `dry_run` remains the default provider.
- External providers are not enabled permanently.
- One-shot selected-provider requests refuse safely when no provider/model is selected.
- One-shot selected-provider requests use existing provider gates and refuse safely when the required key is missing.
- Provider responses are never executed as commands.
- Session state stores only provider/model metadata and last successful provider metadata.

## TASK-062 Consensus Note

Consensus mode does not overwrite manual selected provider/model state. It is an
explicit comparison path that uses existing one-shot gates and leaves `dry_run`
as the default provider.

## TASK-063 Selection Policy Note

Manual runtime provider/model selection wins over selection policy
recommendations. The policy reports the selected provider/model for continued
work but does not change session state, reset state, overwrite last success, or
call the network.
## TASK-064 Ollama Update

Runtime session pinning supports `ollama`:

- `выбрать ai provider ollama`
- `выбрать ai модель ollama qwen2.5:1.5b`
- `ai реальный запрос: <text>`
- `продолжи через ту же модель: <text>`

Selection is runtime-only and does not call the network. Selected Ollama requests call localhost only and fail safely if Ollama or the model is unavailable.
# AI Context Privacy Preflight

Session pinning/manual provider selection does not override the context privacy boundary. A pinned external provider is still blocked for private, secret, file, memory, log, screen, audio, or unknown-sensitive context.
## TASK-066 Fallback Execution

Manual session provider selection is respected as the first fallback candidate,
but it does not bypass privacy, language, key, runtime, or model gates. If the
manual provider is blocked or unavailable, fallback continues through the safe
chain.
