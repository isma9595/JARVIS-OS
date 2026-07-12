# TASK-035 — Vosk Model Installation & Readiness Verification

## Goal

Add safe Russian-first Vosk model installation guidance and local model readiness verification.

## Why This Step Exists

The user can already configure a Vosk model path. TASK-035 adds diagnostics for whether that path is missing, invalid, empty, incomplete, or model-like before any future real local recognition task.

## Commands Added

- `проверить модель vosk`
- `готовность модели vosk`
- `диагностика модели vosk`
- `модель vosk статус`
- `проверка модели vosk`
- `проверить установленную модель vosk`
- `как установить модель vosk`
- `инструкция установки модели vosk`
- `куда положить модель vosk`

## Safety Rules

- Do not enable real speech recognition.
- Do not start microphone capture.
- Do not load a real Vosk model.
- Do not import Vosk.
- Do not download anything automatically.
- Do not install packages automatically.
- Do not execute recognized commands.
- Do not connect continuous listening to recognition.

## Intentionally Not Changed

TASK-035 does not connect the one-shot bridge to real recognition, does not create background listeners, does not enable continuous listening, and does not require real model files in tests.

## Tests

```powershell
python -m pytest tests/unit/test_vosk_model_readiness_verifier.py
python -m pytest tests/unit/test_vosk_settings_manager.py
python -m pytest tests/unit/test_vosk_local_recognition_gate.py
python -m pytest tests/unit/test_one_shot_vosk_recognition_bridge.py
python -m pytest tests/unit/test_command_processor.py
python -m pytest
.\scripts\health_check.ps1
```

## Manual Verification Commands

```text
python run.py
как установить модель vosk
инструкция установки модели vosk
куда положить модель vosk
проверить модель vosk
готовность модели vosk
диагностика модели vosk
статус vosk
путь модели vosk
голосовой мост
помощь
выход
```

## Expected Result

JARVIS explains manual model installation, verifies configured model path readiness, detects missing/empty/incomplete/model-like folders, and keeps all output Russian-first. No automatic download or install occurs. No real model loads. No microphone starts. Existing bridge commands still work.

## Commit Message Suggestion

```text
Add Vosk model readiness verification
```
