# OpenAI Provider Adapter

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

Real one-shot OpenAI network calls are intentionally not enabled in TASK-053.

## Future

- Explicit real request gate
- Provider enable/disable controls
- Model selection
- Prompt safety and context policy
- Cost and rate limit handling
