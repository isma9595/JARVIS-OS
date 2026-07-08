# TASK-003 — Kernel Services Integration

## Роль Codex

Ты инженер-исполнитель проекта JARVIS OS.

Архитектурные решения не принимаешь самостоятельно.
Работаешь строго по задаче.

## Главный архитектурный принцип

JARVIS OS должен всегда оставаться расширяемой платформой.

Нельзя принимать решения, которые мешают в будущем добавить:

- голосовое управление;
- зрение экрана;
- память;
- профиль пользователя;
- human-like dialogue;
- workflow automation;
- installer;
- новые ИИ-модели;
- новые языки;
- плагины;
- новые идеи пользователя.

Любое изменение должно сохранять модульность проекта.

## Цель

Сделать Logger, EventBus и ModuleManager настоящими системными сервисами ядра JARVIS OS.

## Разрешённые зоны изменений

Можно изменять только:

- core/kernel.py
- core/logger.py
- core/exceptions.py
- tests/unit/

Можно создавать только unit-тесты внутри:

- tests/unit/

## Запрещено

Нельзя:

- менять архитектуру проекта;
- менять run.py без необходимости;
- менять memory;
- менять users;
- менять brain;
- менять security;
- менять integrations;
- реализовывать onboarding;
- реализовывать installer;
- реализовывать voice;
- реализовывать workflow automation;
- реализовывать screen awareness;
- добавлять внешние библиотеки;
- выполнять опасные системные команды.

## Нужно реализовать

### 1. Kernel services

В JARVISKernel должны быть системные сервисы:

- logger
- event_bus
- module_manager

Kernel должен иметь метод:

- get_service(name)

Допустимые сервисы:

- logger
- event_bus
- module_manager

Если сервис неизвестен, должна быть понятная ошибка KernelError.

### 2. Startup events

При запуске Kernel должен публиковать события:

- kernel.starting
- kernel.started

Через EventBus.

### 3. Shutdown events

При остановке Kernel должен публиковать события:

- kernel.stopping
- kernel.stopped

Через EventBus.

Метод shutdown() должен:

- остановить модули через ModuleManager;
- опубликовать события остановки;
- вывести понятное сообщение через Logger;
- не падать при повторном вызове.

### 4. Kernel state

Kernel должен хранить состояние:

- created
- running
- stopped

Нельзя запускать Kernel повторно, если он уже running.

Нельзя ломать систему при повторном shutdown.

### 5. Logger

Logger должен оставаться простым.

Можно улучшить его так, чтобы он добавлял уровень сообщения:

- INFO
- WARNING
- ERROR

Но без внешних библиотек.

### 6. Tests

Добавить или обновить unit-тесты.

Нужно проверить:

- создание Kernel;
- наличие сервисов;
- get_service("logger");
- get_service("event_bus");
- get_service("module_manager");
- ошибку при неизвестном сервисе;
- start();
- повторный start();
- shutdown();
- повторный shutdown();
- публикацию событий kernel.started и kernel.stopped.

## Проверки

После изменений должны проходить команды:

python -m py_compile core/logger.py
python -m py_compile core/exceptions.py
python -m py_compile core/kernel.py
python -m tests.unit.test_kernel
python run.py

## В конце ответа

Покажи:

1. Какие файлы изменены.
2. Что именно изменено.
3. Какие проверки запустить.
4. Какие риски есть.