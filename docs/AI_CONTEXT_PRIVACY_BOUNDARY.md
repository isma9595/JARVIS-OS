# AI Context Privacy Boundary

## Purpose

JARVIS uses a deterministic AI context privacy preflight before any explicit AI provider request. The boundary exists so private data is not accidentally sent to external AI providers before file, screen, document, memory, and workflow features are added.

The policy does not call network, does not read files, does not capture screen or audio, and does not store prompts or responses.

## Context Types

- `PUBLIC_OR_GENERAL`
- `USER_TYPED_GENERAL`
- `PRIVATE_OR_PERSONAL`
- `SECRET_LIKE`
- `FILE_CONTENT`
- `FILE_PATH_REFERENCE`
- `MEMORY_PROFILE`
- `LOG_OR_DEBUG`
- `SCREEN_OR_OCR`
- `AUDIO_TRANSCRIPT`
- `UNKNOWN_SENSITIVE`

Secrets are redacted in previews and refusal messages. API keys, bearer tokens, passwords, JWT-like values, and common key phrases are treated as secret-like.

## Targets

- `dry_run`: offline deterministic default, no network.
- `Ollama/local`: localhost-only explicit one-shot provider.
- External providers: Groq, GigaChat, OpenAI, Gemini.
- External consensus: explicit-only multi-provider path; stricter because multiple external providers may be attempted.

## Matrix

| Context type | dry_run | Ollama/local | External providers | External consensus |
| --- | --- | --- | --- | --- |
| Public/general | Allowed | Allowed | Allowed | Allowed with quota warning |
| User-typed general | Allowed | Allowed | Allowed | Allowed with quota warning |
| Private/personal | Allowed | Allowed local-only | Blocked | Blocked |
| Secret-like | Allowed only as redacted policy output | Blocked | Blocked | Blocked |
| File path reference | Allowed | Allowed as path text only | Blocked | Blocked |
| File content | Allowed | Blocked until explicit context package exists | Blocked | Blocked |
| Memory/profile | Allowed | Blocked until explicit context package exists | Blocked | Blocked |
| Logs/debug | Allowed | Blocked until explicit context package exists | Blocked | Blocked |
| Screen/OCR | Allowed | Blocked until explicit context package exists | Blocked | Blocked |
| Audio transcript | Allowed | Blocked until explicit context package exists | Blocked | Blocked |

## Commands

- `статус ai privacy`
- `политика приватности ai`
- `матрица приватности ai`
- `что можно отправлять ai`
- `проверить ai контекст: <text>`
- `можно ли отправить ai: <text>`
- `можно ли отправить во внешний ai: <text>`
- `можно ли отправить в ollama: <text>`

Status and matrix commands are read-only and voice allowlisted. Check commands accept arbitrary text and are not voice allowlisted.

## Examples

General prompt:

```text
проверить ai контекст: обычный вопрос про погоду
```

Allowed for dry_run, Ollama/local, external providers, and external consensus.

Private prompt:

```text
проверить ai контекст: это приватный файл, не отправляй в интернет
```

Allowed for dry_run and Ollama/local typed analysis. Blocked for external providers and consensus.

Secret prompt:

```text
проверить ai контекст: мой api key sk-test-1234567890secret
```

Blocked for all real providers. The secret value is redacted in output.

Screen or log prompt:

```text
проверить ai контекст: скриншот экрана с debug log
```

Blocked for real providers until a future explicit context package and confirmation flow exists.

## Integration

- External one-shot gates block sensitive/private/secret/file/memory/log/screen/audio context before key checks or provider calls.
- Ollama allows private user-typed prompts locally, but blocks secrets and raw context packages.
- Consensus uses the stricter external consensus target before attempting any provider.
- Manual session selection does not override the privacy boundary.
- Provider responses are never executed as commands.

## Limitations

This is a deterministic heuristic boundary, not a legal or complete privacy classifier. A future task may add explicit context packages with user confirmation for selected files, memory, logs, screen, audio, or document content.
## TASK-066 Fallback Execution

The fallback executor uses this boundary before every provider attempt. Secret
context blocks real/local providers, private context blocks external providers,
and previews are redacted. No files, memory, logs, screen, or audio are packaged
or sent by fallback execution.
## TASK-067 Live Verification Polish

Use `проверка ai privacy` for a canned deterministic privacy verification. It
uses safe examples only, redacts a secret-like example, confirms external
provider and consensus blocking for private/secret context, and calls no real
provider.

See `docs/AI_PROVIDER_LIVE_VERIFICATION.md`.
