# TASK-007 — Safe Action Router

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

Добавить Safe Action Router — слой безопасной маршрутизации действий.

На этом этапе JARVIS НЕ должен реально управлять компьютером.
Он НЕ должен удалять файлы, открывать приложения, отправлять письма или выполнять системные команды.

Он должен только:

- принять команду пользователя;
- определить тип действия;
- определить уровень риска;
- сказать, можно ли действие выполнить сразу;
- сказать, нужно ли подтверждение;
- запретить опасные действия;
- вернуть понятный ответ пользователю.

## Зачем это нужно

В будущем JARVIS будет выполнять голосовые команды, видеть экран, заполнять формы и автоматизировать работу.

Перед этим нужна система безопасности, которая отличает:

- обычный вопрос;
- безопасную команду;
- действие с риском;
- опасную команду;
- идею на будущее.

## Разрешённые зоны изменений

Можно изменять или создавать только:

- core/action_router.py
- core/command_processor.py
- core/kernel.py
- dialogue/dialogue_manager.py
- tests/unit/

Можно создать:

- tests/unit/test_action_router.py

Можно обновить:

- tests/unit/test_command_processor.py
- tests/unit/test_kernel.py
- tests/unit/test_dialogue_manager.py

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
- создавать файлы по команде пользователя;
- отправлять письма;
- открывать приложения;
- использовать внешние библиотеки;
- отправлять данные пользователя в интернет.

## Нужно реализовать

### 1. SafeActionRouter

Создать файл:

core/action_router.py

В нём создать класс:

SafeActionRouter

Он должен принимать:

- user_profile
- dialogue_manager

Если user_profile или dialogue_manager отсутствуют, использовать безопасные значения по умолчанию.

### 2. Метод route

SafeActionRouter должен иметь метод:

route(command_text, intent=None)

Он должен возвращать словарь:

{
  "category": "...",
  "risk_level": "...",
  "allowed": true,
  "requires_confirmation": false,
  "reason": "...",
  "response": "..."
}

### 3. Категории действий

Нужно поддержать категории:

#### informational

Информационные команды.

Примеры:

- кто я
- как тебя зовут
- покажи профиль
- что ты умеешь
- помощь

Поведение:

- allowed: true
- requires_confirmation: false
- risk_level: low

#### safe_action

Безопасное действие, которое в будущем можно будет выполнить без риска.

Примеры:

- покажи список команд
- объясни что ты умеешь
- подготовь черновик
- составь текст
- помоги написать письмо

Поведение:

- allowed: true
- requires_confirmation: false
- risk_level: low

Важно:

На этом этапе действие не выполнять, только вернуть решение.

#### confirmation_required

Действия, которые в будущем требуют подтверждения пользователя.

Примеры:

- отправь письмо
- удали файл
- загрузи документ
- опубликуй объявление
- измени настройки
- заполни форму и отправь
- подпиши документ
- создай файл
- открой приложение
- скачай файл

Поведение:

- allowed: true
- requires_confirmation: true
- risk_level: medium

Ответ должен объяснять, что для такого действия потребуется подтверждение пользователя.

#### forbidden

Опасные или недопустимые действия.

Примеры:

- удали system32
- отключи защиту
- взломай
- укради данные
- обойди пароль
- форматируй диск
- удали все файлы
- отключи антивирус
- получи чужой доступ

Поведение:

- allowed: false
- requires_confirmation: false
- risk_level: high

Ответ должен спокойно объяснить, что JARVIS не может выполнить опасное действие.

#### idea

Команда неизвестна, но может быть идеей на будущее.

Поведение:

- allowed: false
- requires_confirmation: false
- risk_level: unknown

Ответ должен сказать, что команда пока не поддерживается, но её можно сохранить как будущую идею.

### 4. Нормализация

SafeActionRouter должен:

- убирать пробелы в начале и конце;
- приводить команду к нижнему регистру;
- нормально работать с пустой строкой.

Если команда пустая:

- category: empty
- risk_level: low
- allowed: false
- requires_confirmation: false

### 5. DialogueManager

Если нужно, добавить методы:

- action_requires_confirmation_response(action_description)
- forbidden_action_response(action_description)
- future_idea_response(action_description)
- safe_action_response(action_description)

Ответы должны быть естественными, спокойными и на русском языке.

Примеры:

Для подтверждения:

Исмаил, это действие требует подтверждения: отправить письмо. Я не буду выполнять его без вашего разрешения.

Для запрета:

Исмаил, я не могу выполнить это действие, потому что оно может быть опасным.

Для идеи:

Исмаил, я пока не умею выполнять эту команду, но могу сохранить её как идею для будущего.

### 6. CommandProcessor integration

CommandProcessor должен использовать SafeActionRouter.

Логика:

- если команда уже известна CommandProcessor — вернуть обычный ответ;
- если команда похожа на действие — передать её в SafeActionRouter;
- если SafeActionRouter вернул confirmation_required — ответить пользователю, что нужно подтверждение;
- если SafeActionRouter вернул forbidden — отказать;
- если SafeActionRouter вернул idea — вернуть идею на будущее.

Важно:

CommandProcessor всё ещё НЕ должен выполнять реальные действия.

### 7. Kernel integration

JARVISKernel должен создавать SafeActionRouter как системный сервис.

Добавить сервис:

- action_router

Метод get_service("action_router") должен возвращать SafeActionRouter.

Старые сервисы должны продолжить работать:

- logger
- event_bus
- module_manager
- command_processor

### 8. Tests

Добавить tests/unit/test_action_router.py

Тесты должны проверять:

- создание SafeActionRouter без профиля;
- создание SafeActionRouter с профилем;
- informational;
- safe_action;
- confirmation_required;
- forbidden;
- idea;
- empty;
- allowed;
- requires_confirmation;
- risk_level;
- response.

Обновить tests/unit/test_command_processor.py:

- команда "отправь письмо" должна требовать подтверждение;
- команда "удали файл" должна требовать подтверждение;
- команда "удали system32" должна быть forbidden;
- неизвестная команда должна быть idea/unknown без выполнения.

Обновить tests/unit/test_kernel.py:

- get_service("action_router");
- старые сервисы должны работать;
- неизвестный сервис всё ещё вызывает KernelError.

## Проверки

После изменений должны проходить команды:

python -m py_compile core/action_router.py
python -m py_compile core/command_processor.py
python -m py_compile core/kernel.py
python -m py_compile dialogue/dialogue_manager.py
python -m tests.unit.test_action_router
python -m tests.unit.test_command_processor
python -m tests.unit.test_kernel
python run.py

## Ожидаемый запуск

Команда:

python run.py

Должна запускать JARVIS в интерактивном режиме.

Примеры:

Пользователь:

отправь письмо

JARVIS:

Исмаил, это действие требует подтверждения: отправь письмо. Я не буду выполнять его без вашего разрешения.

Пользователь:

удали system32

JARVIS:

Исмаил, я не могу выполнить это действие, потому что оно может быть опасным.

Пользователь:

кто я

JARVIS:

Исмаил, вы сохранены в профиле как Исмаил.

Пользователь:

выход

JARVIS завершает работу.

## В конце ответа

Покажи:

1. Какие файлы изменены.
2. Что именно изменено.
3. Какие проверки запустить.
4. Какие риски есть.