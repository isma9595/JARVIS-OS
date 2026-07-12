# Voice Command Confirmation Flow

TASK-038 adds a safe confirmation step between real one-shot Vosk recognition
and command processing.

## Why confirmation is required

Speech recognition can be imperfect. A recognized phrase must not be treated as
an executable command until the user explicitly confirms it.

## One-shot recognition flow

The command `распознай голос один раз` starts one explicit local Vosk
recognition attempt. If recognition succeeds and returns non-empty text,
JARVIS stores that text in memory as the pending voice command for the current
session and asks:

`Выполнить эту команду? Подтвердите: да / нет.`

The recognized command is not executed automatically.

If recognition is empty, blocked, or fails, no pending command is created.

## Confirm or cancel

To confirm a pending recognized command, answer one of:

- `да`
- `подтверждаю`
- `выполнить`
- `выполни`
- `ок`
- `ага`
- `yes`

To cancel it, answer one of:

- `нет`
- `отмена`
- `отмени`
- `не надо`
- `no`

After confirmation or cancellation, the pending command is cleared.

## Status and reset commands

Use these commands to check the pending voice command:

- `ожидающая голосовая команда`
- `pending voice command`
- `какая голосовая команда ожидает подтверждения`

Use these commands to clear it:

- `отменить голосовую команду`
- `сбросить голосовую команду`

Pending state is in memory only and is not persisted.

## Safety boundaries

Voice confirmation only permits JARVIS to treat the recognized text as user
input. The recognized text still goes through the normal `CommandProcessor` and
`SafeActionRouter` flow. Risky or forbidden commands keep the existing safety
classification and are not allowed to bypass protections.

TASK-038 does not enable continuous listening, background microphone listeners,
cloud audio, automatic downloads, automatic installs, or audio file saving by
default.

## Future step

A future task may add an allowlist for low-risk voice commands. Until then,
confirmed recognized text always goes through the normal command processor.
