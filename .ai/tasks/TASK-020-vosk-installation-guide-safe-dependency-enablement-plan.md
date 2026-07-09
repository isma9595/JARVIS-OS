# TASK-020 — Vosk Installation Guide & Safe Dependency Enablement Plan

## Роль Codex

Ты инженер-исполнитель проекта JARVIS OS.

Архитектурные решения не принимаешь самостоятельно.
Работаешь строго по задаче.

## Главный архитектурный принцип

JARVIS OS должен всегда оставаться расширяемой платформой.

Подключение Vosk должно быть подготовлено так, чтобы в будущем можно было безопасно добавить:

- реальный локальный Vosk runtime;
- локальное offline speech-to-text;
- проверку совместимости Python;
- проверку pip;
- проверку установленной зависимости;
- проверку локальной модели;
- безопасный runtime loader;
- real microphone streaming;
- wake word;
- голосовое подтверждение;
- разные уровни доступа;
- плагины;
- переносимость между ПК;
- installer.

Любое изменение должно сохранять модульность проекта.

## Цель

Добавить безопасную инструкцию и план включения Vosk dependency.

После этой задачи JARVIS должен уметь:

- показывать инструкцию по установке Vosk;
- объяснять, что Vosk пока не устанавливается автоматически;
- показывать рекомендуемые команды установки как текст;
- проверять совместимость Python только информационно;
- предупреждать, что текущий Python может быть несовместим;
- показывать рекомендуемый путь: отдельный совместимый venv для Vosk;
- показывать инструкцию по скачиванию локальной модели;
- объяснять, какую русскую модель можно использовать первой;
- не устанавливать зависимости;
- не скачивать модели;
- не импортировать настоящий vosk;
- не включать микрофон;
- не записывать звук.

## Важный контекст

По официальной документации Vosk:

- установка Python-модуля обычно выполняется через pip;
- поддерживается Windows x86/x64;
- в официальной инструкции указан Python 3.5–3.9;
- pip должен быть 20.3 или новее;
- русская маленькая модель vosk-model-small-ru-0.22 подходит как первый lightweight-вариант.

Но JARVIS не должен слепо устанавливать зависимость.

TASK-020 — это только guide/plan слой.

## Запрещено

Нельзя:

- выполнять pip install vosk;
- устанавливать зависимости;
- скачивать модели;
- импортировать настоящий vosk;
- использовать import vosk;
- использовать from vosk import ...;
- использовать pyaudio;
- использовать speech_recognition;
- использовать whisper;
- включать микрофон;
- записывать звук;
- отправлять данные в интернет;
- запускать реальное распознавание;
- менять текущую Python-среду;
- создавать venv автоматически;
- удалять пользовательские файлы;
- менять installer;
- реализовывать настоящий speech-to-text;
- реализовывать real microphone streaming;
- реализовывать screen awareness;
- реализовывать workflow automation.

## Разрешённые зоны изменений

Можно изменять или создавать только:

- voice/
- core/command_processor.py
- dialogue/dialogue_manager.py
- tests/unit/
- docs/
- .ai/tasks/

Можно создать:

- docs/VOSK_INSTALLATION_GUIDE.md
- docs/VOSK_SAFE_ENABLEMENT_PLAN.md
- tests/unit/test_vosk_installation_guide.py
- voice/vosk_installation_guide.py

Можно обновить:

- voice/__init__.py
- voice/vosk_local_backend.py
- voice/voice_input_manager.py
- core/command_processor.py
- dialogue/dialogue_manager.py
- tests/unit/test_command_processor.py
- tests/unit/test_dialogue_manager.py
- tests/unit/test_voice_input_manager.py
- tests/unit/test_vosk_local_backend.py
- tests/unit/test_kernel.py
- docs/VOSK_BACKEND_PLAN.md
- docs/VOSK_PREFLIGHT.md
- docs/VOSK_SETTINGS.md

## Нужно реализовать

### 1. VoskInstallationGuide

Создать файл:

voice/vosk_installation_guide.py

Создать класс:

VoskInstallationGuide

Он должен быть безопасным информационным классом.

Он НЕ должен устанавливать зависимости.

Он НЕ должен импортировать vosk.

Он должен возвращать только текстовые рекомендации и статусы.

### 2. Методы VoskInstallationGuide

Реализовать методы:

- get_python_version_status()
- get_pip_install_command()
- get_recommended_model()
- get_model_download_guidance()
- get_safe_enablement_steps()
- get_installation_summary()
- get_runtime_risks()
- get_public_status()

### 3. get_python_version_status()

Метод должен:

- определить текущую версию Python через sys.version_info;
- вернуть словарь:

```python
{
    "python_version": "3.14.6",
    "official_supported_range": "3.5-3.9",
    "is_likely_compatible": False,
    "message": "..."
}