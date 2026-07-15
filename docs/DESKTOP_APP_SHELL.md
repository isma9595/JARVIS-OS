# Desktop App Shell

TASK-077 adds read-only provider runtime status execution through the existing
AppService/CommandProcessor path. No provider settings UI, raw key input, live
validation, microphone, TTS, or network behavior is added.

## Why This Exists

TASK-070 adds the first safe desktop application shell prototype for JARVIS.
It prepares the project for a future Windows desktop app, dashboard UI,
command preview, command execution through AppService, registry/category
browsing, AI provider settings, secure key storage, installer/product mode,
and a future visual design system.

This is not the final UI, installer, or AI settings screen. TASK-071 adds the
secure key storage foundation, but this shell still has no key input fields.

## Relationship To AppService

The desktop shell uses `JarvisAppService` as its app-facing boundary.
The shell can show service status, list registry commands, preview command
risk, and execute explicit user commands only through AppService.

TASK-073 adds versioned AppService contracts. The shell may read contract
status/cards through AppService, but TASK-073 adds no new screens or key input.

## Relationship To CommandRegistry

`CommandRegistry` remains the metadata source for categories, command lists,
risk levels, network flags, privacy flags, and app readiness.

## Why UI Must Not Call CommandProcessor Directly

The UI is not an execution authority. It must not bypass AppService or call
`ActionRouter` directly. AppService delegates execution to `CommandProcessor`
so the existing safety boundaries remain in charge.

## How To Run

```powershell
python run_desktop.py
```

`run.py` remains unchanged and is still the CLI entry point.

## Current Shell Can Do

- Show desktop/app service status.
- List command registry categories and commands.
- Preview command risk without execution.
- Execute explicit command text through AppService.
- Execute `диалог: <text>` through AppService/CommandProcessor as a safe
  conversational preview/plan.

## Current Shell Does Not Do

- No installer.
- No key input UI.
- No automatic provider use of secure key storage.
- No AI settings UI yet.
- No file reading.
- No screen capture.
- No automation.
- No network by default.

## Safety

- No auto execution on startup.
- No secrets are stored or printed by the shell.
- No network by default.
- AI responses are not executed as commands.
- Preview does not execute target commands.
- Risky/network commands require explicit command text and Execute.
- Conversational preview does not call providers, network, browser, audio, or
  file/OS automation.

## Future

- AI Provider Settings UI.
- Secure Settings & API Key Storage.
- Windows Installer Foundation.
- Visual Design System.
# Audio Lifecycle

The desktop shell can consume the AppService audio lifecycle status card for future voice status UI. TASK-074 does not add microphone buttons, TTS controls, new windows, or real audio actions.
## Vertical Integration

TASK-075 verifies that `DesktopShellViewModel` can build and preview safe
commands through AppService without opening a GUI, starting audio, or using
network.
