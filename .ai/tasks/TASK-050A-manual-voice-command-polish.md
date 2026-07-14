# TASK-050A - Manual Voice Command Polish

## Task

- Task ID: TASK-050A
- Title: Manual Voice Command Polish
- Base stable task: TASK-050 - Voice Cycle Final Polish / Stability Review
- Base stable commit: 9a5bc6b
- Base stable commit message: Finalize voice cycle polish

## Manual Issues Found

1. `выключить микрофон` was not recognized as a microphone command.
2. `частичный режим микрофона` was not recognized as a microphone command.
3. `проверить готовность модели vosk` was not recognized as a Vosk readiness alias.
4. Empty input response `Исмаил, я не услышал команду. Повторите, пожалуйста.` could become the last meaningful response and appear in response history.

## Fixes

- Added explicit microphone OFF aliases:
  - `выключить микрофон`
  - `отключить микрофон`
  - `микрофон выключить`
  - `микрофон off`
  - `mic off`
- Added explicit PARTIAL microphone mode aliases:
  - `частичный режим микрофона`
  - `включить частичный режим микрофона`
  - `микрофон частично`
  - `partial microphone mode`
  - `mic partial`
- Added Vosk readiness alias:
  - `проверить готовность модели vosk`
- Marked empty typed input as non-speakable and non-history so it does not overwrite the last meaningful assistant response.
- Added explicit safe voice allowlist mappings for the new Vosk and microphone aliases.

## Safety Boundaries

- No continuous listening added.
- No background loops added.
- No autonomous execution added.
- No safe action model changes.
- No CommandProcessor, ActionRouter, VoiceOutputManager, or VoiceOutputSafetyController bypass.
- No cloud services.
- No audio files saved.
- No new voice state persisted to disk.
- No installs or downloads.
- No commit or push.

## Tests

Updated unit coverage for:

- Microphone OFF aliases.
- Microphone PARTIAL aliases.
- Vosk readiness alias.
- Empty input not becoming last response.
- Empty input not entering response history.
- Empty input not being spoken by manual voice dialogue.
- Safe voice allowlist mappings for the new aliases.

## Manual Verification Commands

```text
python run.py

последний ответ

статус системы
последний ответ

выключить микрофон
режим микрофона
частичный режим микрофона
режим микрофона
выключить микрофон
режим микрофона

проверить готовность модели vosk

безопасные голосовые команды

включить тестовый голос
включить голосовой диалог

статус системы

выключить голос

история ответов
последний ответ
помощь
выход
```

Also press Enter on an empty prompt before `последний ответ`.

Expected:

- Empty prompt still returns `я не услышал команду`.
- Empty prompt does not overwrite the last meaningful response.
- Empty prompt does not appear as a meaningful repeat target.
- Empty prompt is not spoken in manual voice dialogue.

## Expected Result

- All relevant tests pass.
- Health check passes.
- `git status` shows only TASK-050A-scoped files changed.
- No commit or push is performed.

## Commit Message Suggestion

```text
Polish manual voice commands
```
