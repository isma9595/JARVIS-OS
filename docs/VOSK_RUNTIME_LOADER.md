# Vosk Safe Runtime Loader

`VoskRuntimeLoader` is an architectural stub. It reports prerequisite
readiness by using the existing local backend preflight, but it never loads a
runtime or model and never performs speech recognition.

## TASK-028: gate локального распознавания

TASK-028 добавляет отдельный безопасный gate:
`voice.vosk_local_recognition_gate`.

Gate проверяет доступность пакета `vosk`, наличие настроенного пути к модели,
существование пути и то, что путь является папкой. Также он фиксирует
обязательные условия безопасности: требуется явное разрешение пользователя,
микрофон не запускается автоматически, а режим `CONTINUOUS` пока не связан с
реальным распознаванием.

Gate не импортирует Vosk, не загружает модель, не вызывает one-shot захват, не
запускает постоянное прослушивание и не создает фоновые потоки.

Подробная инструкция по ручной подготовке модели находится в
`docs/VOSK_MODEL_SETUP.md`.

## Guarantees in TASK-021 through TASK-023

- `runtime_loaded` is always `false`.
- Real recognition and microphone access are always disabled.
- No audio is recorded or opened.
- No network access, package installation, model download, virtual environment
  creation, or Python environment mutation is performed.
- `prepare_runtime_stub()` checks readiness and returns blockers only.
- `recognize_text_stub()` always returns a disabled response.

The stub separates dependency/model readiness from runtime activation. A future
real loader requires a separately reviewed and explicitly authorized task.

## TASK-023 Readiness Fields

The runtime status reports these side-effect-free readiness values:

- `vosk_package_available`
- `dependency_available`
- `model_path_configured`
- `model_path_exists`
- `backend_ready_for_real_recognition`
- `missing_requirements`
- `recognition_disabled_reason`

`backend_ready_for_real_recognition` means only that the local prerequisites are
present. It does not mean that Vosk has been imported, that a model has been
loaded, or that microphone recognition is enabled.

## Commands

- `статус runtime vosk`
- `блокировки runtime vosk`
- `безопасность runtime vosk`
- `подготовить runtime vosk`
- `распознать через vosk` (always disabled)
