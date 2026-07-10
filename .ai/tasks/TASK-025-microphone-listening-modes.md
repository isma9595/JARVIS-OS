# TASK-025 - Microphone Listening Modes

## Task ID

TASK-025

## Task Title

Microphone Listening Modes

## Goal

Add safe microphone listening mode architecture so JARVIS-OS can represent
`OFF`, `PARTIAL`, and `CONTINUOUS` microphone states without enabling real
always-on listening.

## What Was Added

- `voice.microphone_listening_modes.MicrophoneListeningMode`
- `voice.microphone_listening_modes.MicrophoneListeningModeManager`
- safe mode switching for `OFF`, `PARTIAL`, and `CONTINUOUS`
- validation for allowed mode names
- status helpers for listening, limited listening, continuous mode, explicit
  activation, and microphone capture
- unit tests for the new mode manager
- Russian documentation for microphone listening modes

## What Was Intentionally Not Enabled

- no real microphone capture
- no automatic microphone startup
- no background listener
- no infinite listening loop
- no Vosk continuous recognition
- no command processing changes
- no automatic downloads or installs

## Safety Rules

- default mode is `OFF`;
- `OFF` does not allow listening;
- `PARTIAL` is only a controlled one-command state;
- `CONTINUOUS` is only a safe state flag in this task;
- `PARTIAL` and `CONTINUOUS` require explicit user activation;
- switching modes never starts microphone capture;
- invalid mode names are rejected without changing the current state.

## Tests

Added:

- `tests/unit/test_microphone_listening_modes.py`

Coverage includes:

- default mode is `OFF`;
- `OFF` does not allow listening;
- `PARTIAL` allows limited listening state;
- `CONTINUOUS` is marked as continuous;
- `CONTINUOUS` requires explicit activation;
- switching between modes works;
- invalid mode names are rejected safely;
- mode switching does not start microphone capture.

## Manual Verification Commands

```powershell
python -m pytest
.\scripts\health_check.ps1
```

## Expected Result

- JARVIS-OS has safe microphone listening mode architecture.
- Default microphone mode is `OFF`.
- `PARTIAL` and `CONTINUOUS` modes exist as controlled states.
- No real continuous listening starts.
- Full test suite passes.
- Health check passes.
- Commit happens only after user verification.

## Commit Message Suggestion

```text
Add safe microphone listening modes
```
