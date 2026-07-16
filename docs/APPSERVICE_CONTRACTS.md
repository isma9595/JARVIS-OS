# AppService Contracts

TASK-077 exposes secure provider runtime status through AppService-safe methods
and status cards. Contract output remains metadata-only with no secrets, no
network, and no provider calls.

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

TASK-078 adds `process_one_shot_voice_request(source)`. It captures one
explicit local Vosk utterance through the existing one-shot recognition
boundary, then delegates recognized text to `execute_contract()` so voice input
and typed input share the same application-level text route.

TASK-079 adds a narrow Russian voice normalization boundary before that
delegation. The original recognized text is preserved, and only a safe
one-shot command candidate such as `статус система` is normalized to
`статус системы`. The normalizer does not execute commands, call providers,
read credentials, call `CommandProcessor`, or call `ActionRouter`.

JARVIS remains Russian-first for user-facing runtime behavior. The AppService
language boundary defaults to `ru-RU`, while existing command, intent,
provider, and Vosk settings continue to use Russian defaults. Recognized
Russian text remains Cyrillic and is not translated before it enters
`execute_contract()`.

## Relationship To CommandRegistry

`AppCommandCard` is built from `CommandRegistry` metadata. Command IDs,
categories, aliases, risk levels, network flags, privacy flags, voice flags,
and app readiness come from the registry.

The registry still does not execute commands.

TASK-076 adds conversational loop command cards under the `conversation`
category. These cards describe status, capabilities, and free-form preview
metadata only; contracts still do not call providers or execute dialog text.

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
- `AppVoiceRequestResult`
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
- Raw microphone audio is not sent to AI providers.
- Recognized voice text reaches providers only by entering the same text path
  as typed input.
- Russian provider-backed prompts preserve the original Russian recognized
  text; only text can reach a configured provider, never raw audio.

## Future UI Expectations

Future UI should use:

- `contract_status()`
- `status_cards()`
- `command_cards(category)`
- `contract_manifest()`
- `preview_contract(text)`
- `execute_contract(text, source)`
- `process_one_shot_voice_request(source)`

Future UI should not call `CommandProcessor` or `ActionRouter` directly.

## One-Shot Voice Contract

`AppVoiceRequestResult` reports capture, recognition, text-processing state,
recognized text when available, optional normalization details, composed
`AppExecutionContract` output, safe error code/message, and
confirmation-required state.

It serializes no Vosk runtime objects, audio buffers, microphone streams,
provider objects, credentials, or command processor internals.

For TASK-079 the result keeps `recognized_text` as the exact recognition output
after the existing AppService trim, and reports `normalized_text`,
`normalization_applied`, and `normalization_rules`. The normalized text is used
as the command candidate only when the normalizer marks it safe.

Russian is the current default user-facing language for voice results,
confirmation messages, local command output, provider-facing language policy,
and safe failures. Error codes may remain English for machines. Complete
multilingual support is not claimed; the language manager is only an
application-level extension point for future user-selected languages.

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
- Does not introduce full multilingual support.
- Does not switch speech recognition or command handling to English.
# Audio Lifecycle Card

Status cards now include `audio_lifecycle`, a safe metadata-only card for microphone/TTS lifecycle state. It reports no network use and no audio saving.
## Vertical Integration

TASK-075 uses AppService contracts as UI-safe serialization boundaries for the
vertical integration report. Contract status and manifest data remain
metadata-only: no secrets, no network, and no response execution.
