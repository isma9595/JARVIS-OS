# TASK-008 — Ideas Backlog

## Роль Codex

Ты инженер-исполнитель проекта JARVIS OS.

Архитектурные решения не принимаешь самостоятельно.
Работаешь строго по задаче.

## Главный архитектурный принцип

JARVIS OS должен всегда оставаться расширяемой платформой.

Новые идеи пользователя должны сохраняться так, чтобы в будущем их можно было превратить в полноценные модули, спринты или задачи для Codex.

Нельзя принимать решения, которые мешают в будущем добавить:

- голосовое управление;
- зрение экрана;
- память;
- workflow automation;
- installer;
- новые ИИ-модели;
- новые языки;
- плагины;
- новые идеи пользователя.

Любое изменение должно сохранять модульность проекта.

## Цель

Добавить Ideas Backlog — локальное хранилище идей пользователя.

JARVIS должен уметь:

- сохранять новые идеи локально;
- показывать список сохранённых идей;
- не отправлять идеи в интернет;
- не использовать внешние библиотеки;
- не выполнять реальные действия;
- хранить идеи в JSON;
- быть готовым к будущему превращению идей в TASK-файлы.

## Приватность

Идеи пользователя должны храниться только локально.

Нельзя:

- отправлять идеи в интернет;
- использовать облако;
- использовать внешние API;
- сохранять лишние персональные данные.

## Разрешённые зоны изменений

Можно изменять или создавать только:

- ideas/
- ideas/ideas.json
- ideas/idea_manager.py
- ideas/__init__.py
- core/command_processor.py
- core/kernel.py
- dialogue/dialogue_manager.py
- tests/unit/

Можно создать:

- tests/unit/test_idea_manager.py

Можно обновить:

- tests/unit/test_command_processor.py
- tests/unit/test_kernel.py
- tests/unit/test_dialogue_manager.py

Можно обновить:

- .gitignore

## Запрещено

Нельзя:

- менять brain;
- менять memory;
- менять users;
- менять security;
- менять integrations;
- менять voice;
- менять vision;
- реализовывать voice;
- реализовывать screen awareness;
- реализовывать workflow automation;
- реализовывать installer;
- реально выполнять системные команды;
- удалять файлы;
- отправлять письма;
- открывать приложения;
- использовать внешние библиотеки;
- отправлять данные пользователя в интернет.

## Нужно реализовать

### 1. IdeaManager

Создать файл:

ideas/idea_manager.py

В нём создать класс:

IdeaManager

Он должен уметь:

- создавать хранилище идей;
- проверять, существует ли файл идей;
- загружать идеи;
- сохранять идеи;
- добавлять новую идею;
- возвращать список идей;
- возвращать количество идей.

Использовать только стандартные библиотеки Python:

- json
- pathlib
- datetime
- uuid

### 2. Файл хранения идей

Идеи должны храниться локально в:

ideas/ideas.json

Если файла нет — создать автоматически.

Структура файла:

{
  "ideas": [
    {
      "id": "...",
      "title": "...",
      "description": "...",
      "source": "user_command",
      "status": "new",
      "priority": "normal",
      "created_at": "...",
      "updated_at": "..."
    }
  ]
}

### 3. Добавление идеи

IdeaManager должен иметь метод:

add_idea(title, description="", source="user_command", priority="normal")

Он должен возвращать созданную идею.

Если title пустой — должна быть понятная ошибка ValueError.

### 4. Получение идей

IdeaManager должен иметь методы:

- list_ideas()
- count_ideas()

Если идей нет — возвращать пустой список.

### 5. DialogueManager

Добавить методы, если нужно:

- idea_saved_response(idea_title)
- ideas_list_response(ideas)
- no_ideas_response()

Примеры:

Если идея сохранена:

Исмаил, я сохранил идею: научиться видеть экран.

Если идей нет:

Исмаил, пока нет сохранённых идей.

Если идеи есть:

Исмаил, вот сохранённые идеи:
1. Научиться видеть экран
2. Сделать голосовое управление

### 6. CommandProcessor integration

CommandProcessor должен понимать команды:

#### Добавление идеи

Команды:

- добавь идею
- запомни идею
- сохрани идею
- записать идею

Примеры:

добавь идею научиться видеть экран

запомни идею сделать голосовое управление

сохрани идею чтобы JARVIS видел монитор

Поведение:

- сохранить идею через IdeaManager;
- вернуть response через DialogueManager;
- intent: idea.add
- should_exit: false

#### Показать идеи

Команды:

- покажи идеи
- мои идеи
- список идей
- идеи

Поведение:

- показать список сохранённых идей;
- intent: idea.list
- should_exit: false

### 7. Unknown command integration

Если SafeActionRouter возвращает category idea, CommandProcessor может пока просто отвечать как раньше.

Но если команда явно начинается с:

- добавь идею
- запомни идею
- сохрани идею

тогда нужно реально сохранить идею.

### 8. Kernel integration

JARVISKernel должен создавать IdeaManager как системный сервис.

Добавить сервис:

- idea_manager

Метод get_service("idea_manager") должен возвращать IdeaManager.

Старые сервисы должны продолжить работать:

- logger
- event_bus
- module_manager
- command_processor
- action_router

### 9. run.py

run.py должен передавать IdeaManager или Kernel service в CommandProcessor так, чтобы команды идей работали.

Простой интерактивный режим должен продолжить работать.

### 10. Tests

Добавить:

tests/unit/test_idea_manager.py

Тесты должны проверять:

- создание IdeaManager;
- создание файла ideas.json;
- list_ideas() на пустом списке;
- count_ideas();
- add_idea();
- запрет пустого title;
- сохранение и повторную загрузку идей.

Обновить tests/unit/test_command_processor.py:

- команда "добавь идею научиться видеть экран";
- команда "запомни идею сделать голосовое управление";
- команда "покажи идеи";
- intent idea.add;
- intent idea.list.

Обновить tests/unit/test_kernel.py:

- get_service("idea_manager");
- старые сервисы должны работать;
- неизвестный сервис всё ещё вызывает KernelError.

## Важное требование по Git

Если ideas/ideas.json будет содержать реальные идеи пользователя, его не нужно отправлять на GitHub.

Нужно добавить в .gitignore:

ideas/ideas.json

Но папка ideas/ должна остаться в проекте.

Можно добавить:

ideas/.gitkeep

или оставить ideas/__init__.py и ideas/idea_manager.py.

## Проверки

После изменений должны проходить команды:

python -m py_compile ideas/idea_manager.py
python -m py_compile core/command_processor.py
python -m py_compile core/kernel.py
python -m py_compile dialogue/dialogue_manager.py
python -m tests.unit.test_idea_manager
python -m tests.unit.test_command_processor
python -m tests.unit.test_kernel
python run.py

## Ожидаемый запуск

Команда:

python run.py

Должна запускать JARVIS в интерактивном режиме.

Примеры:

Пользователь:

добавь идею научиться видеть экран

JARVIS:

Исмаил, я сохранил идею: научиться видеть экран.

Пользователь:

покажи идеи

JARVIS:

Исмаил, вот сохранённые идеи:
1. научиться видеть экран

Пользователь:

выход

JARVIS завершает работу.

## В конце ответа

Покажи:

1. Какие файлы изменены.
2. Что именно изменено.
3. Какие проверки запустить.
4. Какие риски есть.