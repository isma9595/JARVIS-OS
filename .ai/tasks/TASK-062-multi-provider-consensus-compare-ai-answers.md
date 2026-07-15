# TASK-062 - Multi-Provider Consensus / Compare AI Answers

## Goal

Add an explicit multi-provider consensus mode where JARVIS can ask several AI
providers, compare their answers, and produce a safe deterministic final answer.

## Context

- Previous stable task: TASK-061 - AI Provider Session Pinning / Manual Model Selection
- Stable commit: `77c3a4b`
- Stable commit message: `Add AI provider session pinning`
- Existing providers: `dry_run`, `openai`, `gemini`, `groq`, `gigachat`
- `dry_run` remains default.

## User Requirements

- Consensus is explicit-only and never automatic.
- Supported real consensus providers: Groq, GigaChat, OpenAI, Gemini.
- Default provider order: Groq, GigaChat, OpenAI, Gemini.
- Missing provider keys are skipped without network.
- Provider failures are isolated.
- At least one successful provider response is required for synthesis.
- No prompts, responses, keys, tokens, memory, profile, files, or logs are persisted.
- Provider responses are never executed as commands.

## Files Changed

- `ai/provider_consensus.py`
- `ai/__init__.py`
- `core/command_processor.py`
- `voice/voice_command_allowlist.py`
- `tests/unit/test_ai_provider_consensus.py`
- `tests/unit/test_command_processor.py`
- `tests/unit/test_voice_command_allowlist.py`
- `docs/AI_PROVIDER_CONSENSUS.md`
- Existing AI provider documentation files
- `.ai/CHECKPOINT.md`

## Commands Added

Status:

- `статус ai consensus`
- `статус ai консенсуса`
- `статус консенсус ai`
- `ai consensus status`
- `статус сравнения ai`

Consensus:

- `консенсус ai: <text>`
- `ai консенсус: <text>`
- `спроси все ai: <text>`
- `сравни ответы ai: <text>`
- `сравнить ответы ai: <text>`
- `ai compare: <text>`
- `ai consensus: <text>`

## Safety Boundaries

- No external provider is made default.
- Network remains disabled except explicit one-shot provider gates.
- `dry_run` remains available separately and is not a real consensus provider.
- Existing one-shot gates and language policy remain in force.
- Session pinning is not overwritten.
- No new dependencies were added.
- No commits or pushes were made.

## Tests

- `python -m pytest tests/unit/test_ai_provider_consensus.py`
- `python -m pytest tests/unit/test_command_processor.py -k consensus`
- `python -m pytest tests/unit/test_voice_command_allowlist.py`

The full `tests/unit/test_command_processor.py` run was attempted but blocked by
pre-existing Windows temp-directory permission errors unrelated to TASK-062.

## Manual Verification Commands

```powershell
Remove-Item Env:OPENAI_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:GEMINI_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:GROQ_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:GIGACHAT_AUTH_KEY -ErrorAction SilentlyContinue
python run.py
```

Inside JARVIS:

- `статус ai consensus`
- `статус ai консенсуса`
- `статус сравнения ai`
- `консенсус ai: что такое JARVIS в одном предложении?`
- `спроси все ai: дай короткий ответ`
- `сравни ответы ai: что лучше для JARVIS - Groq или Ollama?`
- `статус ai сессии`
- `список ai моделей`
- `статус ai language policy`
- `статус groq`
- `статус gigachat`
- `симулируй распознавание: статус ai consensus`
- `симулируй распознавание: спроси все ai привет`
- `ожидающая голосовая команда`
- `нет`
- `помощь`
- `выход`

## Expected Result

- Consensus status works with no network.
- Real consensus commands refuse safely without provider keys.
- With keys, only present-key providers are attempted through one-shot gates.
- Provider summaries and safety footer are shown.
- `dry_run` remains default.
- Responses are not executed as commands.
- Secrets are not printed.

## Commit Message Suggestion

`Add AI provider consensus mode`
