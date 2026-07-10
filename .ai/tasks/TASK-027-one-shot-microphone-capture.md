# TASK-027 - One-Shot Microphone Capture

## Task ID

TASK-027

## Task title

One-Shot Microphone Capture

## Goal

Add a safe one-shot microphone capture foundation to JARVIS-OS without enabling
always-on listening, startup capture, continuous capture, Vosk recognition, or
background listeners.

## What was added

- `voice/one_shot_microphone_capture.py`
  - `OneShotMicrophoneCapture`
  - `OneShotCaptureResult`
  - `SoundDeviceOneShotCaptureAdapter`
  - safe defaults: 5 seconds by default, 15 seconds hard maximum
- exports in `voice/__init__.py`
- unit tests in `tests/unit/test_one_shot_microphone_capture.py`
- Russian documentation:
  - `docs/ONE_SHOT_MICROPHONE_CAPTURE.md`
  - updated `docs/MICROPHONE_LISTENING_MODES.md`

## What was intentionally not enabled

- no automatic microphone capture on startup;
- no always-on listening;
- no continuous real microphone capture;
- no Vosk activation;
- no speech recognition;
- no background listeners, background threads, or infinite loops;
- no automatic dependency installation or downloads;
- no audio files saved by default;
- no cloud sending.

## Safety rules

- One-shot capture runs only when `capture_once()` is explicitly called.
- Construction, import, status checks, availability checks, and mode switching do
  not capture audio.
- Duration is validated before capture.
- `OFF` rejects capture.
- `PARTIAL` permits one bounded explicit capture.
- `CONTINUOUS` remains a safe state and does not start real continuous capture.
- Missing or unavailable audio dependencies return a safe result instead of
  crashing.

## Russian-first behavior

User-facing messages are Russian-first:

- `Одноразовый захват микрофона недоступен: не найден аудиоадаптер.`
- `Одноразовый захват микрофона завершен.`
- `Микрофон не был запущен автоматически.`
- `Реальное распознавание речи пока не активировано.`

## Tests

Added tests verify:

- construction does not open the microphone;
- availability/status checks do not capture audio;
- default duration is safe;
- over-limit and invalid durations are rejected;
- fake one-shot capture succeeds;
- unavailable adapters return a safe Russian message;
- only one fake capture call is made;
- no background thread is started;
- Vosk recognition is not called;
- `OFF`, `PARTIAL`, and `CONTINUOUS` mode safety is preserved.

## Manual verification commands

```powershell
python -m pytest tests/unit/test_one_shot_microphone_capture.py
python -m pytest tests/unit/test_microphone_listening_modes.py
python -m pytest tests/unit/test_microphone_input_adapter.py
python -m pytest tests/unit/test_command_processor.py
python -m pytest
.\scripts\health_check.ps1
```

## Expected result

JARVIS-OS has a safe one-shot microphone capture foundation. One-shot capture is
explicit and bounded. No automatic microphone capture starts. No continuous
listening starts. No Vosk recognition starts. Tests and health check pass before
commit.

## Commit message suggestion

Add one-shot microphone capture
