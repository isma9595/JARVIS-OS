# Command Registry

## Purpose

TASK-068 adds a command registry and capability manifest foundation for JARVIS.
The current `CommandProcessor` is growing into a large command surface. The
registry gives future desktop UI, command search, categorized help, voice safety,
app service, installer/product mode, and plugin expansion a stable metadata
source.

## What This Does

- Adds `core/command_registry.py`.
- Stores command metadata in memory.
- Validates unique command IDs and aliases.
- Provides safe status, category, list, manifest, coverage, and search text.
- Exposes read-only informational commands through `CommandProcessor`.

## What This Does Not Do

- Does not replace `CommandProcessor`.
- Does not execute commands from the registry.
- Does not add desktop UI, installer, secure key storage, files/documents,
  screen capture, automation, provider behavior changes, or new dependencies.

## Metadata Fields

- `command_id`
- `title_ru`
- `description_ru`
- `category`
- `aliases`
- `risk_level`
- `read_only`
- `voice_auto_allowed`
- `requires_confirmation`
- `requires_network`
- `requires_ai_key`
- `requires_privacy_check`
- `ui_visible`
- `app_ready`
- `introduced_in`
- `notes_ru`

## Risk Levels

- `READ_ONLY`: informational command, no network or mutation.
- `CONFIRMATION_REQUIRED`: command changes local state or accepts arbitrary text.
- `NETWORK_EXPLICIT`: explicit provider/network request.
- `LOCAL_RUNTIME`: local runtime call such as Ollama localhost.
- `SENSITIVE`: arbitrary text/privacy-sensitive analysis.
- `DESTRUCTIVE_BLOCKED`: destructive/system/file automation remains blocked.
- `FUTURE`: planned capability, not implemented.

## Safety Flags

`voice_auto_allowed` means the command can be considered for conservative
read-only voice auto-execution. It does not bypass `CommandProcessor` or voice
safety.

`app_ready` means the metadata entry represents an implemented command suitable
for a future desktop UI. Future app entries are visible but marked
`app_ready=false`.

## Commands

- `статус command registry`
- `статус реестра команд`
- `реестр команд`
- `категории команд`
- `команды ai`
- `команды голос`
- `команды безопасность`
- `команды ollama`
- `команды приложение`
- `найти команду: <text>`

Search is metadata-only and does not execute matching commands.

## Safety

- Metadata only.
- No network.
- No disk writes.
- No secrets used.
- No command execution from registry results.
- Existing `CommandProcessor` remains the execution source.

## Future Use

- App service layer.
- Desktop UI command palette and categorized settings/help.
- Secure key storage UI.
- Installer/product mode.
- Plugin/module expansion.

## TASK-069 App Service

TASK-069 adds `JarvisAppService` as the app-facing boundary for future desktop
UI code. The service uses this registry for list/search/category/preview
metadata and delegates execution to `CommandProcessor`. See
`docs/JARVIS_APP_SERVICE.md`.
