# TASK-019 — Vosk Model Path Persistence & User Settings

## Роль Codex

Ты инженер-исполнитель проекта JARVIS OS.

Архитектурные решения не принимаешь самостоятельно.
Работаешь строго по задаче.

## Главный архитектурный принцип

JARVIS OS должен всегда оставаться расширяемой платформой.

Настройки Vosk должны быть построены так, чтобы в будущем можно было безопасно добавить:

- локальное распознавание речи;
- сохранение выбранного speech backend;
- сохранение пути к локальной модели;
- разные языки моделей;
- настройку качества/скорости;
- real microphone streaming;
- wake word;
- offline speech-to-text;
- голосовое подтверждение;
- разные уровни доступа;
- плагины;
- переносимость между ПК;
- installer.

Любое изменение должно сохранять модульность проекта.

## Цель

Добавить локальное сохранение настроек Vosk.

После этой задачи JARVIS должен уметь:

- сохранять путь к модели Vosk в локальный файл настроек;
- загружать путь к модели Vosk при следующем запуске;
- показывать сохранённый путь;
- очищать сохранённый путь только через безопасную команду;
- не сохранять локальные пользовательские настройки в GitHub;
- не включать микрофон;
- не записывать звук;
- не импортировать настоящий vosk;
- не устанавливать зависимости;
- не скачивать модели.

## Приватность и безопасность

Путь к локальной модели может содержать имя пользователя или структуру папок ПК.

Поэтому файл настроек должен быть локальным и не должен попадать в GitHub.

Запрещено:

- сохранять локальный файл настроек в GitHub;
- отправлять путь модели в интернет;
- включать микрофон;
- записывать звук;
- импортировать настоящий vosk;
- устанавливать зависимости;
- скачивать модели;
- выполнять реальные системные команды;
- удалять пользовательские файлы.

Разрешено:

- создать локальный JSON-файл настроек;
- читать/писать только этот JSON-файл;
- проверять, указан ли путь;
- проверять, существует ли путь;
- очищать только значение пути в JSON-настройках, а не файлы пользователя.

## Разрешённые зоны изменений

Можно изменять или создавать только:

- voice/
- config/
- core/command_processor.py
- dialogue/dialogue_manager.py
- tests/unit/
- docs/
- .ai/tasks/
- .gitignore

Можно создать:

- voice/vosk_settings_manager.py
- tests/unit/test_vosk_settings_manager.py
- docs/VOSK_SETTINGS.md
- config/local/.gitkeep

Можно обновить:

- voice/vosk_local_backend.py
- voice/voice_input_manager.py
- voice/microphone_input_adapter.py
- voice/__init__.py
- core/command_processor.py
- dialogue/dialogue_manager.py
- tests/unit/test_vosk_local_backend.py
- tests/unit/test_voice_input_manager.py
- tests/unit/test_microphone_input_adapter.py
- tests/unit/test_command_processor.py
- tests/unit/test_dialogue_manager.py
- tests/unit/test_kernel.py
- docs/VOSK_PREFLIGHT.md
- docs/VOSK_BACKEND_PLAN.md
- .gitignore

## Запрещено

Нельзя:

- менять brain;
- менять memory;
- менять users;
- менять security;
- менять integrations;
- менять vision;
- менять ideas;
- реализовывать настоящий speech-to-text;
- реализовывать настоящий микрофон;
- реализовывать screen awareness;
- реализовывать workflow automation;
- реализовывать installer;
- реализовывать embeddings;
- реализовывать vector database;
- использовать import vosk;
- использовать from vosk import ...;
- использовать pyaudio;
- использовать speech_recognition;
- использовать whisper;
- устанавливать зависимости;
- скачивать модели;
- включать микрофон;
- записывать звук;
- отправлять данные пользователя в интернет;
- удалять пользовательские файлы.

## Нужно реализовать

### 1. Локальное хранилище настроек

Создать файл:

voice/vosk_settings_manager.py

Создать класс:

VoskSettingsManager

Он должен хранить настройки в JSON-файле:

config/local/vosk_settings.json

По умолчанию файл может отсутствовать.

Если файл отсутствует — настройки считаются пустыми.

Важно:

- создать папку config/local только при сохранении настроек;
- не создавать лишние файлы;
- не удалять пользовательские файлы;
- не писать ничего кроме config/local/vosk_settings.json;
- не сохранять этот JSON в GitHub.

### 2. .gitignore

Обновить .gitignore так, чтобы локальные настройки не попадали в GitHub:

```gitignore
config/local/*.json