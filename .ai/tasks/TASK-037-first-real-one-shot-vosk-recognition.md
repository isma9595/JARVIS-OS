# TASK-037 - First Real One-Shot Vosk Recognition

## Task ID

TASK-037

## Task Title

First Real One-Shot Vosk Recognition

## Goal

Add the first safe real local one-shot Vosk recognition path.

## Why This Step Exists

Previous tasks prepared Vosk settings, model readiness checks, dry runs, and a
safe bridge. TASK-037 is the first controlled step that may use a real
microphone, but only once and only after an explicit command.

## Commands Added

- `распознай голос один раз`
- `распознай одну голосовую команду`
- `реальное распознавание vosk`
- `запусти распознавание vosk один раз`
- `запусти голосовое распознавание один раз`
- `проверить голос через vosk`
- `тест реального vosk`
- `тест реального распознавания`

## Safety Rules

- Real microphone capture is allowed only for explicit one-shot commands.
- Capture happens once and stops.
- Continuous listening is not connected.
- Background listeners are not started.
- Audio is not sent to cloud services.
- Audio files are not saved by default.
- Vosk and models are not downloaded or installed automatically.
- Recognized text is not executed as a command.
- The local `models/` folder remains ignored and local-only.

## What Was Intentionally Not Changed

- Bridge commands remain dry/safe checks.
- Vosk dry run remains test-data only.
- Continuous listening remains disconnected from real recognition.
- Voice command execution from recognized text is not enabled.
- No commit or push is performed automatically.

## Tests

- `tests/unit/test_one_shot_vosk_real_recognition.py`
- `tests/unit/test_command_processor.py`
- Existing one-shot microphone, Vosk readiness, gate, bridge, and backend tests.

## Manual Verification Commands

```powershell
python -m pytest tests/unit/test_one_shot_vosk_real_recognition.py
python -m pytest tests/unit/test_one_shot_microphone_capture.py
python -m pytest tests/unit/test_vosk_model_readiness_verifier.py
python -m pytest tests/unit/test_vosk_local_recognition_gate.py
python -m pytest tests/unit/test_one_shot_vosk_recognition_bridge.py
python -m pytest tests/unit/test_vosk_local_backend.py
python -m pytest tests/unit/test_command_processor.py
python -m pytest
.\scripts\health_check.ps1
```

Manual `run.py` flow:

```text
python run.py
статус vosk
проверить модель vosk
распознай голос один раз
реальное распознавание vosk
проверить голос через vosk
голосовой мост
помощь
выход
```

## Expected Result

If Vosk and the microphone are available, JARVIS attempts one local recognition
and prints recognized text. If Vosk or the microphone is unavailable, it blocks
or fails safely with a Russian explanation and no crash.

No continuous listening, command execution from recognized text, cloud audio,
or audio-file storage is enabled.

## Commit Message Suggestion

Add first real one-shot Vosk recognition
