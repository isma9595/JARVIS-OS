# TASK-015 — Real Microphone Input Adapter

## Роль Codex

Ты инженер-исполнитель проекта JARVIS OS.

Архитектурные решения не принимаешь самостоятельно.
Работаешь строго по задаче.

## Главный архитектурный принцип

JARVIS OS должен всегда оставаться расширяемой платформой.

Микрофонный ввод должен быть построен так, чтобы в будущем можно было добавить:

- настоящий микрофон;
- локальное распознавание речи;
- wake word;
- Whisper;
- Vosk;
- Windows Speech Recognition;
- offline speech-to-text;
- безопасное голосовое подтверждение;
- разные уровни доступа;
- плагины;
- screen awareness;
- workflow automation.

Любое изменение должно сохранять модульность проекта.

## Цель

Добавить фундамент реального микрофонного адаптера.

На этом этапе JARVIS должен получить отдельный слой:

- MicrophoneInputAdapter

Но важно:

- не использовать облачные API;
- не отправлять голос в интернет;
- не записывать аудио в файл;
- не подключать pyaudio, speech_recognition, whisper, vosk;
- не делать бесконечное прослушивание;
- не выполнять реальные системные действия;
- не ломать существующий VoiceInputManager.

## Почему пока без настоящего распознавания

В Python нет встроенного стандартного безопасного распознавания речи через микрофон.

Поэтому в этой задаче мы создаём архитектурный адаптер:

- он умеет запрашивать разрешение;
- он умеет включать/отключать состояние микрофона;
- он умеет сообщать, что backend распознавания ещё не подключён;
- он готов к будущему подключению локального STT backend;
- он не слушает пользователя тайно.

Реальный backend распознавания будет отдельной задачей после выбора технологии.

## Приватность и безопасность

Голос пользователя является чувствительными данными.

Запрещено:

- тайно включать микрофон;
- записывать аудио;
- сохранять аудио;
- отправлять аудио в интернет;
- использовать облачные API;
- использовать внешние библиотеки;
- использовать pyaudio;
- использовать speech_recognition;
- использовать whisper;
- использовать vosk;
- делать постоянное прослушивание;
- выполнять реальные системные команды;
- удалять файлы пользователя.

Микрофонный режим может быть только явно включён пользователем.

## Разрешённые зоны изменений

Можно изменять или создавать только:

- voice/
- voice/microphone_input_adapter.py
- voice/voice_input_manager.py
- core/command_processor.py
- core/kernel.py
- dialogue/dialogue_manager.py
- tests/unit/
- .ai/tasks/

Можно создать:

- tests/unit/test_microphone_input_adapter.py

Можно обновить:

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

### 1. MicrophoneInputAdapter

Создать файл:

voice/microphone_input_adapter.py

Создать класс:

MicrophoneInputAdapter

Он должен иметь состояния:

- disabled
- permission_required
- ready
- listening
- unavailable
- stopped

Начальное состояние:

disabled

### 2. Поля MicrophoneInputAdapter

Класс должен хранить:

- state
- permission_granted
- backend_name
- last_error

По умолчанию:

```python
state = "disabled"
permission_granted = False
backend_name = "none"
last_error = None