# TASK-026: Microphone Mode Commands

## Goal

Connect Russian-first text commands to the existing safe microphone listening
mode architecture from TASK-025.

## What Was Added

- Russian text command handling in `CommandProcessor` for microphone mode
  status and switching.
- Safe internal state changes through `MicrophoneListeningModeManager`.
- Russian-first responses for `OFF`, `PARTIAL`, and `CONTINUOUS`.
- Unit tests for status, switching, safety, and unknown command behavior.
- Documentation update in `docs/MICROPHONE_LISTENING_MODES.md`.

## Russian Commands Added

Status:

- `статус микрофона`
- `режим микрофона`
- `какой режим микрофона`
- `микрофон статус`

Switch to `OFF`:

- `выключи микрофон`
- `отключи микрофон`
- `отключи прослушивание`
- `выключи прослушивание`
- `стоп микрофон`

Switch to `PARTIAL`:

- `слушай одну команду`
- `прими голосовую команду`
- `включи частичное прослушивание`
- `режим одной команды`
- `частичное прослушивание`

Switch to `CONTINUOUS`:

- `включи постоянное прослушивание`
- `слушай постоянно`
- `режим постоянного прослушивания`
- `включи постоянный микрофон`

Disable `CONTINUOUS` and return to `OFF`:

- `отключи постоянное прослушивание`
- `выключи постоянное прослушивание`
- `перестань слушать постоянно`

## Intentionally Not Enabled

- Real microphone capture.
- Always-on listening.
- Background listeners, threads, or infinite loops.
- Device access or OS microphone permission requests.
- Vosk recognition or real runtime activation.
- Automatic downloads or installs.

## Safety Rules

- Commands only change internal microphone mode state.
- `CONTINUOUS` is only a safe state flag.
- `PARTIAL` does not start one-shot capture yet.
- Existing adapter commands remain available where they do not conflict with
  TASK-026 approved mode phrases.
- Commit and push are not performed automatically.

## Tests

Added or updated tests in `tests/unit/test_command_processor.py`:

- default status returns `OFF`;
- `OFF` commands switch to `OFF`;
- `PARTIAL` commands switch to `PARTIAL`;
- `CONTINUOUS` commands switch to `CONTINUOUS`;
- disabling continuous returns to `OFF`;
- unknown microphone mode command stays safe;
- mode commands do not call microphone capture or Vosk selection;
- existing non-overlapping microphone adapter behavior remains covered.

## Manual Verification Commands

```powershell
python -m pytest tests/unit/test_microphone_listening_modes.py
python -m pytest tests/unit/test_command_processor.py
python -m pytest
.\scripts\health_check.ps1
```

## Expected Result

JARVIS-OS understands Russian microphone mode commands and switches internal
mode between `OFF`, `PARTIAL`, and `CONTINUOUS` without starting real
microphone capture or Vosk recognition.

## Commit Message Suggestion

```text
Add microphone mode commands
```
