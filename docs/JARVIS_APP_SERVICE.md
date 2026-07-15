# JARVIS App Service

TASK-077 adds provider runtime status methods and a safe status card. These
methods report credential source metadata only: no decrypted secrets, no network,
and no provider calls.

## Purpose

TASK-069 adds a safe application service layer between a future Windows desktop
UI and the existing JARVIS core. Future UI code should use `JarvisAppService`
instead of calling `CommandProcessor` directly.

## What This Does

- Adds `app/app_service.py`.
- Provides status snapshots for future UI cards.
- Lists, searches, and categorizes commands through `CommandRegistry`.
- Previews command risk from registry metadata without execution.
- Delegates execution to `CommandProcessor`.
- Adds read-only AppService informational commands.
- Exposes TASK-076 conversational loop status, capabilities, preview, and safe
  handle methods without network/provider/audio execution.

## What This Does Not Do

- No GUI.
- No installer.
- No secure key storage.
- No file or document reading.
- No screen capture.
- No automation.
- No new dependencies.
- No provider calls from AppService.
- No prompt or response storage.

## Data Classes

- `AppCommandSource`: `CLI`, `DESKTOP_UI`, `VOICE`, `TEST`, `UNKNOWN`.
- `AppCommandPreview`: normalized command metadata and risk flags.
- `AppCommandResult`: wrapped `CommandProcessor` output and safety flags.
- `AppStatusSnapshot`: service, registry, UI, installer, key storage, network,
  dry-run, privacy, fallback, consensus, and voice safety state.

TASK-073 adds versioned contract dataclasses in `app/app_contracts.py`:
`AppContractStatus`, `AppStatusCard`, `AppCommandCard`, `AppPreviewContract`,
`AppExecutionContract`, and `AppContractManifest`. See
`docs/APPSERVICE_CONTRACTS.md`.

## Command Preview

`preview_command(text)` uses `CommandRegistry` metadata only. It does not call
`CommandProcessor`, `ActionRouter`, shell/system APIs, files, network, or AI
providers. Parameterized registry aliases such as `groq реальный запрос: <text>`
are matched as metadata prefixes for preview only.

## Safe Execution

`execute_command(text, source)` delegates to `CommandProcessor.process(text)`.
AppService does not bypass `CommandProcessor`, does not call `ActionRouter`
directly, and does not execute AI responses as commands.

Unknown commands can still pass to `CommandProcessor` exactly as before. Their
preview reports `known_command=false`.

## Relationship To CommandRegistry

AppService uses the registry as the app-facing capability manifest. A future
desktop command palette or settings screen can use it to show command IDs,
categories, risk levels, network flags, privacy flags, and `app_ready`.

## TASK-076 Conversational Loop

`JarvisAppService` exposes `conversational_preview_text_ru()` and related
methods for safe Russian-first dialogue classification. The loop can classify
known commands, small talk, drafting, research, simple action plans, complex
agent plans, and risky requests. It does not call providers, use network, start
audio, open browsers, touch files, or execute AI responses as commands.

## TASK-070 Desktop Shell

TASK-070 adds `app/desktop_shell.py` and `run_desktop.py` as a safe tkinter
desktop shell prototype. The shell uses `JarvisAppService` for status,
registry browsing, preview, and explicit execution. It does not call
`CommandProcessor` directly.

## Future UI

The desktop UI should call AppService for:

- command lists
- command search
- command preview
- status cards
- versioned contract status/manifests/cards
- explicit execution through `CommandProcessor`

The UI should not call `CommandProcessor` directly.

## Secure Key Storage

TASK-071 adds the secure key storage foundation. AppService status/capabilities
may mention that the foundation is available, but AppService still does not
read, print, validate, or route decrypted secrets. Future AI Provider Settings
UI should use the secure storage boundary instead of command arguments.

See `docs/SECURE_KEY_STORAGE.md`.

## Installer

Installer/product mode is planned but not implemented in TASK-069. The status
snapshot reports installer readiness as false.

## Safety Boundaries

- No network by default.
- Dry-run remains default.
- Privacy boundary remains active.
- Fallback and consensus remain explicit-only.
- Voice safety remains active.
- No secrets printed.
- No response execution.
- No arbitrary file reads.
- No disk writes by AppService itself.

## Commands

- `статус app service`
- `статус jarvis app service`
- `статус сервиса приложения`
- `статус приложения jarvis`
- `app service capabilities`
- `возможности app service`
- `возможности приложения jarvis`
- `app service commands`
- `команды app service`
- `app preview: <text>`
- `предпросмотр команды: <text>`
- `preview command: <text>`
- `предварительная проверка команды: <text>`

Preview commands are not voice auto-allowlisted.

## Future

- Desktop App Shell
- Secure Settings & API Key Storage
- AI Provider Settings UI
- Windows Installer Foundation
# Audio Lifecycle

AppService exposes `audio_lifecycle_status()`, `audio_lifecycle_status_text_ru()`, and `audio_status_card()` as metadata-only contracts. These methods do not start microphone capture, play TTS, use network, save audio, or expose secrets.
## Vertical Integration

TASK-075 adds `VerticalIntegrationService` access through AppService report,
checklist, and summary methods. These methods are metadata/read-only and do not
call providers, network, audio devices, or decrypted secret paths.
