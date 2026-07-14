# TASK-058C - Groq Python HTTP Transport Compatibility Fix

## Issue Summary

Direct PowerShell calls to Groq succeed with the same key, model, and session, but JARVIS Groq one-shot live requests return HTTP 403. The likely failure point is the Python transport/request path or one-shot config wiring, not the key or model.

## Evidence

- Direct PowerShell request: OK.
- Endpoint: `POST https://api.groq.com/openai/v1/chat/completions`.
- Model: `llama-3.1-8b-instant`.
- JARVIS command: `groq реальный запрос: Answer with exactly one word: OK`.
- JARVIS result before this task: `Groq authentication/permission failed: status 403.`

## Files Changed

- `ai/providers/groq_provider.py`
- `ai/groq_request_gate.py`
- `core/command_processor.py`
- `voice/voice_command_allowlist.py`
- `tests/unit/test_groq_provider.py`
- `tests/unit/test_groq_request_gate.py`
- `tests/unit/test_command_processor.py`
- `tests/unit/test_voice_command_allowlist.py`
- `docs/GROQ_PROVIDER_ADAPTER.md`
- `.ai/CHECKPOINT.md`

## Safety Boundaries

- Do not commit or print API keys.
- Do not require `GROQ_API_KEY` for tests.
- Do not make real network calls in tests.
- Do not make Groq the default provider.
- Do not enable Groq permanently.
- Do not remove `dry_run`, OpenAI, or Gemini.
- Do not save prompts/responses by default.
- Do not execute Groq output as commands.
- Do not add continuous listening.
- Do not commit or push.

## Tests

Run:

```powershell
python -m pytest tests/unit/test_groq_provider.py
python -m pytest tests/unit/test_groq_request_gate.py
python -m pytest tests/unit/test_groq_one_shot_smoke.py
python -m pytest tests/unit/test_command_processor.py
python -m pytest tests/unit/test_voice_command_allowlist.py
python -m pytest
.\scripts\health_check.ps1
git diff --check
git status
```

## Manual Verification

No-key run:

```powershell
python run.py
```

Inside JARVIS:

```text
статус groq
статус groq request shape
groq request shape
форма groq запроса
спроси groq: это не должно идти в сеть
groq реальный запрос: привет
симулируй распознавание: статус groq request shape
симулируй распознавание: groq реальный запрос привет
ожидающая голосовая команда
нет
выход
```

Expected:

- No key is printed.
- Request shape shows `Authorization: PRESENT` or `MISSING` only.
- No-network ask behavior is unchanged.
- No-key one-shot refuses safely.
- Voice real request requires confirmation.

Optional live test with a temporary local key:

```powershell
$env:GROQ_API_KEY = "PASTE_TEMPORARY_KEY_HERE"
$env:GROQ_MODEL = "llama-3.1-8b-instant"
python run.py
```

Inside JARVIS:

```text
статус groq
статус groq request shape
groq реальный запрос: Answer with exactly one word: OK
выход
```

After exit:

```powershell
Remove-Item Env:GROQ_API_KEY
Remove-Item Env:GROQ_MODEL
```

## Commit Message Suggestion

`Fix Groq Python transport compatibility`
