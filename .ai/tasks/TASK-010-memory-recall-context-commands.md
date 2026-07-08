# TASK-010 — Memory Recall & Context Commands

## Роль Codex

Ты инженер-исполнитель проекта JARVIS OS.

Архитектурные решения не принимаешь самостоятельно.
Работаешь строго по задаче.

## Главный архитектурный принцип

JARVIS OS должен всегда оставаться расширяемой платформой.

Память должна быть построена так, чтобы в будущем можно было добавить:

- semantic memory;
- project memory;
- voice memory;
- screen context memory;
- workflow memory;
- vector search;
- local embeddings;
- AI reasoning;
- синхронизацию только по разрешению пользователя.

Любое изменение должно сохранять модульность проекта.

## Цель

Усилить локальную память JARVIS.

После этой задачи JARVIS должен уметь:

- показывать последние записи памяти;
- считать количество записей памяти;
- искать по памяти;
- отвечать на команду “что ты знаешь обо мне”;
- отвечать на команду “вспомни про ...”;
- не отправлять память в интернет;
- не использовать внешние библиотеки;
- не удалять память;
- не сохранять личную память в GitHub.

## Приватность

Память пользователя должна храниться только локально.

Нельзя:

- отправлять память в интернет;
- использовать облако;
- использовать внешние API;
- автоматически запоминать всё подряд;
- удалять память;
- изменять личные файлы пользователя;
- сохранять memory/local/memory.json в GitHub.

## Разрешённые зоны изменений

Можно изменять или создавать только:

- memory/memory_manager.py
- core/command_processor.py
- core/kernel.py
- dialogue/dialogue_manager.py
- tests/unit/
- .ai/tasks/

Можно обновить:

- tests/unit/test_memory_manager.py
- tests/unit/test_command_processor.py
- tests/unit/test_dialogue_manager.py
- tests/unit/test_kernel.py

## Запрещено

Нельзя:

- менять brain;
- менять users;
- менять security;
- менять integrations;
- менять voice;
- менять vision;
- реализовывать voice;
- реализовывать screen awareness;
- реализовывать workflow automation;
- реализовывать installer;
- реализовывать embeddings;
- реализовывать vector database;
- реально выполнять системные команды;
- удалять память;
- удалять пользовательские файлы;
- отправлять данные пользователя в интернет;
- использовать внешние библиотеки.

## Нужно реализовать

### 1. LocalMemoryManager

Обновить файл:

memory/memory_manager.py

Добавить методы:

- get_recent_memories(limit=5)
- has_memories()
- summarize_memory_count()
- get_all_memory_text()
- search_memories(query)

Если search_memories уже есть — улучшить без усложнения.

Требования:

- get_recent_memories(limit=5) должен возвращать последние записи памяти;
- если limit меньше 1 — использовать 1;
- если limit больше количества записей — вернуть все доступные;
- порядок последних записей: от новых к старым или от старых к новым, но тесты должны быть согласованы;
- search_memories(query) должен делать простой поиск по content и tags;
- если query пустой — возвращать пустой список.

### 2. DialogueManager

Добавить методы, если нужно:

- memory_count_response(count)
- recent_memory_response(memories)
- about_user_response(memories)
- memory_recall_response(memories, query)
- memory_not_found_response(query)

Примеры ответов:

Если пользователь спрашивает количество памяти:

Исмаил, в локальной памяти сохранено записей: 3.

Если пользователь спрашивает последние записи:

Исмаил, вот последние записи памяти:
1. я работаю с муниципальными письмами
2. JARVIS должен быть расширяемым

Если пользователь спрашивает “что ты знаешь обо мне”:

Исмаил, вот что я знаю из локальной памяти:
1. вы работаете с муниципальными письмами
2. вы хотите, чтобы JARVIS был расширяемым

Если ничего не найдено:

Исмаил, я не нашёл в памяти записей по запросу: проект.

### 3. CommandProcessor integration

Обновить CommandProcessor.

Он должен понимать команды:

#### Количество памяти

Команды:

- сколько ты помнишь
- сколько записей в памяти
- сколько у тебя памяти

Intent:

memory.count

Ответ должен использовать count_memories().

#### Последние записи памяти

Команды:

- покажи последние записи памяти
- последние записи памяти
- последняя память
- последние воспоминания

Intent:

memory.recent

Ответ должен показать последние записи через get_recent_memories(limit=5).

#### Что ты знаешь обо мне

Команды:

- что ты знаешь обо мне
- что ты помнишь обо мне
- что ты знаешь про меня
- что ты помнишь про меня

Intent:

memory.about_user

Ответ должен показать локальные записи памяти, если они есть.

Если памяти нет — ответить, что пока в локальной памяти ничего нет.

#### Вспомни про ...

Команды:

- вспомни про
- что ты помнишь про
- найди в памяти
- поиск в памяти

Примеры:

вспомни про муниципальные письма

что ты помнишь про JARVIS

найди в памяти документы

Intent:

memory.search

Ответ должен использовать search_memories(query).

#### Старые команды памяти

Старые команды должны продолжить работать:

- запомни что ...
- сохрани в память ...
- что ты помнишь
- покажи память
- память

### 4. Безопасность

Команды удаления памяти НЕ реализовывать.

Если пользователь пишет:

- удали память
- очисти память
- забудь всё

JARVIS не должен удалять память.

Он должен ответить, что удаление памяти требует отдельной подтверждаемой функции в будущем.

Intent может быть:

memory.delete.requested

should_exit:

false

### 5. Kernel integration

JARVISKernel уже должен иметь memory_manager.

Проверить, что сервис:

- memory_manager

доступен через:

get_service("memory_manager")

Старые сервисы должны продолжить работать:

- logger
- event_bus
- module_manager
- command_processor
- action_router
- idea_manager

### 6. Tests

Обновить tests/unit/test_memory_manager.py

Проверить:

- get_recent_memories();
- get_recent_memories(limit=1);
- get_recent_memories(limit больше количества записей);
- has_memories();
- summarize_memory_count();
- search_memories() по content;
- search_memories() по tags;
- search_memories() с пустым query.

Обновить tests/unit/test_command_processor.py

Проверить команды:

- сколько ты помнишь
- покажи последние записи памяти
- что ты знаешь обо мне
- вспомни про документы
- что ты помнишь про JARVIS
- удали память
- очисти память
- забудь всё

Проверить intents:

- memory.count
- memory.recent
- memory.about_user
- memory.search
- memory.delete.requested

Обновить tests/unit/test_dialogue_manager.py

Проверить новые методы ответов памяти.

Обновить tests/unit/test_kernel.py

Проверить, что memory_manager всё ещё доступен как сервис.

## Проверки

После изменений должны проходить команды:

python -m py_compile memory/memory_manager.py
python -m py_compile core/command_processor.py
python -m py_compile core/kernel.py
python -m py_compile dialogue/dialogue_manager.py
python -m tests.unit.test_memory_manager
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

сколько ты помнишь

JARVIS:

Исмаил, в локальной памяти сохранено записей: 1.

Пользователь:

покажи последние записи памяти

JARVIS:

Исмаил, вот последние записи памяти:
1. я работаю с муниципальными письмами

Пользователь:

вспомни про муниципальные письма

JARVIS:

Исмаил, я нашёл в памяти:
1. я работаю с муниципальными письмами

Пользователь:

удали память

JARVIS:

Исмаил, удаление памяти требует отдельной подтверждаемой функции. В этой версии я не удаляю память.

Пользователь:

выход

JARVIS завершает работу.

## В конце ответа

Покажи:

1. Какие файлы изменены.
2. Что именно изменено.
3. Какие проверки запустить.
4. Какие риски есть.