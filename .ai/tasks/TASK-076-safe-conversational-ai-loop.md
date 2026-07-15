# TASK-076 — Safe Conversational AI Loop

## Goal

Add the first safe conversational loop foundation so JARVIS can classify ordinary
Russian-first user text as known commands, small talk, AI questions, drafting
tasks, simple actions, research tasks, complex agentic tasks, risky actions, or
unknown/clarification cases.

## Context

- Previous stable stage: TASK-075 — Vertical Integration.
- Stable commit: `44ec8db`.
- Stable commit message: `Add vertical integration checks`.
- Previous full pytest and strict DeprecationWarning pytest passed with 1239
  tests, and `health_check` passed before this task.

## User Requirements

- Make JARVIS feel more like a human assistant while preserving safety.
- Distinguish simple commands from complex tasks.
- Keep simple commands fast in future.
- For complex tasks, produce browser/search + AI plans for future work.
- Preserve all existing safety boundaries.

## Files Changed

- `app/conversational_loop.py`
- `app/app_service.py`
- `app/__init__.py`
- `app/vertical_integration.py`
- `core/command_processor.py`
- `core/command_registry.py`
- `voice/voice_command_allowlist.py`
- `tests/unit/test_conversational_loop.py`
- `tests/unit/test_app_service.py`
- `tests/unit/test_command_processor.py`
- `tests/unit/test_command_registry.py`
- `tests/unit/test_voice_command_allowlist.py`
- `tests/unit/test_vertical_integration.py`
- `tests/unit/test_desktop_shell.py`
- `docs/CONVERSATIONAL_LOOP.md`
- `docs/JARVIS_APP_SERVICE.md`
- `docs/APPSERVICE_CONTRACTS.md`
- `docs/VERTICAL_INTEGRATION.md`
- `docs/COMMAND_REGISTRY.md`
- `docs/DESKTOP_APP_SHELL.md`
- `.ai/CHECKPOINT.md`
- `.ai/tasks/TASK-076-safe-conversational-ai-loop.md`

## Commands Added

- `статус conversational loop`
- `статус conversation loop`
- `статус диалога jarvis`
- `статус разговорного режима`
- `conversational loop status`
- `conversational loop capabilities`
- `возможности conversational loop`
- `возможности диалога jarvis`
- `возможности разговорного режима`
- `диалог: <text>`
- `чат: <text>`
- `jarvis: <text>`
- `джарвис: <text>`
- `поговори: <text>`
- `conversational preview: <text>`
- `предпросмотр диалога: <text>`

## Safety Boundaries

- No hidden network.
- No provider calls by default.
- No command execution by default in preview/handle.
- No browser/search automation.
- No file or OS automation.
- No microphone/TTS/audio start.
- No prompt/response storage.
- No decrypted secret access.
- No AI response execution as commands.
- Risky/destructive text is blocked or marked confirmation-required.
- Free-form dialog commands are not voice auto-allowlisted.

## Tests

Added or updated unit coverage for:

- Conversational status and classification examples.
- Known command preview for `статус ai`.
- Drafting, simple action, research, complex task, and risky classifications.
- AppService conversational status/preview methods.
- CommandProcessor status/capability/dialog commands.
- CommandRegistry conversational metadata.
- Voice allowlist boundaries.
- Vertical integration conversational safety check.
- Desktop shell safe execution of `диалог: привет`.

## Manual Verification Commands

```powershell
python -m pytest tests/unit/test_conversational_loop.py
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

If the sandbox blocks Windows temp/cache directories, use a workspace-local
pytest temp/cache path or run verification in the normal developer shell.

## Expected Result

- Conversational loop exists.
- JARVIS can classify ordinary Russian text safely.
- JARVIS gives human-like safe responses/plans.
- Known commands are recognized.
- Risky requests are blocked or confirmation-required.
- No hidden network.
- No provider calls by default.
- No mic/TTS.
- No commit or push performed by Codex.

## Commit Message Suggestion

`Add safe conversational loop`
