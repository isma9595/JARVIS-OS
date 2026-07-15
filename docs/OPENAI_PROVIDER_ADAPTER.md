# OpenAI Provider Adapter

## TASK-060 Language Policy

OpenAI real one-shot prompts pass through the shared AI provider language policy before
the Responses API call. The default is Russian-first, explicit language requests and
translation targets are respected, `dry_run` remains default, and no memory/profile/files/logs
or secrets are added to the prompt.

## Purpose

TASK-053 adds a safe OpenAI provider adapter behind `AIProviderRouter` using the OpenAI Responses API pattern.

OpenAI is disabled by default, and real network requests are not enabled by this task.

## Architecture

- Provider: `ai/providers/openai_provider.py`
- Router integration: `AIProviderRouter`
- API pattern: `POST https://api.openai.com/v1/responses`
- Request body: `model` and `input`
- Response parsing prefers `output_text`, then a common `output -> content -> text` shape.

The provider uses only the Python standard library. Tests pass a fake HTTP client and do not make network calls.

## API Key

OpenAI uses `OPENAI_API_KEY`.

JARVIS checks only whether the variable is present or missing. Key values are never printed, logged, stored in tracked files, or included in user-facing errors.

## Commands

- `статус openai`
- `проверить openai ключ`
- `спроси openai: <текст>`
- `openai: <текст>`

`спроси openai` and `openai:` intentionally return a safe disabled/network-disabled message. No request is sent by default.

Use dry-run AI through `спроси ai: <текст>`.

AI responses are returned as text only and are not executed as commands.

## Current Limitation

TASK-054 adds `docs/OPENAI_ONE_SHOT_REQUEST_GATE.md` and `ai/openai_request_gate.py`.

The adapter still remains disabled by default. Real calls are allowed only through the explicit one-shot gate command, which creates a temporary enabled provider instance for one request and does not persist state.

## Future

- Explicit real request gate
- Provider enable/disable controls
- Model selection
- Prompt safety and context policy
- Cost and rate limit handling

## TASK-055 Update

`OpenAIProvider` now accepts a guarded `max_output_tokens` value from `AIRequest.metadata["max_output_tokens"]` and sends it to the Responses API when present. Arbitrary metadata is not forwarded.

The request body remains limited to:

- `model`
- `input`
- `max_output_tokens` when provided by the one-shot guard

The adapter still does not send memory, profile data, files, logs, tools, streaming options, or `previous_response_id`.

## TASK-058 Note

OpenAI remains optional and may require paid billing. Gemini and Groq are tracked as free-tier candidates, but they also remain disabled by default and explicit one-shot only.

## TASK-062 Consensus Note

OpenAI may be attempted by explicit consensus commands only when
`OPENAI_API_KEY` is present. Consensus uses the OpenAI one-shot gate, does not
enable OpenAI permanently, does not override session pinning, and does not
include `dry_run` as a real consensus provider.

## TASK-063 Selection Policy Note

Selection policy may recommend OpenAI for code/strong reasoning tasks when
`OPENAI_API_KEY` is PRESENT. This is recommendation-only: no network is called,
manual session pinning wins, and real OpenAI use still requires an explicit
one-shot command.
# AI Context Privacy Preflight

OpenAI real one-shot requests are blocked by the context privacy boundary for sensitive/private/secret/file/memory/log/screen/audio context before any provider call.
