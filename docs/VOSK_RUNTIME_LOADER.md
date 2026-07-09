# Vosk Safe Runtime Loader

`VoskRuntimeLoader` is an architectural stub. It reports prerequisite
readiness by using the existing local backend preflight, but it never loads a
runtime or model and never performs speech recognition.

## Guarantees in TASK-021

- `runtime_loaded` is always `false`.
- Real recognition and microphone access are always disabled.
- No audio is recorded or opened.
- No network access, package installation, model download, virtual environment
  creation, or Python environment mutation is performed.
- `prepare_runtime_stub()` checks readiness and returns blockers only.
- `recognize_text_stub()` always returns a disabled response.

The stub separates dependency/model readiness from runtime activation. A future
real loader requires a separately reviewed and explicitly authorized task.

## Commands

- `статус runtime vosk`
- `блокировки runtime vosk`
- `безопасность runtime vosk`
- `подготовить runtime vosk`
- `распознать через vosk` (always disabled)
