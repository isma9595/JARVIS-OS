# TASK-063 - AI Provider Fallback Matrix / Provider Selection Policy

## Goal

Add a safe deterministic AI provider selection policy and fallback matrix.

## Context

TASK-062 completed multi-provider consensus mode. Stable commit:
`41cef22` with message `Add AI provider consensus mode`.

Existing providers: `dry_run`, `openai`, `gemini`, `groq`, `gigachat`.
`dry_run` remains default. External providers remain disabled by default and
real external requests are explicit one-shot only.

## User Requirements

- Keep manual session provider/model selection authoritative.
- Allow manual model choice.
- Keep consensus explicit-only.
- Recommend provider/fallback order safely.
- List Ollama as planned local/offline foundation only.

## Files Changed

- `ai/provider_selection_policy.py`
- `ai/__init__.py`
- `core/command_processor.py`
- `voice/voice_command_allowlist.py`
- `tests/unit/test_ai_provider_selection_policy.py`
- `tests/unit/test_command_processor.py`
- `tests/unit/test_voice_command_allowlist.py`
- `docs/AI_PROVIDER_SELECTION_POLICY.md`
- related provider docs
- `.ai/CHECKPOINT.md`

## Commands Added

- `статус ai fallback`
- `статус ai selection policy`
- `статус выбора ai`
- `матрица ai провайдеров`
- `политика выбора ai`
- `какой ai выбрать: <text>`
- `ai route: <text>`

## Safety Boundaries

- No external provider default.
- No network by default.
- No automatic provider calls from policy.
- No Ollama implementation.
- No new provider adapters.
- No new dependencies.
- No prompt/response persistence.
- No secret printing or storage.
- No AI response execution.
- No commits or pushes.

## Tests

- `python -m pytest tests/unit/test_ai_provider_selection_policy.py`
- `python -m pytest tests/unit/test_command_processor.py`
- `python -m pytest tests/unit/test_voice_command_allowlist.py`
- `python -m pytest`
- `.\scripts\health_check.ps1`
- `git diff --check`
- `git status`

## Expected Result

JARVIS can explain provider roles and recommend a provider/fallback chain while
preserving all existing one-shot gates, session pinning, dry-run default,
consensus explicit-only behavior, and secret safety.

## Commit Message Suggestion

Add AI provider selection policy
