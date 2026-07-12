# TASK-040 - Conservative Voice Command Normalization & Safe Aliases

## Goal

Improve recognition robustness for safe voice commands by adding conservative normalization and explicit safe alias mapping.

## Context

TASK-039 added the Safe Voice Command Allowlist. JARVIS can auto-execute known safe read-only voice commands, while unknown or risky commands still require confirmation.

Manual live testing showed Vosk can recognize `статус системы` as close variants such as `статуя система`. TASK-040 keeps that safety behavior but maps a small set of known read-only variants to their canonical commands.

## Safe alias examples

- `статус систем` -> `статус системы`
- `статусе системы` -> `статус системы`
- `статуя система` -> `статус системы`
- `помоги` -> `помощь`
- `справка` -> `помощь`
- `статус воска` -> `статус vosk`
- `проверка аудио зависимости` -> `проверка аудио зависимостей`
- `как твое имя` -> `как тебя зовут`

## Safety boundaries

- No broad fuzzy matching.
- No auto-correction for unknown or risky commands.
- No auto-execution of modifying commands.
- No bypass of `CommandProcessor` or `ActionRouter`.
- No continuous listening.
- No background microphone listener.
- No cloud audio.
- No audio saving by default.
- No automatic downloads or installs.

Commands such as `открой браузер`, `удали файл`, `запомни это`, `скачай`, `установи`, `запусти`, `выполни powershell`, `cmd`, and `отправь письмо` must stay outside the safe allowlist.

## Tests

Update unit coverage for:

- exact canonical allowlist matches
- explicit safe aliases
- normalization of spaces, case, `ё` / `е`, and punctuation
- risky commands remaining non-allowlisted
- no broad fuzzy matching
- one-shot recognition auto-execution for safe aliases
- pending confirmation for unknown or risky recognized text
- allowlist status response explaining aliases and safety boundaries

## Manual verification commands

```powershell
python -m pytest tests/unit/test_voice_command_allowlist.py
python -m pytest tests/unit/test_voice_command_confirmation_flow.py
python -m pytest tests/unit/test_command_processor.py
python -m pytest
.\scripts\health_check.ps1
git status
```

Manual run:

```powershell
python run.py
```

Then test:

- `список безопасных голосовых команд`
- `распознай голос один раз`, say `статус системы`
- `распознай голос один раз`, try a variant that Vosk may recognize as `статуя система`
- `распознай голос один раз`, say `открой браузер`
- `нет`
- `выход`

## Expected result

Known safe aliases auto-execute the canonical read-only command. Unknown and risky commands still require confirmation. There is no broad guessing, continuous listening, background listener, cloud audio, or audio saving.

## Commit message suggestion

Add conservative voice command normalization
