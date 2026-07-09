# TASK-017 — Vosk Local Backend Skeleton

## Роль Codex

Ты инженер-исполнитель проекта JARVIS OS.

Архитектурные решения не принимаешь самостоятельно.
Работаешь строго по задаче.

## Главный архитектурный принцип

JARVIS OS должен всегда оставаться расширяемой платформой.

Vosk backend должен быть построен так, чтобы в будущем можно было безопасно добавить:

- локальное распознавание речи;
- Vosk model;
- offline speech-to-text;
- real microphone streaming;
- wake word;
- голосовое подтверждение;
- разные уровни доступа;
- screen awareness;
- workflow automation;
- плагины.

Любое изменение должно сохранять модульность проекта.

## Цель

Добавить безопасный skeleton для будущего Vosk local backend.

На этом этапе JARVIS НЕ должен реально распознавать речь.

Он должен только:

- иметь отдельный класс VoskLocalBackend;
- реализовать общий SpeechRecognitionBackend interface;
- сообщать, что Vosk backend пока не установлен/не подключён;
- позволять выбрать Vosk skeleton как backend;
- не импортировать vosk;
- не устанавливать библиотеки;
- не скачивать модели;
- не включать микрофон;
- не записывать звук;
- не отправлять данные в интернет.

## Запрещено

Нельзя:

- использовать import vosk;
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

- voice/vosk_local_backend.py
- tests/unit/test_vosk_local_backend.py
- docs/VOSK_BACKEND_PLAN.md

Можно обновить:

- voice/__init__.py
- voice/speech_recognition_backend.py
- voice/microphone_input_adapter.py
- voice/voice_input_manager.py
- tests/unit/test_speech_recognition_backend.py
- tests/unit/test_microphone_input_adapter.py
- tests/unit/test_voice_input_manager.py
- tests/unit/test_command_processor.py
- tests/unit/test_dialogue_manager.py
- tests/unit/test_kernel.py

## Нужно реализовать

### 1. VoskLocalBackend skeleton

Создать файл:

voice/vosk_local_backend.py

Создать класс:

VoskLocalBackend

Он должен наследоваться от SpeechRecognitionBackend.

Поля:

- model_path
- language
- installed
- model_available
- backend_name

Значения по умолчанию:

```python
backend_name = "vosk_local"
language = "ru"
model_path = None
installed = False
model_available = False