# TASK-002 — Kernel Runtime

## Роль Codex

Ты инженер-исполнитель проекта JARVIS OS.

Архитектурные решения не принимаешь самостоятельно.
Работаешь строго по задаче.

## Цель

Создать первый нормальный запуск JARVIS OS через файл run.py.

## Разрешённые зоны изменений

Можно изменять только:

- core/logger.py
- core/exceptions.py
- core/kernel.py
- run.py
- tests/unit/

## Запрещено

Нельзя:

- менять архитектуру проекта;
- удалять файлы;
- менять memory;
- менять brain;
- менять security;
- менять integrations;
- добавлять внешние библиотеки;
- выполнять опасные системные команды.

## Нужно реализовать

### 1. core/logger.py

Создать простой Logger без внешних библиотек.

Он должен иметь методы:

- info(message)
- warning(message)
- error(message)

Пока достаточно выводить сообщения в консоль.

### 2. core/exceptions.py

Создать базовые исключения:

- JarvisError
- KernelError
- ModuleError
- SecurityError

### 3. core/kernel.py

Создать класс JARVISKernel.

Он должен:

- хранить версию системы;
- создавать Logger;
- создавать EventBus;
- создавать ModuleManager;
- иметь метод start();
- иметь метод shutdown();
- при запуске выводить понятные сообщения;
- не выполнять опасные системные команды.

### 4. run.py

Создать точку входа проекта.

Команда:

python run.py

Должна запускать JARVISKernel.

## Ожидаемый вывод

При запуске:

python run.py

Должен быть вывод примерно:

JARVIS OS v0.2
Инициализация ядра...
Logger: OK
EventBus: OK
ModuleManager: OK
Система успешно запущена.
Добро пожаловать, Исмаил.

## Проверки

После изменений должны проходить команды:

python -m py_compile core/logger.py
python -m py_compile core/exceptions.py
python -m py_compile core/kernel.py
python -m py_compile run.py
python run.py

## В конце ответа

Покажи:

1. Какие файлы изменены.
2. Что именно изменено.
3. Какие проверки запустить.
4. Какие риски есть.