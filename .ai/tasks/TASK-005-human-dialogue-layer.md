# TASK-005 — Human Dialogue Layer

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
- workflow automation;
- installer;
- новые ИИ-модели;
- новые языки;
- плагины;
- новые идеи пользователя.

Любое изменение должно сохранять модульность проекта.

## Цель

Добавить Human Dialogue Layer — слой естественного общения JARVIS.

JARVIS должен общаться с пользователем не как робот, а как понятный, спокойный и живой помощник.

Важно:

- не притворяться человеком;
- не заявлять, что JARVIS является человеком;
- не делать эмоциональные манипуляции;
- не использовать слишком длинные фразы;
- сохранять честность и безопасность;
- учитывать профиль пользователя.

## Разрешённые зоны изменений

Можно изменять или создавать только:

- dialogue/
- dialogue/__init__.py
- dialogue/dialogue_manager.py
- core/kernel.py
- run.py
- tests/unit/

Можно создать:

- tests/unit/test_dialogue_manager.py

Можно обновить:

- tests/unit/test_kernel.py

## Запрещено

Нельзя:

- менять brain;
- менять memory;
- менять security;
- менять integrations;
- менять voice;
- менять vision;
- реализовывать voice;
- реализовывать screen awareness;
- реализовывать workflow automation;
- реализовывать installer;
- добавлять внешние библиотеки;
- выполнять опасные системные команды;
- отправлять данные пользователя в интернет.

## Нужно реализовать

### 1. DialogueManager

Создать файл:

dialogue/dialogue_manager.py

В нём создать класс:

DialogueManager

Он должен принимать user_profile.

Если user_profile отсутствует, использовать безопасные значения по умолчанию.

Минимальные значения по умолчанию:

- user_name: "Пользователь"
- preferred_name: "Пользователь"
- assistant_name: "JARVIS"
- language: "ru"
- communication_style: "естественный, понятный, не робот"

### 2. Методы DialogueManager

DialogueManager должен иметь методы:

- get_user_name()
- get_preferred_name()
- get_assistant_name()
- get_language()
- get_communication_style()
- greeting()
- startup_complete()
- shutdown_message()
- already_stopped_message()
- confirmation_request(action_description)
- acknowledgement(task_description)
- error_message(message)

### 3. Примеры ожидаемых фраз

greeting() должен возвращать примерно:

Добро пожаловать, Исмаил.

startup_complete() должен возвращать примерно:

Система успешно запущена.

shutdown_message() должен возвращать примерно:

Система остановлена.

already_stopped_message() должен возвращать примерно:

Ядро уже остановлено.

confirmation_request("отправить письмо") должен вернуть примерно:

Исмаил, я могу выполнить действие: отправить письмо. Подтвердить?

acknowledgement("подготовить письмо") должен вернуть примерно:

Понял, Исмаил. Подготовлю: подготовить письмо.

error_message("файл не найден") должен вернуть примерно:

Исмаил, возникла ошибка: файл не найден.

### 4. Kernel integration

JARVISKernel должен использовать DialogueManager для пользовательских сообщений.

Нужно убрать жёстко зашитые пользовательские фразы из Kernel, если они относятся к общению с пользователем.

Kernel должен:

- создавать DialogueManager;
- использовать его для приветствия;
- использовать его для сообщения об успешном запуске;
- использовать его для сообщения об остановке;
- использовать его для повторного shutdown.

При этом технические сообщения могут оставаться простыми:

- JARVIS OS v0.2
- Инициализация ядра...
- Logger: OK
- EventBus: OK
- ModuleManager: OK

### 5. run.py

run.py должен передавать user_profile в Kernel так, чтобы DialogueManager мог использовать профиль.

Если профиль отсутствует, запуск не должен падать.

### 6. Tests

Добавить tests/unit/test_dialogue_manager.py

Тесты должны проверять:

- создание DialogueManager без профиля;
- создание DialogueManager с профилем;
- получение имени пользователя;
- получение имени ассистента;
- получение языка;
- получение стиля общения;
- greeting();
- startup_complete();
- shutdown_message();
- already_stopped_message();
- confirmation_request();
- acknowledgement();
- error_message();

Обновить tests/unit/test_kernel.py при необходимости.

## Проверки

После изменений должны проходить команды:

python -m py_compile dialogue/dialogue_manager.py
python -m py_compile core/kernel.py
python -m py_compile run.py
python -m tests.unit.test_dialogue_manager
python -m tests.unit.test_kernel
python run.py

## Ожидаемый запуск

Команда:

python run.py

Должна вывести примерно:

[INFO] JARVIS OS v0.2
[INFO] Инициализация ядра...
[INFO] Logger: OK
[INFO] EventBus: OK
[INFO] ModuleManager: OK
[INFO] Система успешно запущена.
[INFO] Добро пожаловать, Исмаил.

## В конце ответа

Покажи:

1. Какие файлы изменены.
2. Что именно изменено.
3. Какие проверки запустить.
4. Какие риски есть.