# TASK-016 — Local Speech Recognition Backend Research & Adapter Interface

## Роль Codex

Ты инженер-исполнитель проекта JARVIS OS.

Архитектурные решения не принимаешь самостоятельно.
Работаешь строго по задаче.

## Главный архитектурный принцип

JARVIS OS должен всегда оставаться расширяемой платформой.

Speech Recognition слой должен быть построен так, чтобы в будущем можно было добавить:

- локальное распознавание речи;
- Vosk;
- Whisper local;
- Windows Speech Recognition;
- wake word;
- real microphone streaming;
- offline voice commands;
- голосовое подтверждение действий;
- разные уровни доступа;
- screen awareness;
- workflow automation;
- плагины.

Любое изменение должно сохранять модульность проекта.

## Цель

Добавить интерфейс для будущих локальных backend распознавания речи.

На этом этапе JARVIS НЕ должен реально распознавать речь.

Он должен только:

- иметь отдельный backend-интерфейс для speech-to-text;
- иметь безопасный backend по умолчанию: NoSpeechRecognitionBackend;
- позволять MicrophoneInputAdapter работать через backend-интерфейс;
- сохранить текущую безопасность микрофона;
- не использовать внешние библиотеки;
- не включать реальный микрофон;
- не записывать звук;
- не отправлять данные в интернет.

## Почему это нужно

Сейчас JARVIS имеет:

- VoiceInputManager;
- simulated voice commands;
- MicrophoneInputAdapter.

Но пока нет отдельного слоя speech-to-text backend.

TASK-016 должен создать этот слой, чтобы позже можно было подключить реальный локальный backend без переписывания архитектуры.

## Приватность и безопасность

Голос пользователя является чувствительными данными.

В этой задаче запрещено:

- включать микрофон;
- записывать аудио;
- сохранять аудио;
- отправлять аудио в интернет;
- использовать облачные API;
- использовать внешние библиотеки;
- использовать pyaudio;
- использовать speech_recognition;
- использовать whisper;
- использовать vosk;
- выполнять реальные системные команды;
- удалять файлы пользователя.

Backend по умолчанию должен быть безопасным и ничего не слушать.

## Разрешённые зоны изменений

Можно изменять или создавать только:

- voice/
- voice/speech_recognition_backend.py
- voice/microphone_input_adapter.py
- voice/voice_input_manager.py
- voice/__init__.py
- core/command_processor.py
- core/kernel.py
- dialogue/dialogue_manager.py
- tests/unit/
- docs/
- .ai/tasks/

Можно создать:

- tests/unit/test_speech_recognition_backend.py
- docs/VOICE_BACKEND_RESEARCH.md

Можно обновить:

- tests/unit/test_microphone_input_adapter.py
- tests/unit/test_voice_input_manager.py
- tests/unit/test_command_processor.py
- tests/unit/test_dialogue_manager.py
- tests/unit/test_kernel.py

## Запрещено

Нельзя:

- менять brain;
- менять memory;
- менять users;
- менять security;
- менять integrations;
- менять vision;
- менять ideas;
- реализовывать настоящий микрофон;
- реализовывать настоящий speech-to-text;
- реализовывать screen awareness;
- реализовывать workflow automation;
- реализовывать installer;
- реализовывать embeddings;
- реализовывать vector database;
- использовать внешние библиотеки;
- использовать pyaudio;
- использовать speech_recognition;
- использовать whisper;
- использовать vosk;
- записывать звук;
- отправлять данные пользователя в интернет;
- выполнять реальные системные команды;
- удалять файлы пользователя.

## Нужно реализовать

### 1. SpeechRecognitionBackend interface

Создать файл:

voice/speech_recognition_backend.py

Создать классы:

- SpeechRecognitionBackend
- NoSpeechRecognitionBackend

SpeechRecognitionBackend должен быть базовым интерфейсом для будущих backend.

Методы:

- get_name()
- is_available()
- requires_permission()
- requires_installation()
- get_status()
- recognize_once()
- supports_streaming()
- supports_offline()
- get_description()

### 2. SpeechRecognitionBackend behavior

Базовый SpeechRecognitionBackend не должен реально распознавать речь.

Если метод recognize_once() вызван напрямую, он должен возвращать безопасный результат:

```python
{
    "backend": "base",
    "available": False,
    "text": "",
    "confidence": 0.0,
    "intent": "speech.backend.not_implemented",
    "should_exit": False,
    "message": "Speech recognition backend is not implemented yet."
}