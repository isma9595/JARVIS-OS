# TASK-061 - AI Provider Session Pinning / Manual Model Selection

Status: in progress

Goal:

Add runtime-only AI provider/model session pinning so the user can select a provider/model manually and send explicit selected-provider one-shot requests.

Required behavior:

- Recognize Russian user-facing status, list, select, request, continuation, and reset commands.
- Keep selection in process memory only.
- Do not require keys or network for selection.
- Route selected-provider one-shot requests through the existing provider gates.
- Refuse safely without network when no selection exists or the selected provider key is missing.
- Keep `dry_run` as default and do not permanently enable external providers.
- Allowlist only read-only voice commands for session status/model/provider lists.
- Keep selection, reset, and request commands behind voice confirmation.

Verification:

- `python -m pytest tests/unit/test_ai_provider_session.py`
- `python -m pytest tests/unit/test_command_processor.py`
- `python -m pytest tests/unit/test_voice_command_allowlist.py`
- `python -m pytest`
- `.\scripts\health_check.ps1`
- `git diff --check`
- `git status`
