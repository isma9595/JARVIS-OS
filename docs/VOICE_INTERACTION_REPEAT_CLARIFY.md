# Voice Interaction Repeat / Clarify Controls

TASK-049 adds safe current-session controls for repeating and clarifying recent
voice dialogue context.

## Commands

- `что ты сказал` / `что ты ответил` / `повтори текстом` show the last
  meaningful assistant response.
- `повтори` / `повтори голосом` / `скажи ещё раз` speak the last meaningful
  assistant response through `VoiceOutputManager`.
- `что я сказал` / `что ты услышал` / `последняя голосовая команда` show the
  last recognized voice command, canonical command, source, and status.
- `повтори последнюю голосовую команду` can speak only the recognized text of
  the last voice command.
- `объясни короче` / `скажи короче` / `коротко` return a local shortened
  version of the last assistant response.
- `скажи проще` / `объясни проще` return the same kind of safe local trimming
  with a simpler prefix.

## Safety Behavior

The last voice command is never executed automatically. Repeat only displays or
speaks text. Risky command replay remains unavailable.

All speech goes through `VoiceOutputManager.speak(...)` and respects:

- `OFF`
- `DRY_RUN`
- `WINDOWS_LOCAL`
- mute
- skip-next
- manual voice dialogue mode controls

Manual voice dialogue does not auto-speak these control command responses, which
prevents repeat loops.

Clarify/shorten does not use AI reasoning yet. It takes the first sentence when
safe, or trims the previous response to a fixed character limit. The response is
marked as local trimming without AI rephrasing.

## Boundaries

- No continuous listening.
- No background loops.
- No cloud TTS.
- No external services.
- No generated audio files.
- No voice interaction state persisted to disk.
- No automatic downloads or installs.

## Future Direction

- AI Brain/provider router for real summarization and rephrasing.
- Safe command replay with explicit confirmation.
- Voice interruption for active local speech.
- Richer conversational memory after a separate safety design.
