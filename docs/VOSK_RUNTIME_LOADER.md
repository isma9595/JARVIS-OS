## TASK-031: safe dry run

TASK-031 добавляет отдельный пробный запуск локального распознавания Vosk. Это
не runtime loader и не реальное распознавание. Dry run использует существующий
gate готовности и fake/stub recognizer с тестовыми данными.

Команды dry run:

- `пробный запуск vosk`
- `тест vosk`
- `тест распознавания`
- `пробное распознавание`
- `проверить локальное распознавание`
- `dry run vosk`

Даже при успешном dry run `VoskRuntimeLoader` остается безопасной заглушкой:
runtime не загружается, настоящая модель Vosk не открывается, микрофон не
запускается, one-shot захват не вызывается, `CONTINUOUS` не подключается к
реальному распознаванию, аудио не пишется на диск и не отправляется наружу.

Подробности: `docs/VOSK_LOCAL_RECOGNITION_DRY_RUN.md`.

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

## TASK-029: ручные команды статуса и настройки

TASK-029 подключает русские текстовые команды к безопасной проверке готовности
Vosk. Команды `статус vosk`, `проверить vosk`, `готово ли распознавание` и
другие команды статуса возвращают русское объяснение gate: разрешено ли
локальное распознавание, какие есть блокировки, предупреждения и следующие
ручные шаги.

Команды `как настроить vosk`, `инструкция vosk` и `настройка распознавания`
возвращают только ручную инструкцию. JARVIS не устанавливает пакеты, не
скачивает модели, не загружает runtime, не запускает микрофон и не подключает
режим `CONTINUOUS` к реальному распознаванию.

Команды `путь модели vosk` и `где модель vosk` только читают текущий
настроенный путь, если он есть. Если путь не настроен, JARVIS сообщает, что
путь к модели Vosk пока не указан.

## TASK-030: команды настройки пути модели

TASK-030 добавляет русские команды для безопасной ручной настройки пути к
локальной папке модели Vosk:

- `установи путь модели vosk <path>`
- `задай путь модели vosk <path>`
- `измени путь модели vosk <path>`
- `сохрани путь модели vosk <path>`
- `путь модели vosk <path>`
- `очисти путь модели vosk`
- `сбрось путь модели vosk`
- `удали путь модели vosk`

Эти команды используют существующий менеджер настроек Vosk. Они могут сохранить
строковое значение пути, проверить, существует ли папка, и очистить сохраненное
значение. Runtime-loader при этом не загружается: Vosk не импортируется, модель
не открывается, микрофон не запускается, one-shot захват не вызывается, режим
`CONTINUOUS` не подключается к реальному распознаванию.

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
