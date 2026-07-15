# AI Provider Live Verification

## Command Registry

TASK-068 records live verification commands in the metadata-only command
registry for command search and future UI use. Verification behavior is still
implemented by `CommandProcessor` and the live verification module. See
`docs/COMMAND_REGISTRY.md`.

## Purpose

TASK-067 adds a safe manual verification layer for the existing AI provider
foundation. It does not add a provider, does not call external APIs
automatically, does not read files, and does not store prompts or responses.

## What This Verifies

- no-key safe mode
- Ollama local mode
- Groq live readiness when `GROQ_API_KEY` is present
- GigaChat live readiness when `GIGACHAT_AUTH_KEY` is present
- privacy boundary blocking/redaction
- explicit fallback execution
- explicit consensus safety
- voice allowlist safety

## Cleanup Environment

Run these in PowerShell before no-key verification:

```powershell
Remove-Item Env:OPENAI_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:GEMINI_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:GROQ_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:GIGACHAT_AUTH_KEY -ErrorAction SilentlyContinue
Remove-Item Env:GROQ_MODEL -ErrorAction SilentlyContinue
Remove-Item Env:GIGACHAT_MODEL -ErrorAction SilentlyContinue
Remove-Item Env:GIGACHAT_SCOPE -ErrorAction SilentlyContinue
Remove-Item Env:OLLAMA_MODEL -ErrorAction SilentlyContinue
Remove-Item Env:OLLAMA_BASE_URL -ErrorAction SilentlyContinue
```

Never paste keys into chat. Never commit secrets. Remove env vars after live
tests.

## No-Key Safe Mode

```powershell
python run.py
```

Commands:

```text
статус ai verification
статус проверки ai
чеклист ai проверки
проверка ai без ключей
проверка ai privacy
проверка live ai readiness
статус ai fallback execution
план ai fallback: обычный короткий вопрос
fallback ai запрос: обычный короткий вопрос
выход
```

Expected: key presence is `PRESENT`/`MISSING` only, no key values are printed,
status/checklist do not call network, fallback ends safely at `dry_run` if no
live/local provider is available.

## Ollama Local Verification

Only use this if Ollama and a model are already installed by the user. JARVIS
does not pull/download/install models.

```powershell
$env:OLLAMA_MODEL = "qwen2.5:3b"
python run.py
```

Commands:

```text
проверка ollama local
статус ollama
список ollama моделей
ollama реальный запрос: Ответь одним коротким предложением: локальный AI работает?
fallback ai запрос: это приватный вопрос, не отправляй в интернет
выход
```

Cleanup:

```powershell
Remove-Item Env:OLLAMA_MODEL -ErrorAction SilentlyContinue
Remove-Item Env:OLLAMA_BASE_URL -ErrorAction SilentlyContinue
```

Expected: only localhost `/api/tags` is used for readiness; no cloud, no keys,
no auto pull/download, no response execution.

## Groq Live Verification

Set the key locally. Do not paste it into chat.

```powershell
$env:GROQ_API_KEY = "<set locally, do not paste>"
python run.py
```

Commands:

```text
проверка live ai readiness
groq реальный запрос: Скажи одним коротким предложением: Groq работает?
fallback ai запрос: обычный короткий вопрос
выход
```

Cleanup:

```powershell
Remove-Item Env:GROQ_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:GROQ_MODEL -ErrorAction SilentlyContinue
```

## GigaChat Live Verification

Set the key locally. Do not paste it into chat.

```powershell
$env:GIGACHAT_AUTH_KEY = "<set locally, do not paste>"
python run.py
```

Commands:

```text
проверка live ai readiness
gigachat реальный запрос: Скажи одним коротким предложением: GigaChat работает?
fallback ai запрос: обычный короткий вопрос
выход
```

Cleanup:

```powershell
Remove-Item Env:GIGACHAT_AUTH_KEY -ErrorAction SilentlyContinue
Remove-Item Env:GIGACHAT_MODEL -ErrorAction SilentlyContinue
Remove-Item Env:GIGACHAT_SCOPE -ErrorAction SilentlyContinue
```

## Privacy Boundary Verification

```text
проверка ai privacy
статус ai privacy
матрица приватности ai
можно ли отправить во внешний ai: это приватный вопрос, не отправляй в интернет
консенсус ai: это приватный вопрос, не отправляй в интернет
```

Expected: canned secret-like examples are redacted, external providers and
consensus are blocked for private/secret context, no real provider is called.

## Fallback Verification

```text
статус ai fallback execution
план ai fallback: обычный короткий вопрос
fallback ai запрос: обычный короткий вопрос
```

Expected: ordinary provider commands do not retry automatically; only the
explicit fallback command executes the fallback chain. Output reports network
scope per attempt and does not execute provider responses.

## Consensus Verification

```text
статус ai consensus
консенсус ai: обычный короткий вопрос
```

Expected: consensus is explicit-only and privacy preflight blocks private or
secret context before provider calls.

## Voice Safety Verification

```text
симулируй распознавание: статус ai verification
симулируй распознавание: чеклист ai проверки
симулируй распознавание: проверка ollama local
ожидающая голосовая команда
нет
```

Expected: verification status/checklist auto-execute as read-only commands;
local runtime checks, live readiness, provider requests, fallback execution,
and consensus execution require confirmation.

## Safety Rules

- External providers are disabled by default.
- Real external requests are explicit one-shot only.
- Ollama is local-only and explicit one-shot only.
- No automatic model pull/download/install.
- No file/document/screen/audio context is sent automatically.
- No prompt/response persistence.
- No response execution.
- No payment/quota automation.
# TASK-069 App Service Note

Future desktop UI code should reach AI live verification status through
`JarvisAppService`, which previews command risk through `CommandRegistry` and
executes only by delegating to `CommandProcessor`.
