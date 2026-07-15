# AI Provider Fallback Execution

## Purpose

AI provider fallback execution is an explicit-only retry mode. It tries a safe
provider chain in order and stops at the first successful answer.

It is not automatic. Ordinary provider commands do not retry elsewhere.

## Fallback vs Consensus

- Fallback: tries providers in order, stops after first success, no synthesis.
- Consensus: asks multiple providers and compares/synthesizes answers.
- Both modes remain explicit-only and separate.

## Commands

- Status: `статус ai fallback execution`
- Plan only: `план ai fallback: <text>`
- Execute: `fallback ai запрос: <text>`

Aliases:

- `статус ai retry`
- `статус fallback ai`
- `статус безопасного fallback`
- `статус ai fallback executor`
- `план fallback ai: <text>`
- `ai fallback plan: <text>`
- `показать ai fallback: <text>`
- `ai fallback запрос: <text>`
- `безопасный fallback ai: <text>`
- `controlled ai retry: <text>`
- `ai retry запрос: <text>`

## Provider Chains

- General/fast: `groq -> gigachat -> openai -> gemini -> ollama -> dry_run`
- Russian/Russia: `gigachat -> groq -> openai -> gemini -> ollama -> dry_run`
- Code/reasoning: `openai -> groq -> gemini -> gigachat -> ollama -> dry_run`
- Private/offline: `ollama -> dry_run`
- Secret-like: real/local providers are blocked by privacy preflight; dry_run may
  return a safe redacted fallback.

Manual session provider selection is tried first, but it does not bypass the
privacy boundary.

## Safety

- Explicit fallback command required.
- Ordinary provider commands do not retry automatically.
- Privacy boundary runs before every provider attempt.
- External providers require privacy approval and a present key.
- Ollama is localhost-only and must already have runtime/model available.
- `dry_run` remains the terminal fallback and global default.
- Provider answers are never executed as commands.
- Prompts and responses are not stored to disk.
- Secrets, tokens, and key values are not printed.
- No model pull, install, payment, quota, browsing, file reading, screen capture,
  memory export, logs, or audio context sending is added.
- `network_called` means a provider gate was attempted; output also reports
  per-attempt `network_scope` and `external_network_called`.

## Examples

General prompt with no keys:

- Plan shows external providers with missing keys, then Ollama, then dry_run.
- Execution skips missing-key external providers and ends with dry_run if local
  Ollama is unavailable.

Private prompt:

- Chain is `ollama -> dry_run`.
- External providers are not attempted.

Secret prompt:

- Secret preview is redacted.
- Real/local providers are blocked by privacy.
- dry_run may return only a safe redacted fallback.

Selected Ollama unavailable:

- Manual selected `ollama` appears first.
- If localhost/model is unavailable, the attempt is marked unavailable and
  fallback continues to `dry_run`.

External key missing:

- Provider is marked `MISSING_KEY`.
- Key value is never printed.
