# TASK-034 - One-Shot Capture to Vosk Recognition Bridge

## Goal

Add a safe bridge layer that prepares the future connection between explicit one-shot microphone capture and local Vosk recognition without enabling real microphone capture or real speech recognition in `run.py`.

## Why This Step Exists

The project already has one-shot capture foundations and a Vosk readiness gate. TASK-034 adds the coordinator between those pieces so future work can be small and controlled.

## Architecture

- New module: `voice/one_shot_vosk_recognition_bridge.py`
- Main class: `OneShotVoskRecognitionBridge`
- Result dataclass: `OneShotVoskRecognitionBridgeResult`
- The bridge checks Vosk readiness through the existing gate.
- The bridge requires explicit one-shot intent.
- Capture and recognizer dependencies are injected.
- The default bridge does not start a microphone and does not load Vosk.

## Commands Added

- `голосовой мост`
- `мост vosk`
- `one shot vosk`
- `one-shot vosk`
- `проверка голосового моста`
- `тест голосового моста`
- `проверить мост распознавания`
- `мост распознавания`

## Safety Rules

- No automatic microphone start.
- No continuous listening.
- No background listener.
- No real Vosk model load by default.
- No downloads or installs.
- No cloud audio.
- No audio storage by default.
- No execution of recognized text as a command.

## What Was Intentionally Not Changed

- `run.py` was not wired to real microphone-to-Vosk recognition.
- Continuous listening was not connected to recognition.
- Real command execution from recognized text was not enabled.
- No model download, package install, or cloud service was added.

## Tests

Added:

- `tests/unit/test_one_shot_vosk_recognition_bridge.py`

Updated:

- `tests/unit/test_command_processor.py`

## Manual Verification Commands

```powershell
python -m pytest tests/unit/test_one_shot_vosk_recognition_bridge.py
python -m pytest tests/unit/test_one_shot_microphone_capture.py
python -m pytest tests/unit/test_vosk_local_recognition_gate.py
python -m pytest tests/unit/test_vosk_local_recognition_dry_run.py
python -m pytest tests/unit/test_command_processor.py
python -m pytest
.\scripts\health_check.ps1
```

Manual `run.py` check:

```powershell
python run.py
```

Then test:

```text
голосовой мост
мост vosk
тест голосового моста
проверить мост распознавания
статус vosk
тест vosk
помощь
```

## Expected Result

Bridge commands work safely in Russian-first output. They do not start the real microphone, do not use continuous listening, do not load a real Vosk model, do not execute recognized text, and do not send or store real audio.

## Commit Message Suggestion

Add one-shot Vosk recognition bridge
