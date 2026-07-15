# TASK-077 - Secure Provider Runtime Integration

## Goal

Safely connect Secure API Key Storage to AI provider runtime credential
resolution without enabling hidden network calls.

## Context

TASK-076 - Safe Conversational AI Loop is the current stable stage.
Stable commit: `4be498d`.
Commit message: `Add safe conversational loop`.

## User Requirements

- Prefer secure store over environment variables.
- Preserve environment fallback.
- Return safe missing-credential results.
- Keep provider runtime explicit-only.
- Do not print, store, log, or serialize raw keys.
- Do not decrypt secrets during status/list/preview/vertical integration.
- Do not call providers or network from status/preview/tests.
- Do not add providers, dependencies, UI, raw key commands, commits, or pushes.

## Files Changed

- `ai/secure_provider_runtime.py`
- `ai/__init__.py`
- `ai/openai_request_gate.py`
- `ai/gemini_request_gate.py`
- `ai/groq_request_gate.py`
- `ai/gigachat_request_gate.py`
- `core/command_processor.py`
- `core/command_registry.py`
- `voice/voice_command_allowlist.py`
- `app/app_service.py`
- `app/vertical_integration.py`
- `tests/unit/test_secure_provider_runtime.py`
- `tests/unit/test_secure_provider_runtime_integration.py`
- `tests/unit/test_app_service.py`
- `tests/unit/test_vertical_integration.py`
- `docs/SECURE_PROVIDER_RUNTIME.md`
- short doc/checkpoint/task-record updates

## Commands Added

- `статус provider runtime`
- `статус ai provider runtime`
- `статус runtime провайдеров`
- `статус ключей provider runtime`
- `статус runtime ключей ai`
- `provider runtime status`
- `provider runtime credentials`
- `ai runtime credentials`
- `runtime ключи ai`
- `ключи runtime провайдеров`
- `статус runtime groq/openai/gemini/gigachat/ollama`
- `runtime groq/openai/gemini/gigachat/ollama status`

## Safety Boundaries

- Status/list commands do not decrypt secrets.
- `resolve_credential()` is for explicit provider execution paths.
- Secure store is preferred over env.
- Env fallback remains.
- Missing credentials refuse safely.
- No network or provider call from runtime status.
- AI responses are not executed as commands.
- Voice auto-allowlist includes only read-only runtime status/list commands.

## Tests

Focused tests cover status safety, no secret leaks, secure-store preference,
environment fallback, unsupported providers, no-key local providers, safe
credential repr/to_dict, AppService methods, CommandProcessor commands,
CommandRegistry metadata, voice allowlist, vertical integration, and provider
gate compatibility.

## Manual Verification Commands

```powershell
python -m pytest tests/unit/test_secure_provider_runtime.py
python -m pytest tests/unit/test_secure_provider_runtime_integration.py
python -m pytest tests/unit/test_app_service.py
python -m pytest tests/unit/test_command_processor.py
python -m pytest tests/unit/test_command_registry.py
python -m pytest tests/unit/test_voice_command_allowlist.py
python -m pytest tests/unit/test_vertical_integration.py
python -m pytest tests/unit/test_desktop_shell.py
python -m pytest
python -W error::DeprecationWarning -m pytest
.\scripts\health_check.ps1
git diff --check
git status
```

## Expected Result

SecureProviderRuntime exists. Secure store is preferred over env for explicit
provider runtime credential resolution. Env fallback remains. Missing credentials
fail safely. Status commands expose no secrets and use no network. Existing
provider one-shot behavior remains guarded.

## Commit Message Suggestion

`Add secure provider runtime integration`
