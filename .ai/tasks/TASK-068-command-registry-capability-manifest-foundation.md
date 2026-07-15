# TASK-068 — Command Registry & Capability Manifest Foundation

## Goal

Create a safe command registry and capability manifest foundation for JARVIS.

## Context

- TASK-067 — AI Provider Live Verification & Polish is completed and pushed.
- Current stable commit: `28e4430`
- Commit message: `Add AI provider live verification polish`
- `dry_run` remains default.
- Privacy boundary is active.
- Fallback execution is explicit-only.
- Consensus is explicit-only.
- Voice safety is conservative.

## User Requirement

JARVIS is moving toward a real Windows desktop application with installer,
beautiful UI, AI provider settings, API key management, and future extensibility.
Before UI work, commands need a registry/capability manifest so they are not
hardcoded forever in one growing `CommandProcessor`.

## Files Changed

- `core/command_registry.py`
- `core/command_processor.py`
- `voice/voice_command_allowlist.py`
- `tests/unit/test_command_registry.py`
- `tests/unit/test_command_processor.py`
- `tests/unit/test_voice_command_allowlist.py`
- `docs/COMMAND_REGISTRY.md`
- `docs/AI_PROVIDER_ROUTER.md`
- `docs/AI_PROVIDER_LIVE_VERIFICATION.md`
- `docs/AI_PROVIDER_FALLBACK_EXECUTION.md`
- `docs/AI_CONTEXT_PRIVACY_BOUNDARY.md`
- `docs/OLLAMA_LOCAL_PROVIDER.md`
- `.ai/CHECKPOINT.md`
- `.ai/tasks/TASK-068-command-registry-capability-manifest-foundation.md`

## Commands Added

- `статус command registry`
- `статус реестра команд`
- `статус registry команд`
- `статус capability manifest`
- `реестр команд`
- `список команд jarvis`
- `команды jarvis`
- `capability manifest`
- `manifest команд`
- `категории команд`
- `категории jarvis`
- `категории command registry`
- `найти команду: <text>`
- `поиск команды: <text>`
- `command search: <text>`
- `команды ai`
- `команды голос`
- `команды безопасность`
- `команды ollama`
- `команды приложение`
- `команды profile`
- `команды system`

## Safety Boundaries

- Metadata only.
- No desktop UI.
- No installer.
- No secure key storage.
- No file/document reading.
- No screen capture.
- No automation.
- No provider network behavior changes.
- No external provider defaults.
- No privacy boundary bypass.
- No voice confirmation bypass.
- No dependencies added.
- No secrets stored or printed.
- No AI responses executed as commands.
- No commit or push.

## Tests

- Registry builds and validates unique IDs/aliases.
- Registry status/categories/list/search outputs are safe.
- Future app commands are `FUTURE` and `app_ready=false`.
- Risky commands are not voice-auto-allowed.
- Real provider commands require network, key, and privacy checks.
- `CommandProcessor` registry commands do not call `ActionRouter`.
- Existing AI/voice/provider status commands still work.
- Voice allowlist permits only read-only registry status/list/category commands.
- Voice search, real provider, fallback, and consensus commands remain blocked.

## Verification Commands

```powershell
python -m pytest tests/unit/test_command_registry.py
python -m pytest tests/unit/test_command_processor.py
python -m pytest tests/unit/test_voice_command_allowlist.py
python -m pytest
.\scripts\health_check.ps1
git diff --check
git status
```

## Manual `run.py` Verification

```powershell
python run.py
```

Commands:

- `статус command registry`
- `статус реестра команд`
- `реестр команд`
- `категории команд`
- `команды ai`
- `команды голос`
- `команды безопасность`
- `команды ollama`
- `команды приложение`
- `найти команду: fallback`
- `найти команду: ollama`
- `найти команду: privacy`
- `статус ai verification`
- `статус ai fallback execution`
- `статус ai privacy`
- `статус ollama`
- `симулируй распознавание: статус command registry`
- `симулируй распознавание: категории команд`
- `симулируй распознавание: команды ai`
- `симулируй распознавание: найти команду fallback`
- `ожидающая голосовая команда`
- `нет`
- `помощь`
- `выход`

## Expected Result

- Registry status works without network.
- List/category/search commands work.
- App commands show future/not implemented and `app_ready=false`.
- Search does not execute commands.
- Existing AI/voice/provider statuses still work.
- Voice registry status/list/category commands auto-execute.
- Voice search with arbitrary text requires confirmation.
- No secrets printed.
- No network called.
- `run.py` still works.

## Commit Message Suggestion

`Add command registry foundation`
