# Vertical Integration

TASK-075 adds a read-only vertical integration checkpoint for the current
JARVIS stack.

## Purpose

Vertical integration verifies that the major layers can be inspected together
without adding product features or changing runtime behavior.

Checked layers:

- CommandRegistry
- AppService Contracts
- AppService
- Desktop Shell
- Secure Keys
- Audio Lifecycle
- Voice Safety
- AI Safety
- Conversational Loop

## Report Checks

The report verifies registry categories, contract manifest safety, AppService
status and preview behavior, DesktopShellViewModel construction, secure key
metadata, audio lifecycle metadata, voice allowlist boundaries, explicit-only AI
provider requests, and no-network/no-secret integration flags.

TASK-076 adds a conversational loop check. It verifies that greeting text is
classified locally, risky text such as `удали все файлы` is blocked or
confirmation-required, and no network, providers, command execution,
microphone, or TTS are used.

## Safety Guarantees

- no network
- no secrets
- no provider calls
- no microphone or TTS start
- no response execution
- no risky command execution

The default report does not execute CommandProcessor smoke commands; it uses
metadata and safe status/preview contracts only.

## Commands

- `статус vertical integration`
- `статус интеграции jarvis`
- `статус вертикальной интеграции`
- `vertical integration checklist`
- `чеклист интеграции jarvis`
- `vertical integration summary`
- `кратко интеграция jarvis`

## Verify

```powershell
python -m pytest tests/unit/test_vertical_integration.py
python -m pytest tests/unit/test_app_service.py
python -m pytest tests/unit/test_command_processor.py
python -m pytest tests/unit/test_command_registry.py
python -m pytest tests/unit/test_voice_command_allowlist.py
python -m pytest tests/unit/test_desktop_shell.py
python -m pytest
python -W error::DeprecationWarning -m pytest
.\scripts\health_check.ps1
git diff --check
git status
```

Manual CLI smoke:

```powershell
python run.py
```

Then run the integration status, checklist, and summary commands. Risky
provider, fallback, consensus, secure key import, audio reset, and arbitrary
app preview commands remain confirmation-required or blocked from voice
auto-execution.

Manual desktop smoke:

```powershell
python run_desktop.py
```

Expected: the window opens, status and preview still work, no microphone starts,
no TTS starts, and no network is called.

## Future Work

- AI Provider Settings UI
- Installer
- Visual Design System
- Mobile companion
- Admin/support console
