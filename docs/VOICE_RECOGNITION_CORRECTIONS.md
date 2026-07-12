# Voice Recognition Corrections

TASK-042 adds a session-only correction flow for local voice recognition mistakes.

The user can explicitly tell JARVIS that one recognized phrase should be treated as another phrase during the current session:

- `я сказал не статуя система, а статус системы`
- `исправь распознавание: статуя система -> статус системы`

Corrections are held only in memory. They are not written to disk, not sent to a cloud service, and do not store audio.

## Safety

Corrections do not bypass command safety.

If Vosk returns a phrase that matches a session correction, JARVIS shows both values:

- original recognized text
- corrected session text

The corrected text is then processed through the existing `CommandProcessor` and `ActionRouter` flow.

Safe read-only corrected commands may auto-execute only when they are explicitly allowlisted. Risky or unknown corrected commands still require confirmation.

Example:

- `статуя система -> статус системы` may auto-execute if `статус системы` is allowlisted.
- `браузер -> открой браузер` still requires confirmation and safety processing.

## Commands

Add:

- `я сказал не <wrong>, а <correct>`
- `я говорил не <wrong>, а <correct>`
- `исправь распознавание: <wrong> -> <correct>`
- `исправь голос: <wrong> -> <correct>`
- `это не <wrong>, это <correct>`

View:

- `голосовые исправления`
- `список голосовых исправлений`
- `покажи исправления распознавания`
- `сколько голосовых исправлений`

Clear:

- `очистить голосовые исправления`
- `очисти исправления распознавания`
- `сбросить голосовые исправления`

## Future Direction

- Reviewed persistent corrections.
- User-approved safe custom aliases.
- Confidence scoring for recognition results.
