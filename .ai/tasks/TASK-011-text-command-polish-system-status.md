# TASK-011 — Text Command Polish & System Status

## Роль Codex

Ты инженер-исполнитель проекта JARVIS OS.

Архитектурные решения не принимаешь самостоятельно.
Работаешь строго по задаче.

## Главный архитектурный принцип

JARVIS OS должен всегда оставаться расширяемой платформой.

Текстовый режим команд должен быть построен так, чтобы в будущем его можно было использовать как основу для:

- голосовых команд;
- экранного зрения;
- workflow automation;
- управления приложениями;
- плагинов;
- новых языков;
- AI reasoning;
- installer;
- новых идей пользователя.

Любое изменение должно сохранять модульность проекта.

## Цель

Улучшить текстовый режим JARVIS.

После этой задачи JARVIS должен уметь:

- показывать статус системы;
- показывать версию системы;
- показывать список системных сервисов;
- показывать список доступных команд;
- улучшенно отвечать на “помощь”;
- улучшенно отвечать на “что ты умеешь”;
- не выполнять реальные системные действия;
- не отправлять данные в интернет;
- сохранить совместимость со всеми существующими командами.

## Разрешённые зоны изменений

Можно изменять или создавать только:

- core/command_processor.py
- core/kernel.py
- dialogue/dialogue_manager.py
- tests/unit/
- .ai/tasks/

Можно обновить:

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
- менять voice;
- менять vision;
- менять ideas;
- реализовывать voice;
- реализовывать screen awareness;
- реализовывать workflow automation;
- реализовывать installer;
- реализовывать embeddings;
- реализовывать vector database;
- выполнять реальные системные команды;
- удалять память;
- удалять файлы пользователя;
- отправлять данные пользователя в интернет;
- использовать внешние библиотеки.

## Нужно реализовать

### 1. Kernel system status

Обновить JARVISKernel.

Добавить методы:

- get_version()
- get_state()
- list_services()
- get_system_status()

get_system_status() должен возвращать словарь примерно такого вида:

{
  "version": "0.2",
  "state": "running",
  "services": [
    "logger",
    "event_bus",
    "module_manager",
    "command_processor",
    "action_router",
    "idea_manager",
    "memory_manager"
  ]
}

Если какие-то сервисы уже создаются в Kernel — не ломать их.

Старый get_service(name) должен продолжить работать.

### 2. CommandProcessor system commands

CommandProcessor должен понимать команды:

#### Версия

Команды:

- версия
- покажи версию
- какая версия
- версия системы

Intent:

system.version

Ответ примерно:

Исмаил, текущая версия JARVIS OS: v0.2.

#### Статус системы

Команды:

- статус
- статус системы
- как система
- состояние системы

Intent:

system.status

Ответ примерно:

Исмаил, система работает. Версия: v0.2. Активных сервисов: 7.

#### Сервисы

Команды:

- покажи сервисы
- список сервисов
- какие сервисы работают
- системные сервисы

Intent:

system.services

Ответ примерно:

Исмаил, активные системные сервисы:
1. logger
2. event_bus
3. module_manager
4. command_processor
5. action_router
6. idea_manager
7. memory_manager

#### Команды

Команды:

- покажи команды
- список команд
- какие команды есть
- все команды

Intent:

assistant.commands

Ответ должен показать сгруппированный список команд:

- Профиль
- Память
- Идеи
- Система
- Безопасность
- Выход

Пример:

Исмаил, сейчас доступны такие команды:

Профиль:
- кто я
- покажи профиль

Память:
- запомни что ...
- что ты помнишь
- вспомни про ...

Идеи:
- добавь идею ...
- покажи идеи

Система:
- статус системы
- покажи версию
- покажи сервисы

Выход:
- выход

#### Помощь

Команды:

- помощь
- help
- команды
- что ты умеешь
- покажи возможности

Intent:

assistant.help

Ответ должен быть более аккуратным и понятным, чем раньше.

Он должен кратко объяснить:

- что JARVIS уже умеет;
- что будет добавлено позже;
- как выйти из программы.

Пример:

Исмаил, сейчас я умею работать с профилем, сохранять идеи, запоминать факты, искать по памяти, показывать статус системы и различать риск действий. Голос, зрение экрана и автоматизация будут добавлены позже. Для выхода напишите: выход.

### 3. DialogueManager

Добавить методы, если нужно:

- version_response(version)
- system_status_response(status)
- services_response(services)
- commands_response()
- help_response()

Ответы должны быть естественными, спокойными и на русском языке.

Не делать ответы слишком длинными.

### 4. CommandProcessor integration

CommandProcessor должен иметь доступ к Kernel status или к callable/provider, чтобы отвечать на системные команды.

Если прямой доступ к Kernel создаёт циклическую зависимость, использовать простой system_info/system_status_provider, переданный в CommandProcessor.

Важно:

- не ломать существующие команды профиля;
- не ломать команды памяти;
- не ломать команды идей;
- не ломать SafeActionRouter;
- не ломать выход;
- не выполнять реальные действия.

### 5. run.py

run.py менять только если без этого невозможно корректно передать system status в CommandProcessor.

Если можно не менять run.py — не менять.

### 6. Tests

Обновить tests/unit/test_command_processor.py.

Проверить команды:

- версия
- покажи версию
- статус системы
- покажи сервисы
- покажи команды
- список команд
- помощь
- что ты умеешь

Проверить intents:

- system.version
- system.status
- system.services
- assistant.commands
- assistant.help

Обновить tests/unit/test_kernel.py.

Проверить:

- get_version()
- get_state()
- list_services()
- get_system_status()
- старые сервисы доступны через get_service()
- неизвестный сервис всё ещё вызывает KernelError.

Обновить tests/unit/test_dialogue_manager.py.

Проверить новые методы DialogueManager.

## Проверки

После изменений должны проходить команды:

python -m py_compile core/command_processor.py
python -m py_compile core/kernel.py
python -m py_compile dialogue/dialogue_manager.py
python -m tests.unit.test_command_processor
python -m tests.unit.test_dialogue_manager
python -m tests.unit.test_kernel
python run.py

## Ожидаемый запуск

Команда:

python run.py

Должна запускать JARVIS в интерактивном режиме.

Примеры:

Пользователь:

статус системы

JARVIS:

Исмаил, система работает. Версия: v0.2. Активных сервисов: 7.

Пользователь:

покажи сервисы

JARVIS:

Исмаил, активные системные сервисы:
1. logger
2. event_bus
3. module_manager
4. command_processor
5. action_router
6. idea_manager
7. memory_manager

Пользователь:

покажи команды

JARVIS показывает сгруппированный список команд.

Пользователь:

выход

JARVIS завершает работу.

## В конце ответа

Покажи:

1. Какие файлы изменены.
2. Что именно изменено.
3. Какие проверки запустить.
4. Какие риски есть.