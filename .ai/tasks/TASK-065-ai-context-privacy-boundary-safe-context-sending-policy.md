# TASK-065 — AI Context & Privacy Boundary / Safe Context Sending Policy

## Goal

Add a deterministic AI context privacy boundary and safe context sending policy so JARVIS can decide what context may be sent to dry_run, Ollama/local, external providers, and explicit external consensus.

## Context

- Previous stable stage: TASK-064 — Ollama Local Provider Adapter / Offline AI Foundation
- Last stable commit: `5d7aec6`
- Last stable commit message: `Add Ollama local provider adapter`
- Existing providers: dry_run, ollama, openai, gemini, groq, gigachat
- dry_run remains default
- Ollama remains local-only and explicit one-shot only
- External providers remain disabled by default and explicit one-shot only
- Consensus remains explicit-only

## User Requirements

JARVIS must not accidentally send private data, files, logs, screenshots, profile, memory, or secrets to external AI providers. Privacy-sensitive context should prefer Ollama/local or dry_run, and secret-like content should be redacted/manual only.

## Files Changed

- `ai/context_privacy_policy.py`
- `ai/openai_request_gate.py`
- `ai/gemini_request_gate.py`
- `ai/groq_request_gate.py`
- `ai/gigachat_request_gate.py`
- `ai/ollama_request_gate.py`
- `ai/provider_consensus.py`
- `ai/provider_selection_policy.py`
- `ai/__init__.py`
- `core/command_processor.py`
- `voice/voice_command_allowlist.py`
- `tests/unit/test_ai_context_privacy_policy.py`
- provider gate, consensus, selection, command processor, and voice allowlist tests
- `docs/AI_CONTEXT_PRIVACY_BOUNDARY.md`
- related AI provider docs
- `.ai/CHECKPOINT.md`

## Commands Added

- `статус ai privacy`
- `статус ai privacy boundary`
- `статус ai context`
- `статус ai context boundary`
- `статус приватности ai`
- `статус контекста ai`
- `политика приватности ai`
- `матрица приватности ai`
- `матрица контекста ai`
- `что можно отправлять ai`
- `ai context matrix`
- `ai privacy matrix`
- `проверить ai контекст: <text>`
- `проверить приватность ai: <text>`
- `можно ли отправить ai: <text>`
- `можно ли отправить во внешний ai: <text>`
- `можно ли отправить в ollama: <text>`
- `ai privacy check: <text>`
- `ai context check: <text>`

## Safety Boundaries

- No file reading/sending added.
- No screen capture added.
- No document analysis added.
- No autonomous browsing added.
- No external provider made default.
- No network enabled by default.
- No one-shot, session pinning, or consensus gates bypassed.
- No prompt/response persistence added.
- No secret storage or printing added.
- AI responses are not executed as commands.
- No dependencies added.

## Tests

Focused tests added or updated for:

- context policy classification, decisions, redaction, status, matrix
- external gates blocking private/secret prompts before provider calls
- Ollama allowing private typed prompts but blocking secrets
- consensus preflight blocking private/secret prompts before provider attempts
- selection policy recommendations based on privacy classification
- CommandProcessor privacy status/matrix/check routing
- voice allowlist read-only privacy commands and non-allowlisted arbitrary checks

## Manual Verification Commands

```powershell
python -m pytest tests/unit/test_ai_context_privacy_policy.py
python -m pytest tests/unit/test_openai_request_gate.py
python -m pytest tests/unit/test_gemini_request_gate.py
python -m pytest tests/unit/test_groq_request_gate.py
python -m pytest tests/unit/test_gigachat_request_gate.py
python -m pytest tests/unit/test_ollama_request_gate.py
python -m pytest tests/unit/test_ai_provider_consensus.py
python -m pytest tests/unit/test_ai_provider_selection_policy.py
python -m pytest tests/unit/test_command_processor.py
python -m pytest tests/unit/test_voice_command_allowlist.py
python -m pytest
.\scripts\health_check.ps1
git diff --check
git status
```

## Expected Result

Sensitive context is blocked before external provider calls, secrets are redacted in policy output/refusals, Ollama remains local-only and conservative, consensus is stricter, and manual provider selection does not override the privacy boundary.

## Commit Message Suggestion

`Add AI context privacy boundary`
