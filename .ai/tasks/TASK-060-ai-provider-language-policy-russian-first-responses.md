# TASK-060 - AI Provider Language Policy / Russian-First Responses

## Goal

Add a provider-agnostic language policy layer so all external AI providers answer in
Russian by default unless the user explicitly asks for another language.

## Context

TASK-059 completed the GigaChat provider adapter and Russia-friendly fallback.
Stable baseline:

- Stable commit: `79c74e0`
- Commit message: `Add GigaChat provider adapter`
- Existing providers: `dry_run`, `openai`, `gemini`, `groq`, `gigachat`
- `dry_run` remains default
- External providers remain disabled by default
- Real external requests remain explicit one-shot only

## Files Changed

- `ai/provider_language_policy.py`
- `ai/__init__.py`
- `ai/openai_request_gate.py`
- `ai/gemini_request_gate.py`
- `ai/groq_request_gate.py`
- `ai/gigachat_request_gate.py`
- `core/command_processor.py`
- `voice/voice_command_allowlist.py`
- `tests/unit/test_ai_provider_language_policy.py`
- `tests/unit/test_openai_request_gate.py`
- `tests/unit/test_gemini_request_gate.py`
- `tests/unit/test_groq_request_gate.py`
- `tests/unit/test_gigachat_request_gate.py`
- `tests/unit/test_command_processor.py`
- `tests/unit/test_voice_command_allowlist.py`
- `docs/AI_PROVIDER_LANGUAGE_POLICY.md`
- `docs/AI_PROVIDER_ROUTER.md`
- `docs/AI_PROVIDER_CONFIGURATION.md`
- `docs/GROQ_PROVIDER_ADAPTER.md`
- `docs/GIGACHAT_PROVIDER_ADAPTER.md`
- `docs/OPENAI_PROVIDER_ADAPTER.md`
- `docs/GEMINI_PROVIDER_ADAPTER.md`
- `.ai/CHECKPOINT.md`

## Commands Added

- `статус ai language policy`
- `статус language policy`
- `ai language policy`
- `языковая политика ai`
- `язык ai`
- `ai язык`

Voice allowlist includes only read-only language policy status commands:

- `статус ai language policy`
- `статус language policy`
- `языковая политика ai`
- `язык ai`
- `ai язык`

## Safety Boundaries

- No external provider was made default.
- Network remains disabled by default.
- One-shot safety gates remain in place.
- `dry_run` was not removed or changed.
- OpenAI, Gemini, Groq, and GigaChat keep their existing adapter boundaries.
- Memory, profile, files, and logs are not sent automatically.
- API keys and tokens are not printed or saved.
- AI responses are not executed as commands.
- No new dependencies were added.
- No commit or push was performed.

## Tests

Targeted tests:

```powershell
python -m pytest tests/unit/test_ai_provider_language_policy.py
python -m pytest tests/unit/test_openai_request_gate.py
python -m pytest tests/unit/test_gemini_request_gate.py
python -m pytest tests/unit/test_groq_request_gate.py
python -m pytest tests/unit/test_gigachat_request_gate.py
python -m pytest tests/unit/test_command_processor.py
python -m pytest tests/unit/test_voice_command_allowlist.py
```

Full verification:

```powershell
python -m pytest
.\scripts\health_check.ps1
git diff --check
git status
```

## Manual Verification Commands

Remove external keys:

```powershell
Remove-Item Env:OPENAI_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:GEMINI_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:GROQ_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:GIGACHAT_AUTH_KEY -ErrorAction SilentlyContinue
Remove-Item Env:GIGACHAT_MODEL -ErrorAction SilentlyContinue
Remove-Item Env:GIGACHAT_SCOPE -ErrorAction SilentlyContinue
```

Run:

```powershell
python run.py
```

Inside JARVIS:

```text
статус ai language policy
статус language policy
языковая политика ai
язык ai
статус ai
спроси ai: this should still be dry-run
статус groq
статус gigachat
симулируй распознавание: статус ai language policy
симулируй распознавание: groq реальный запрос hello
ожидающая голосовая команда
нет
помощь
выход
```

## Expected Result

- Language policy status works without network.
- External one-shot prompts receive a Russian-first safe prefix by default.
- Explicit language requests and translation targets are respected.
- Code syntax and quoted text are preserved.
- `dry_run` remains default.
- Groq/GigaChat status remains safe.
- Real request via voice still requires confirmation.
- No secrets are printed.

## Commit Message Suggestion

`Add AI provider language policy`
