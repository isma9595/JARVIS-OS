# TASK-023 - Real Vosk Speech Recognition Bootstrap

## Goal

Prepare the safe Vosk skeleton for local speech recognition readiness checks
without enabling uncontrolled microphone recognition, runtime loading, package
installation, or model download.

## Added

- Explicit Vosk package availability reporting.
- Explicit model path configured and model path exists reporting.
- Backend readiness reporting for future real recognition prerequisites.
- Clear missing requirement reporting.
- Runtime loader status fields that expose readiness while keeping the runtime
  unloaded.
- Unit tests for missing package, missing model path, missing model directory,
  preserved skeleton behavior, and disabled recognition boundaries.

## Intentionally Disabled

- Real Vosk runtime loading.
- Vosk model loading.
- Microphone access.
- Audio recording or audio file recognition.
- Automatic package installation.
- Automatic model download.
- Always-on listening.

## Safety Rules

TASK-023 is readiness/bootstrap only. Even when all safe prerequisites are
present, `real_recognition_enabled` remains `false`, `microphone_enabled`
remains `false`, and `recognize_once()` continues to return the safe unavailable
response.

## Verification Commands

```powershell
python -m pytest tests/unit/test_vosk_local_backend.py
python -m pytest tests/unit/test_vosk_runtime_loader.py
python -m pytest tests/unit/test_vosk_settings_manager.py
python -m pytest
.\scripts\health_check.ps1
```

## Expected Result

- All targeted Vosk unit tests pass.
- The full test suite passes.
- Health check passes when run by the user.
- JARVIS reports readiness information but does not listen, record audio,
  install packages, download models, load Vosk, or recognize speech.
- Commit is created only after user verification.
