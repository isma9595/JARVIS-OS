# Voice Recognition Typed Simulation

TASK-043 adds a typed simulation command for the voice recognition pipeline.

This exists because live microphone and Vosk tests can be unreliable even when the command safety logic is working. Typed simulation lets a user provide recognized text manually and send it through the same safe pipeline used after one-shot Vosk recognition.

## Commands

- `симулируй распознавание: <текст>`
- `симуляция распознавания: <текст>`
- `тест распознавания: <текст>`
- `тестовое распознавание: <текст>`
- `проверить голосовую команду: <текст>`
- `проверь голосовую команду: <текст>`

Examples:

- `симулируй распознавание: статус системы`
- `симулируй распознавание: открой браузер`
- `тестовое распознавание: статуя система`

If text is empty, JARVIS responds:

`Укажите текст для симуляции распознавания.`

## Safety

Typed simulation does not use the microphone, does not use Vosk, does not load a model, does not store audio, and does not send audio or text to a cloud service.

It does not bypass safety. Simulated text still goes through:

- session recognition corrections
- safe read-only voice command allowlist
- pending confirmation for unknown or risky commands
- `CommandProcessor`
- `ActionRouter`
- in-memory voice command history

Safe read-only allowlisted commands may execute automatically. Unknown or risky commands still require `да / нет` confirmation and then continue through the normal safe processing path.

## What It Tests

Typed simulation is useful for testing:

- safe allowlist behavior
- pending confirmation
- risky command safety behavior
- session-only recognition corrections
- correction history
- last recognition and voice command history

It is not a substitute for real microphone testing. It validates the command pipeline after recognized text exists.
