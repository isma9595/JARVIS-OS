# Ollama Local Provider

TASK-064 adds Ollama as the local/offline AI foundation for JARVIS.

## Purpose

- Local/private AI provider through a locally running Ollama server.
- No cloud, no API key, no Ollama Cloud.
- No automatic install, model pull, download, or payment logic.
- No memory/profile/files/logs are sent automatically.
- AI responses are never executed as commands.
- `dry_run` remains the default provider.

## Runtime

- Default base URL: `http://127.0.0.1:11434`
- Ollama API paths used:
  - `GET /api/tags`
  - `POST /api/chat`
- Chat requests set `stream=false`.
- Default model preference: `qwen2.5:1.5b`
- Optional environment variables:
  - `OLLAMA_BASE_URL`
  - `OLLAMA_MODEL`

`OLLAMA_BASE_URL` is accepted only when it is `http` and points to `localhost`, `127.0.0.1`, or `::1`. Credentials, HTTPS/cloud URLs, non-local hosts, query strings, fragments, and unsafe paths are rejected before any request is made.

## Commands

- `статус ollama`
- `статус олама`
- `статус локального ai`
- `ollama модель`
- `олама модель`
- `локальная ai модель`
- `список ollama моделей`
- `проверить ollama runtime`
- `ollama реальный запрос: <text>`
- `олама реальный запрос: <text>`
- `локальный ai запрос: <text>`
- `выбрать ai provider ollama`
- `выбрать ai модель ollama qwen2.5:1.5b`
- `ai реальный запрос: <text>`

Status/model commands do not call the runtime. Runtime/model-list commands may call only localhost `/api/tags`. Real requests may call only localhost `/api/chat` after an explicit command and local model check.

## If Ollama Is Not Running

JARVIS reports a safe local refusal. It does not crash, does not call cloud, does not install Ollama, and does not pull a model.

## If The Model Is Missing

JARVIS refuses the one-shot request and tells the user to install or pull the model manually outside JARVIS. It never starts `ollama pull`.

Manual examples outside JARVIS:

```powershell
ollama --version
ollama pull qwen2.5:1.5b
ollama run qwen2.5:1.5b
```

## Selection Policy

For privacy/offline prompts, the selection policy now recommends:

```text
ollama -> dry_run
```

The recommendation does not call Ollama. It suggests checking local models with `список ollama моделей` and using `ollama реальный запрос: <text>` for an explicit local request.

## Consensus

Consensus remains explicit-only. Ollama is not added to the default consensus provider order in TASK-064. A later task may add local plus external consensus mixing.

## Voice Safety

Voice allowlist includes only read-only/no-prompt local status commands:

- `статус ollama`
- `статус олама`
- `статус локального ai`
- `ollama модель`
- `олама модель`
- `локальная ai модель`

Runtime model-list commands and real requests are not auto-executed by voice.
# AI Context Privacy Preflight

Ollama remains the preferred local-only option for privacy/offline typed prompts, but it does not receive secret-like content or raw file/memory/log/screen/audio packages in this task. Redact secrets manually and use future explicit context confirmation for raw context.
## TASK-066 Fallback Execution

Ollama may appear in explicit fallback chains as the local-only provider. It is
called only through localhost, only when privacy allows it, and only if runtime
and model are already available. No pull, install, or download is automated.
## TASK-067 Live Verification Polish

Use `проверка ollama local` for explicit local readiness. It may call only the
configured localhost Ollama `/api/tags` endpoint through `OllamaRuntime`. It
does not pull, download, install, use cloud services, use keys, or execute
model responses as commands.

See `docs/AI_PROVIDER_LIVE_VERIFICATION.md`.
