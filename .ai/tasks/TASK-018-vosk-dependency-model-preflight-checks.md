# TASK-018 — Vosk Dependency & Model Preflight Checks

## Роль Codex

Ты инженер-исполнитель проекта JARVIS OS.

Архитектурные решения не принимаешь самостоятельно.
Работаешь строго по задаче.

## Главный архитектурный принцип

JARVIS OS должен всегда оставаться расширяемой платформой.

Vosk preflight слой должен быть построен так, чтобы в будущем можно было безопасно добавить:

- локальное распознавание речи;
- проверку установленной зависимости Vosk;
- проверку локальной модели;
- offline speech-to-text;
- real microphone streaming;
- wake word;
- голосовое подтверждение;
- разные уровни доступа;
- плагины;
- screen awareness;
- workflow automation.

Любое изменение должно сохранять модульность проекта.

## Цель

Добавить безопасные preflight-проверки для будущего Vosk backend.

На этом этапе JARVIS НЕ должен реально распознавать речь.

Он должен только:

- проверять, доступен ли пакет vosk через безопасную проверку importlib.util.find_spec();
- НЕ импортировать настоящий vosk;
- НЕ устанавливать зависимости;
- НЕ скачивать модели;
- проверять, указан ли путь к модели;
- безопасно проверять существование папки модели, если путь указан;
- объяснять, чего не хватает для подключения Vosk;
- позволять указать путь к модели только в памяти процесса;
- сохранить совместимость с VoskLocalBackend skeleton;
- сохранить безопасность микрофона.

## Запрещено

Нельзя:

- использовать import vosk;
- использовать from vosk import ...;
- использовать pyaudio;
- использовать speech_recognition;
- использовать whisper;
- устанавливать зависимости;
- скачивать модели;
- включать реальный микрофон;
- записывать звук;
- отправлять данные в интернет;
- выполнять реальные системные команды;
- удалять файлы пользователя;
- реализовывать настоящий speech-to-text;
- реализовывать screen awareness;
- реализовывать workflow automation;
- реализовывать installer;
- реализовывать embeddings;
- реализовывать vector database.

## Разрешённые зоны изменений

Можно изменять или создавать только:

- voice/
- core/command_processor.py
- dialogue/dialogue_manager.py
- tests/unit/
- docs/
- .ai/tasks/

Можно создать:

- docs/VOSK_PREFLIGHT.md

Можно обновить:

- voice/vosk_local_backend.py
- voice/microphone_input_adapter.py
- voice/voice_input_manager.py
- voice/__init__.py
- tests/unit/test_vosk_local_backend.py
- tests/unit/test_microphone_input_adapter.py
- tests/unit/test_voice_input_manager.py
- tests/unit/test_command_processor.py
- tests/unit/test_dialogue_manager.py
- tests/unit/test_kernel.py
- docs/VOSK_BACKEND_PLAN.md

## Нужно реализовать

### 1. VoskLocalBackend preflight

Обновить файл:

voice/vosk_local_backend.py

Добавить методы:

- check_dependency_available()
- check_model_path_configured()
- check_model_path_exists()
- preflight_check()
- get_preflight_summary()
- get_missing_requirements()
- configure_model_path(model_path)

### 2. check_dependency_available()

Метод должен проверять наличие пакета vosk безопасно:

```python
import importlib.util
importlib.util.find_spec("vosk") is not None