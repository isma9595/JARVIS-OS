# TASK-032 — Command Smoke Test Polish

## Task ID

TASK-032

## Task title

Command Smoke Test Polish

## Goal

Polish command handling based on the live `run.py` smoke test after TASK-031.

## Smoke test findings

- `привет` was not recognized as a greeting.
- `что ты запомнил` was not recognized, even though memory save/count worked.
- `сколько идей` was not recognized, even though idea list commands worked.
- `помощь` still described voice as future-only, although microphone mode and Vosk command layers exist.
- `тест vosk` was too verbose and repeated safety details.
- Empty input stayed safe and should remain covered by tests.

## What was fixed

- Added Russian greeting aliases: `привет`, `здравствуй`, `здравствуйте`, `салам`, `ассаламу алейкум`.
- Added memory recall aliases: `что ты запомнил`, `покажи что ты запомнил`, `что в памяти`, `локальная память`.
- Kept `покажи память` working and covered by tests.
- Added idea count aliases: `сколько идей`, `количество идей`, `сколько сохранено идей`.
- Updated help text for current profile, system status, memory, ideas, action safety, microphone mode, Vosk setup/status/path, Vosk dry run, and voice command simulation support.
- Shortened user-facing Vosk dry-run response while preserving safety statements.
- Kept empty input safe.

## What was intentionally not changed

- No real speech recognition was enabled.
- No microphone capture was started.
- One-shot microphone capture was not connected to real Vosk recognition.
- CONTINUOUS mode was not connected to real recognition.
- Vosk models are not downloaded, installed, or loaded in tests.
- Memory manager, idea manager, voice modules, `run.py`, and architecture were not rewritten.

## Safety rules

- Command polish only.
- No automatic downloads or installs.
- No background listeners.
- No infinite loops.
- No audio storage by default.
- No cloud audio processing.
- No commits or pushes without user verification and explicit approval.

## Russian-first behavior

- New command aliases and user-facing responses are Russian-first.
- Internal code names remain English where that matches existing project style.
- Future multilingual support remains possible through alias/response boundaries.

## Tests

Updated `tests/unit/test_command_processor.py` to cover:

- `привет`
- `салам`
- `что ты запомнил`
- empty memory recall
- `покажи память`
- `сколько идей`
- `количество идей`
- updated `помощь`
- updated `что ты умеешь`
- concise `тест vosk`
- dry-run safety statements for no microphone and no real model
- empty input safety
- existing command processor behavior

## Manual verification commands

```powershell
python -m pytest tests/unit/test_command_processor.py
python -m pytest tests/unit/test_vosk_local_recognition_dry_run.py
python -m pytest
.\scripts\health_check.ps1
```

## Expected result

- JARVIS recognizes common Russian greetings.
- JARVIS can show what it remembered.
- JARVIS can answer how many ideas are saved.
- Help text matches current capabilities.
- Vosk dry-run response is shorter and not repetitive.
- No real recognition starts.
- No microphone capture starts.
- Full test suite passes.
- Health check passes.
- Commit happens only after user verification.

## Commit message suggestion

Polish command smoke test responses
