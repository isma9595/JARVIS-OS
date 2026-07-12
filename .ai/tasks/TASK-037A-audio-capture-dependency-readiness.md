# TASK-037A: Audio Capture Dependency Readiness

- Task ID: TASK-037A
- Title: Audio Capture Dependency Readiness
- Goal: Add safe Russian-first diagnostics for local audio capture dependencies used by real one-shot Vosk recognition.

## Context

TASK-037 added first real one-shot Vosk recognition. The real `run.py` test successfully captured audio once and recognized speech locally through Vosk. A crash related to NumPy array truthiness was fixed and committed in `f0d429b`.

## Commands Added

- `проверка аудио зависимостей`
- `проверить аудио зависимости`
- `проверить зависимости микрофона`
- `диагностика микрофона`
- `почему не работает микрофон`
- `проверить numpy`
- `статус numpy`
- `проверить sounddevice`
- `статус sounddevice`
- `проверить vosk пакет`
- `статус vosk пакета`

## Safety Boundaries

- No automatic package installs.
- No automatic downloads.
- No continuous listening.
- No background listener.
- No cloud audio.
- No default audio file storage.
- No automatic command execution from recognized text.

## Tests

- `tests/unit/test_audio_dependency_readiness.py`
- `tests/unit/test_command_processor.py`
- `tests/unit/test_one_shot_vosk_real_recognition.py`

## Verification Commands

```powershell
python -m pytest tests/unit/test_audio_dependency_readiness.py
python -m pytest tests/unit/test_one_shot_vosk_real_recognition.py
python -m pytest tests/unit/test_command_processor.py
python -m pytest
.\scripts\health_check.ps1
git status
```

Manual `run.py` verification:

```powershell
python run.py
```

Then test:

```text
проверка аудио зависимостей
проверить зависимости микрофона
диагностика микрофона
почему не работает микрофон
проверить numpy
проверить sounddevice
проверить vosk пакет
распознай голос один раз
выход
```

## Expected Result

JARVIS explains dependency readiness in Russian, gives manual install commands only when something is missing, does not install anything automatically, and preserves one-shot recognition safety behavior.

## Commit Message Suggestion

`Add audio capture dependency diagnostics`
