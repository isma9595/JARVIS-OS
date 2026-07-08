# TASK-013 — Voice Command Simulation & Confirmation Flow

## Роль Codex

Ты инженер-исполнитель проекта JARVIS OS.

Архитектурные решения не принимаешь самостоятельно.
Работаешь строго по задаче.

## Главный архитектурный принцип

JARVIS OS должен всегда оставаться расширяемой платформой.

Голосовой канал должен быть построен так, чтобы в будущем можно было добавить:

- реальный микрофон;
- wake word;
- локальное распознавание речи;
- Whisper;
- Vosk;
- Windows Speech Recognition;
- голосовое подтверждение;
- безопасное выполнение действий;
- screen awareness;
- workflow automation;
- плагины;
- разные уровни доступа.

Любое изменение должно сохранять модульность проекта.

## Цель

Добавить симуляцию голосовых команд и безопасный confirmation flow.

На этом этапе JARVIS НЕ должен реально слушать микрофон.

Он должен только:

- принимать текстовую команду как имитацию голосовой команды;
- передавать её в VoiceInputManager;
- VoiceInputManager должен передавать распознанный текст в CommandProcessor;
- рискованные голосовые команды должны требовать подтверждения;
- запрещённые голосовые команды должны блокироваться;
- подтверждение должно быть безопасной симуляцией, без реального выполнения системных действий;
- все старые команды должны продолжить работать.

## Приватность

Голосовые данные являются чувствительными.

В этой задаче запрещено:

- включать микрофон;
- записывать аудио;
- сохранять аудио;
- отправлять аудио в интернет;
- использовать внешние API;
- использовать облачные сервисы;
- использовать внешние библиотеки;
- подключать реальное распознавание речи.

В будущем микрофон можно будет включать только после явного разрешения пользователя.

## Разрешённые зоны изменений

Можно изменять или создавать только:

- voice/
- voice/voice_input_manager.py
- core/kernel.py
- core/command_processor.py
- dialogue/dialogue_manager.py
- tests/unit/
- .ai/tasks/

Можно обновить:

- tests/unit/test_voice_input_manager.py
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
- менять vision;
- менять ideas;
- реализовывать настоящий микрофон;
- реализовывать screen awareness;
- реализовывать workflow automation;
- реализовывать installer;
- реализовывать embeddings;
- реализовывать vector database;
- использовать pyaudio;
- использовать speech_recognition;
- использовать whisper;
- использовать vosk;
- записывать звук;
- отправлять данные пользователя в интернет;
- выполнять реальные системные команды;
- удалять файлы пользователя.

## Нужно реализовать

### 1. VoiceInputManager: обработка голосовой команды

Обновить файл:

voice/voice_input_manager.py

Добавить или улучшить методы:

- process_recognized_text(text)
- has_pending_confirmation()
- get_pending_confirmation()
- clear_pending_confirmation()
- confirm_pending_action()
- cancel_pending_action()

VoiceInputManager должен хранить pending confirmation только в памяти процесса.

Ничего не записывать в файлы.

Пример структуры pending confirmation:

{
  "text": "отправь письмо",
  "channel": "voice",
  "risk": "confirmation_required"
}

### 2. Поведение process_recognized_text(text)

Если text пустой:

- intent: voice.empty
- should_exit: false
- ответ: что голосовая команда пустая.

Если text обычный и безопасный:

Пример:

process_recognized_text("кто я")

Должен передать текст в CommandProcessor и вернуть обычный результат, но с пометкой:

- channel: voice
- source: recognized_text

Если text рискованный и CommandProcessor / SafeActionRouter возвращает confirmation_required:

- не выполнять действие;
- сохранить pending confirmation;
- вернуть intent: voice.confirmation_required;
- should_exit: false;
- ответить, что голосовая команда требует подтверждения.

Если text запрещённый:

- не сохранять pending confirmation;
- вернуть ответ о блокировке.

### 3. Confirmation flow

Добавить методы:

#### confirm_pending_action()

Если pending confirmation отсутствует:

- intent: voice.confirmation.none
- should_exit: false
- ответ: нет голосового действия для подтверждения.

Если pending confirmation есть:

- очистить pending confirmation;
- НЕ выполнять реальное действие;
- intent: voice.confirmation.confirmed
- should_exit: false
- ответ: подтверждение принято, но реальное выполнение действий будет добавлено позже безопасно.

#### cancel_pending_action()

Если pending confirmation отсутствует:

- intent: voice.confirmation.none
- should_exit: false
- ответ: нет голосового действия для отмены.

Если pending confirmation есть:

- очистить pending confirmation;
- intent: voice.confirmation.cancelled
- should_exit: false
- ответ: голосовое действие отменено.

### 4. CommandProcessor: команды симуляции голоса

CommandProcessor должен понимать команды:

#### Симуляция голосовой команды

Команды:

- голосовая команда ...
- голосом ...
- как голос ...
- распознанный текст ...

Примеры:

голосовая команда кто я

голосом покажи профиль

как голос статус системы

распознанный текст вспомни про муниципальные письма

Intent:

voice.command.simulated

Поведение:

- извлечь текст после префикса;
- передать его в VoiceInputManager.process_recognized_text(text);
- вернуть результат.

Если текст после префикса пустой:

- intent: voice.empty

#### Подтверждение голосовой команды

Команды:

- подтвердить голосовую команду
- подтверждаю голосовую команду
- голос подтверждаю
- подтвердить голосом

Intent:

voice.confirmation.confirmed или voice.confirmation.none

Поведение:

- вызвать VoiceInputManager.confirm_pending_action()

#### Отмена голосовой команды

Команды:

- отменить голосовую команду
- отмени голосовую команду
- голос отмена
- отменить голосом

Intent:

voice.confirmation.cancelled или voice.confirmation.none

Поведение:

- вызвать VoiceInputManager.cancel_pending_action()

### 5. Без циклической зависимости

Если CommandProcessor не может напрямую получить VoiceInputManager из-за порядка создания сервисов, реализовать один из безопасных вариантов:

Вариант A:

- добавить в CommandProcessor метод set_voice_input_manager(voice_input_manager)
- Kernel после создания VoiceInputManager вызывает этот метод.

Вариант B:

- передать provider/callback в CommandProcessor.

Главное:

- не ломать архитектуру;
- не создавать глобальные переменные;
- не импортировать Kernel внутрь CommandProcessor;
- не создавать циклический импорт.

### 6. DialogueManager

Добавить методы, если нужно:

- voice_command_received_response(text)
- voice_confirmation_required_response(text)
- voice_confirmation_confirmed_response(text)
- voice_confirmation_cancelled_response(text)
- voice_confirmation_none_response()
- voice_forbidden_response(text)
- voice_empty_input_response()

Ответы должны быть на русском языке, спокойные и короткие.

Примеры:

Исмаил, я принял голосовую команду: кто я.

Исмаил, эта голосовая команда требует подтверждения: отправь письмо.

Исмаил, подтверждение принято. Реальное выполнение действий будет добавлено позже безопасно.

Исмаил, голосовое действие отменено.

Исмаил, сейчас нет голосового действия для подтверждения.

### 7. Kernel integration

JARVISKernel уже должен создавать VoiceInputManager.

Проверить, что:

- get_service("voice_input_manager") работает;
- list_services() содержит voice_input_manager;
- get_system_status() содержит voice_input_manager.

Если используется set_voice_input_manager(), вызвать его в Kernel после создания VoiceInputManager.

Старые сервисы должны продолжить работать:

- logger
- event_bus
- module_manager
- command_processor
- action_router
- idea_manager
- memory_manager
- voice_input_manager

### 8. Tests

Обновить:

tests/unit/test_voice_input_manager.py

Проверить:

- process_recognized_text("кто я");
- process_recognized_text("");
- process_recognized_text("отправь письмо") создаёт pending confirmation;
- has_pending_confirmation();
- get_pending_confirmation();
- confirm_pending_action();
- cancel_pending_action();
- forbidden voice command не создаёт pending confirmation.

Обновить:

tests/unit/test_command_processor.py

Проверить команды:

- голосовая команда кто я
- голосом покажи профиль
- как голос статус системы
- распознанный текст вспомни про муниципальные письма
- голосовая команда отправь письмо
- подтвердить голосовую команду
- отменить голосовую команду

Проверить intents:

- voice.command.simulated
- voice.empty
- voice.confirmation_required
- voice.confirmation.confirmed
- voice.confirmation.cancelled
- voice.confirmation.none

Обновить:

tests/unit/test_dialogue_manager.py

Проверить новые voice confirmation ответы.

Обновить:

tests/unit/test_kernel.py

Проверить:

- voice_input_manager всё ещё системный сервис;
- CommandProcessor связан с VoiceInputManager, если используется set_voice_input_manager();
- старые сервисы не сломаны.

## Проверки

После изменений должны проходить команды:

python -m py_compile voice/voice_input_manager.py
python -m py_compile core/command_processor.py
python -m py_compile core/kernel.py
python -m py_compile dialogue/dialogue_manager.py
python -m tests.unit.test_voice_input_manager
python -m tests.unit.test_command_processor
python -m tests.unit.test_dialogue_manager
python -m tests.unit.test_kernel
python run.py

## Ожидаемый запуск

Команда:

python run.py

Примеры:

Пользователь:

голосовая команда кто я

JARVIS:

Исмаил, я принял голосовую команду: кто я.
Исмаил, вы — Исмаил.

Пользователь:

голосовая команда отправь письмо

JARVIS:

Исмаил, эта голосовая команда требует подтверждения: отправь письмо.

Пользователь:

подтвердить голосовую команду

JARVIS:

Исмаил, подтверждение принято. Реальное выполнение действий будет добавлено позже безопасно.

Пользователь:

голосовая команда удали system32

JARVIS:

Исмаил, я не могу выполнить эту голосовую команду, потому что она может быть опасной.

Пользователь:

выход

JARVIS завершает работу.

## В конце ответа

Покажи:

1. Какие файлы изменены.
2. Что именно изменено.
3. Какие проверки запустить.
4. Какие риски есть.