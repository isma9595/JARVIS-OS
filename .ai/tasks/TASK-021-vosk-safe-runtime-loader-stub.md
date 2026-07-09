# TASK-021 — Vosk Safe Runtime Loader Stub

## Роль Codex

Ты инженер-исполнитель проекта JARVIS OS.

Архитектурные решения не принимаешь самостоятельно.
Работаешь строго по задаче.

## Главный архитектурный принцип

JARVIS OS должен всегда оставаться расширяемой платформой.

Runtime loader Vosk должен быть построен так, чтобы в будущем можно было безопасно добавить:

- реальную загрузку Vosk runtime;
- локальное offline speech-to-text;
- загрузку vosk.Model;
- KaldiRecognizer;
- проверку тестового аудиофайла;
- real microphone streaming;
- wake word;
- голосовое подтверждение;
- разные уровни доступа;
- разные языки моделей;
- плагины;
- переносимость между ПК;
- installer.

Любое изменение должно сохранять модульность проекта.

## Цель

Добавить безопасный runtime loader stub для Vosk.

После этой задачи JARVIS должен уметь:

- показывать статус runtime loader;
- проверять, можно ли теоретически готовить загрузку Vosk;
- объяснять, почему настоящий runtime ещё не загружается;
- связывать loader с preflight и локальными настройками модели;
- показывать безопасные блокировки;
- иметь команды для статуса runtime;
- не импортировать настоящий vosk на уровне модуля;
- не создавать vosk.Model;
- не создавать KaldiRecognizer;
- не запускать распознавание;
- не включать микрофон;
- не записывать звук.

## Важный принцип безопасности

TASK-021 — это только loader stub.

Разрешается создать объект/класс, который описывает будущую загрузку runtime.

Но запрещено выполнять реальную загрузку Vosk runtime.

То есть:

- нельзя делать import vosk;
- нельзя делать from vosk import ...;
- нельзя создавать vosk.Model;
- нельзя создавать KaldiRecognizer;
- нельзя открывать аудиофайлы;
- нельзя слушать микрофон;
- нельзя записывать звук.

Можно использовать уже существующие безопасные проверки:

- importlib.util.find_spec("vosk");
- проверка сохранённого пути модели;
- проверка существования папки модели;
- статусы preflight.

## Запрещено

Нельзя:

- выполнять pip install vosk;
- устанавливать зависимости;
- скачивать модели;
- импортировать настоящий vosk;
- использовать import vosk;
- использовать from vosk import ...;
- использовать importlib.import_module("vosk");
- создавать vosk.Model;
- создавать KaldiRecognizer;
- использовать pyaudio;
- использовать speech_recognition;
- использовать whisper;
- использовать sounddevice;
- использовать wave для реального аудио;
- включать микрофон;
- записывать звук;
- читать аудиофайлы пользователя;
- отправлять данные в интернет;
- запускать реальное распознавание;
- менять Python-окружение;
- создавать venv автоматически;
- удалять пользовательские файлы;
- реализовывать real microphone streaming;
- реализовывать screen awareness;
- реализовывать workflow automation;
- реализовывать installer.

## Разрешённые зоны изменений

Можно изменять или создавать только:

- voice/
- core/command_processor.py
- dialogue/dialogue_manager.py
- tests/unit/
- docs/
- .ai/tasks/

Можно создать:

- voice/vosk_runtime_loader.py
- tests/unit/test_vosk_runtime_loader.py
- docs/VOSK_RUNTIME_LOADER.md

Можно обновить:

- voice/__init__.py
- voice/vosk_local_backend.py
- voice/voice_input_manager.py
- voice/vosk_installation_guide.py
- core/command_processor.py
- dialogue/dialogue_manager.py
- tests/unit/test_vosk_local_backend.py
- tests/unit/test_voice_input_manager.py
- tests/unit/test_command_processor.py
- tests/unit/test_dialogue_manager.py
- tests/unit/test_kernel.py
- docs/VOSK_BACKEND_PLAN.md
- docs/VOSK_PREFLIGHT.md
- docs/VOSK_SETTINGS.md
- docs/VOSK_INSTALLATION_GUIDE.md
- docs/VOSK_SAFE_ENABLEMENT_PLAN.md

## Нужно реализовать

### 1. VoskRuntimeLoader

Создать файл:

voice/vosk_runtime_loader.py

Создать класс:

VoskRuntimeLoader

Это безопасная заглушка будущего runtime loader.

Он должен принимать:

- backend=None
- installation_guide=None

Если backend не передан, можно создать VoskLocalBackend.

Если installation_guide не передан, можно создать VoskInstallationGuide.

### 2. Методы VoskRuntimeLoader

Реализовать методы:

- get_runtime_status()
- can_prepare_runtime()
- get_blockers()
- get_safety_summary()
- get_next_steps()
- prepare_runtime_stub()
- unload_runtime_stub()
- is_runtime_loaded()
- recognize_text_stub()

### 3. get_runtime_status()

Должен вернуть словарь:

```python id="ilpz48"
{
    "runtime": "vosk",
    "loader_type": "safe_stub",
    "runtime_loaded": False,
    "dependency_available": False,
    "model_path_configured": False,
    "model_path_exists": False,
    "can_prepare_runtime": False,
    "real_recognition_enabled": False,
    "microphone_enabled": False,
    "message": "..."
}