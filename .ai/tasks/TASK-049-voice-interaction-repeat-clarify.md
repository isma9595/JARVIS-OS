# TASK-049 — Voice Dialogue Repeat / Clarify / Last Voice Interaction Controls

## Goal

Add safe repeat, clarify, and last voice interaction controls for JARVIS.

## Context

TASK-048 completed voice output safety controls:

- mute / stop
- unmute
- skip next speech
- safety status

Current stable commit: `3b45d93`
Commit message: `Add voice output safety controls`

## Commands Added

- `что ты сказал`
- `что ты ответил`
- `повтори текстом`
- `повтори`
- `повтори голосом`
- `скажи ещё раз`
- `что я сказал`
- `что ты услышал`
- `последняя голосовая команда`
- `повтори последнюю голосовую команду`
- `объясни короче`
- `скажи проще`

## Safety Boundaries

- No continuous listening.
- No background loops.
- No automatic replay or execution of the last voice command.
- No bypass of `CommandProcessor`, `ActionRouter`, `VoiceOutputManager`, or
  `VoiceOutputSafetyController`.
- No cloud TTS.
- No external service calls.
- No generated audio files.
- No persisted voice interaction state.
- No automatic downloads or installs.

## Tests

Added:

- `tests/unit/test_voice_interaction_controls.py`

Updated:

- `tests/unit/test_command_processor.py`
- `tests/unit/test_voice_command_allowlist.py`

## Manual Verification Commands

```powershell
python run.py
```

Then test:

```text
что ты сказал
статус системы
что ты сказал
повтори
включить тестовый голос
повтори
замолчи
повтори
снова говори
не озвучивай следующий ответ
повтори
повтори
симулируй распознавание: статус системы
что я сказал
повтори последнюю голосовую команду
объясни короче
скажи проще
статус голосовой безопасности
помощь
выход
```

## Expected Result

Repeat and clarify controls work in memory for the current session only.
Voice repeat respects `OFF`, `DRY_RUN`, `WINDOWS_LOCAL`, mute, and skip-next.
Last voice command repeat speaks text only and does not execute the command.
No cloud, no files, no continuous listening.

## Commit Message Suggestion

`Add voice interaction repeat controls`
