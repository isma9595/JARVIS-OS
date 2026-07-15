# AppService Contracts

## Why This Exists

TASK-073 adds stable, typed, versioned contracts for future JARVIS UI surfaces.
Desktop, AI provider settings, installer/product mode, mobile companion, and
future admin/support tools should consume contract objects instead of raw
strings or internal implementation details.

This is a foundation task only. It does not add product features.

## Relationship To AppService

`JarvisAppService` remains the app-facing boundary. Contract methods expose
safe status, cards, manifests, preview shape, and execution result shape.
Contract/list/status/card methods are deterministic and do not execute commands.

`execute_contract(text, source)` is the only execution contract method, and it
delegates to the existing `execute_command()` path.

## Relationship To CommandRegistry

`AppCommandCard` is built from `CommandRegistry` metadata. Command IDs,
categories, aliases, risk levels, network flags, privacy flags, voice flags,
and app readiness come from the registry.

The registry still does not execute commands.

## Relationship To DesktopShell

The desktop shell can read AppService contract status as a UI-safe status
addendum. No new desktop screens, key fields, or product UI are added.

## Stable Contract Version

- Schema name: `jarvis.app_service.contracts`
- Version: `0.1`

## Contract Dataclasses

- `AppContractStatus`
- `AppStatusCard`
- `AppCommandCard`
- `AppPreviewContract`
- `AppExecutionContract`
- `AppContractManifest`

Every contract supports deterministic `to_dict()`. Text-oriented contracts also
provide `safe_text_ru()` for UI-facing output.

## Safe Serialization

Contract serialization uses stable field names and simple standard-library
dataclasses. Obvious API-key/token patterns are redacted from serialized text.

Contracts are safe to pass to future UI code because they do not expose raw
internal objects, decrypted keys, provider responses as commands, or arbitrary
execution handles.

## Safety Boundaries

- No secrets.
- No accidental network calls.
- No provider calls from contract/list/status/card methods.
- No decrypted secret access.
- No prompt/response storage.
- No response execution as commands.
- Preview does not execute.
- Status, manifest, and card commands are read-only.

## Future UI Expectations

Future UI should use:

- `contract_status()`
- `status_cards()`
- `command_cards(category)`
- `contract_manifest()`
- `preview_contract(text)`
- `execute_contract(text, source)`

Future UI should not call `CommandProcessor` or `ActionRouter` directly.

## Mobile, Admin, And Support Relevance

Mobile and admin/support clients can consume the same schema/version, status
cards, command cards, preview contracts, and execution contracts later. This
task only creates the local contract foundation.

## Commands

- `статус app contracts`
- `app contracts manifest`
- `app status cards`
- `app command cards`

Aliases for these commands are registered as read-only AppService contract
metadata and are voice-allowlisted only for status/manifest/cards.

## What This Task Does Not Do

- Does not build AI Provider Settings UI.
- Does not build an installer.
- Does not build a mobile app.
- Does not build admin/support backend.
- Does not change provider request behavior.
- Does not change secure key behavior.
- Does not change command execution behavior.
- Does not add dependencies.
# Audio Lifecycle Card

Status cards now include `audio_lifecycle`, a safe metadata-only card for microphone/TTS lifecycle state. It reports no network use and no audio saving.
