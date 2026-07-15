# TASK-064 - Ollama Local Provider Adapter / Offline AI Foundation

## Goal

Add Ollama as a local/offline AI provider foundation for JARVIS.

## Context

- TASK-063 completed at stable commit `6271003`.
- Commit message: `Add AI provider selection policy`.
- `dry_run` remains default.
- Existing providers remain available: OpenAI, Gemini, Groq, GigaChat.

## User Requirements

- Local/offline AI through localhost only.
- No cloud, API key, automatic install, automatic pull, or external network.
- No automatic memory/profile/files/logs transmission.
- No response execution as commands.

## Files Changed

- `ai/ollama_runtime.py`
- `ai/providers/ollama_provider.py`
- `ai/ollama_request_gate.py`
- `ai/provider_config_manager.py`
- `ai/provider_router.py`
- `ai/provider_selection_policy.py`
- `core/command_processor.py`
- `voice/voice_command_allowlist.py`
- `config/ai_providers.example.json`
- `docs/OLLAMA_LOCAL_PROVIDER.md`
- Related AI provider docs
- Ollama and integration tests

## Commands Added

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
- selected generic one-shot through `ai реальный запрос: <text>`

## Safety Boundaries

- No Ollama install or pull automation.
- Only `http://localhost`, `http://127.0.0.1`, or `http://[::1]`.
- No Ollama Cloud.
- No API key.
- No automatic routing or fallback execution.
- `dry_run` remains default.
- Responses are not executed as commands.
- Prompts/responses are not written to disk.

## Tests

- `tests/unit/test_ollama_runtime.py`
- `tests/unit/test_ollama_provider.py`
- `tests/unit/test_ollama_request_gate.py`
- Updated selection policy, session, command processor, and voice allowlist tests.

## Manual Verification Commands

```powershell
python -m pytest tests/unit/test_ollama_runtime.py
python -m pytest tests/unit/test_ollama_provider.py
python -m pytest tests/unit/test_ollama_request_gate.py
python -m pytest tests/unit/test_ai_provider_selection_policy.py
python -m pytest tests/unit/test_ai_provider_session.py
python -m pytest tests/unit/test_command_processor.py
python -m pytest tests/unit/test_voice_command_allowlist.py
python -m pytest
.\scripts\health_check.ps1
git diff --check
git status
```

## Expected Result

JARVIS can use Ollama as an explicit localhost-only provider when the user has already installed Ollama and manually installed a model. Without Ollama running, status/model commands remain safe and one-shot requests refuse cleanly.

## Commit Message Suggestion

`Add Ollama local provider adapter`
