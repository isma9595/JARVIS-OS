# Voice Command Session History

JARVIS keeps a small in-memory history of voice command recognition events for the current runtime session.

## What Is Stored

Each event can store:

- recognized voice text
- normalized text
- canonical command, when a safe alias resolves to one
- source, currently `one_shot_vosk`
- status
- reason
- safety notes
- creation time

This is text-only observability for debugging recognition and command safety decisions.

## Session-Only Safety

- History is in memory only.
- JARVIS does not write recognized voice text to disk.
- JARVIS does not store audio files.
- JARVIS does not send audio or recognized text to the cloud.
- JARVIS does not enable continuous listening or background microphone listeners.
- Unknown and risky voice commands still require confirmation.
- Voice commands still pass through `CommandProcessor` and `ActionRouter`.

## Commands

- `последнее распознавание`
- `последняя голосовая команда`
- `что ты услышал`
- `что ты распознал`
- `история голосовых команд`
- `покажи историю голоса`
- `история распознавания`
- `сколько голосовых команд`
- `очистить историю голосовых команд`
- `очисти историю голоса`
- `сбросить историю распознавания`

## Why This Helps

The history shows what Vosk recognized, whether the command was allowlisted, whether it created a pending confirmation, and whether the pending command was confirmed, canceled, blocked, empty, or failed.

This makes voice debugging practical without saving audio or adding persistent learning.

## Future Direction

A later task can build a correction flow, for example: `я сказал не X, а Y`. That should remain user-controlled and should not persist recognized text until persistence is explicitly approved.
