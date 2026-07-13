# Voice Dialogue Speak Last Response Gate

TASK-046 adds a safe manual gate for repeating the last meaningful assistant
response by voice.

## What It Does

JARVIS keeps a small in-memory assistant response history for the current
process session. The user can explicitly ask to view or speak the last
meaningful response.

Commands:

- `последний ответ`
- `покажи последний ответ`
- `что ты ответил`
- `озвучь последний ответ`
- `скажи последний ответ`
- `произнеси последний ответ`
- `повтори голосом`
- `история ответов`
- `сколько ответов`
- `очистить историю ответов`
- `статус голосового диалога`

## Safety Boundaries

- JARVIS does not speak every response automatically.
- JARVIS does not enable always-on voice dialogue.
- JARVIS does not start background speech loops.
- JARVIS does not enable continuous listening.
- Speech still goes through `VoiceOutputManager`.
- Cloud TTS is not used.
- Text or audio is not sent to external services.
- Generated audio files are not saved.
- Assistant response history is not persisted to disk.

## Session-Only History

The response history exists only in memory. Restarting JARVIS clears it.
Empty responses are ignored, recent entries are capped, and long responses are
trimmed before storage. VoiceOutputManager still applies its own speech length
limit before playback or dry-run output.

Speech command results and history/status responses do not replace the last
meaningful response. This prevents `озвучь последний ответ` from becoming the
next response that JARVIS repeats.

## Voice Output Modes

OFF:

JARVIS explains that voice output is disabled and tells the user how to enable
test or local voice mode.

DRY_RUN:

JARVIS returns a `[TTS dry-run]` line containing the last response. No real
sound is played.

WINDOWS_LOCAL:

JARVIS speaks the last response using the gated Windows local TTS backend after
the user explicitly enables local voice mode.

## Why This Is Safer Than Full Dialogue

This gate gives the user explicit control over every spoken assistant response.
It proves the response-history foundation without enabling automatic replies,
continuous listening, wake words, interruption handling, or background audio
behavior.

## Future Direction

Possible future stages:

- speak current response only through an explicit gate
- explicit voice dialogue mode with clear enable/disable commands
- stop speaking command
- voice interruption support
- wake and stop words
- automatic spoken replies only after explicit opt-in and a separate safety gate
