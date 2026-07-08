# TASK-014 — Voice Channel Polish & Command Aliases

## Роль Codex

Ты инженер-исполнитель проекта JARVIS OS.

Архитектурные решения не принимаешь самостоятельно.
Работаешь строго по задаче.

## Главный архитектурный принцип

JARVIS OS должен всегда оставаться расширяемой платформой.

Голосовой канал должен быть построен так, чтобы в будущем можно было добавить:

- настоящий микрофон;
- wake word;
- локальное распознавание речи;
- Whisper;
- Vosk;
- Windows Speech Recognition;
- голосовое подтверждение;
- команды через плагины;
- screen awareness;
- workflow automation;
- разные уровни доступа.

Любое изменение должно сохранять модульность проекта.

## Цель

Улучшить голосовой канал и добавить естественные псевдо-голосовые команды.

На этом этапе JARVIS НЕ должен реально слушать микрофон.

Он должен только:

- лучше понимать голосовые алиасы;
- поддерживать обращение “джарвис ...”;
- поддерживать команды “скажи ...”, “спроси ...”, “голосом ...”;
- поддерживать короткое подтверждение “подтверждаю”;
- поддерживать короткую отмену “отмена”;
- сохранять безопасный confirmation flow;
- не выполнять реальные системные действия;
- сохранить совместимость со всеми существующими командами.

## Приватность и безопасность

В этой задаче запрещено:

- включать микрофон;
- записывать аудио;
- сохранять аудио;
- отправлять аудио в интернет;
- использовать внешние API;
- использовать облачные сервисы;
- использовать внешние библиотеки;
- использовать pyaudio;
- использовать speech_recognition;
- использовать whisper;
- использовать vosk;
- выполнять реальные системные команды;
- удалять файлы пользователя.

Подтверждение голосовой команды остаётся только безопасной симуляцией.

## Разрешённые зоны изменений

Можно изменять или создавать только:

- voice/
- voice/voice_input_manager.py
- core/command_processor.py
- core/kernel.py
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
- использовать внешние библиотеки;
- отправлять данные пользователя в интернет;
- выполнять реальные системные команды.

## Нужно реализовать

### 1. VoiceInputManager: нормализация голосового текста

Обновить файл:

voice/voice_input_manager.py

Добавить методы:

- normalize_voice_text(text)
- extract_voice_command(text)
- is_voice_alias(text)
- is_voice_confirmation(text)
- is_voice_cancel(text)

### 2. normalize_voice_text(text)

Метод должен:

- принимать строку;
- убирать лишние пробелы;
- приводить текст к нижнему регистру;
- безопасно обрабатывать None;
- возвращать пустую строку, если текста нет.

Примеры:

"  Джарвис   кто Я  " -> "джарвис кто я"

None -> ""

### 3. extract_voice_command(text)

Метод должен извлекать реальную команду из голосовых алиасов.

Поддержать префиксы:

- голосовая команда ...
- голосом ...
- как голос ...
- распознанный текст ...
- джарвис ...
- jarvis ...
- скажи ...
- спроси ...
- голосом спроси ...
- голосом скажи ...
- джарвис скажи ...
- джарвис спроси ...

Примеры:

джарвис кто я -> кто я

джарвис статус системы -> статус системы

скажи кто я -> кто я

спроси что ты помнишь -> что ты помнишь

голосом спроси статус системы -> статус системы

джарвис скажи покажи память -> покажи память

Если префикса нет — вернуть нормализованный текст.

### 4. is_voice_alias(text)

Должен возвращать true, если команда начинается с голосового префикса:

- голосовая команда
- голосом
- как голос
- распознанный текст
- джарвис
- jarvis
- скажи
- спроси

### 5. is_voice_confirmation(text)

Должен распознавать подтверждение голосовой команды.

Команды:

- подтвердить голосовую команду
- подтверждаю голосовую команду
- голос подтверждаю
- подтвердить голосом
- подтверждаю
- да подтверждаю
- можно
- давай
- выполняй

Важно:

Эти короткие команды должны подтверждать только pending voice confirmation.

Они не должны выполнять реальные действия.

### 6. is_voice_cancel(text)

Должен распознавать отмену голосовой команды.

Команды:

- отменить голосовую команду
- отмени голосовую команду
- голос отмена
- отменить голосом
- отмена
- отбой
- не надо
- стоп

### 7. process_recognized_text(text)

Обновить поведение:

- использовать normalize_voice_text();
- использовать extract_voice_command();
- если после извлечения команда пустая — вернуть voice.empty;
- безопасную команду передавать в CommandProcessor;
- рискованную команду сохранять как pending confirmation;
- запрещённую команду блокировать;
- в результате указывать channel: voice и source: recognized_text.

### 8. CommandProcessor: новые голосовые алиасы

Обновить CommandProcessor.

Он должен понимать как голосовую симуляцию:

- голосовая команда кто я
- голосом кто я
- как голос кто я
- распознанный текст кто я
- джарвис кто я
- jarvis кто я
- скажи кто я
- спроси кто я
- голосом спроси статус системы
- джарвис скажи покажи память

Intent:

voice.command.simulated

Команды подтверждения:

- подтверждаю
- да подтверждаю
- можно
- давай
- выполняй

Если есть pending voice confirmation:

intent:

voice.confirmation.confirmed

Если pending confirmation нет:

intent:

voice.confirmation.none

Команды отмены:

- отмена
- отбой
- не надо
- стоп

Если есть pending voice confirmation:

intent:

voice.confirmation.cancelled

Если pending confirmation нет:

intent:

voice.confirmation.none

Важно:

- обычная команда “стоп” не должна завершать программу;
- программа завершается только старой командой “выход” и её уже существующими вариантами, если они есть;
- не ломать старые команды;
- не ломать SafeActionRouter;
- не выполнять реальные действия.

### 9. DialogueManager

Добавить или улучшить ответы, если нужно:

- voice_command_received_response(text)
- voice_confirmation_required_response(text)
- voice_confirmation_confirmed_response(text)
- voice_confirmation_cancelled_response(text)
- voice_confirmation_none_response()
- voice_forbidden_response(text)
- voice_empty_input_response()

Ответы должны быть короткими, естественными и на русском языке.

Примеры:

Исмаил, я принял голосовую команду: статус системы.

Исмаил, эта голосовая команда требует подтверждения: отправь письмо.

Исмаил, подтверждение принято. Реальное выполнение действий будет добавлено позже безопасно.

Исмаил, голосовое действие отменено.

Исмаил, сейчас нет голосового действия для подтверждения.

### 10. Kernel integration

Проверить:

- voice_input_manager остаётся системным сервисом;
- CommandProcessor связан с VoiceInputManager;
- list_services() содержит voice_input_manager;
- get_system_status() содержит voice_input_manager;
- старые сервисы не сломаны.

### 11. Tests

Обновить tests/unit/test_voice_input_manager.py

Проверить:

- normalize_voice_text(None);
- normalize_voice_text("  Джарвис   кто Я  ");
- extract_voice_command("джарвис кто я");
- extract_voice_command("скажи кто я");
- extract_voice_command("спроси статус системы");
- extract_voice_command("голосом спроси статус системы");
- extract_voice_command("джарвис скажи покажи память");
- is_voice_alias();
- is_voice_confirmation();
- is_voice_cancel();
- process_recognized_text("джарвис кто я");
- process_recognized_text("скажи статус системы");
- process_recognized_text("джарвис отправь письмо") создаёт pending confirmation;
- forbidden voice command не создаёт pending confirmation.

Обновить tests/unit/test_command_processor.py

Проверить команды:

- джарвис кто я
- jarvis статус системы
- скажи кто я
- спроси статус системы
- голосом спроси статус системы
- джарвис скажи покажи память
- джарвис отправь письмо
- подтверждаю
- да подтверждаю
- отмена
- отбой
- стоп

Проверить intents:

- voice.command.simulated
- voice.confirmation_required
- voice.confirmation.confirmed
- voice.confirmation.cancelled
- voice.confirmation.none

Обновить tests/unit/test_dialogue_manager.py

Проверить voice confirmation ответы.

Обновить tests/unit/test_kernel.py

Проверить, что voice_input_manager остаётся сервисом.

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

джарвис кто я

JARVIS:

Исмаил, я принял голосовую команду: кто я.
Исмаил, вы сохранены в профиле как Исмаил.

Пользователь:

джарвис статус системы

JARVIS:

Исмаил, я принял голосовую команду: статус системы.
Исмаил, система работает. Версия: v0.2. Активных сервисов: 8.

Пользователь:

джарвис отправь письмо

JARVIS:

Исмаил, эта голосовая команда требует подтверждения: отправь письмо.

Пользователь:

подтверждаю

JARVIS:

Исмаил, подтверждение принято. Реальное выполнение действий будет добавлено позже безопасно.

Пользователь:

джарвис удали system32

JARVIS:

Исмаил, я не могу выполнить эту голосовую команду, потому что она может быть опасной.

Пользователь:

стоп

JARVIS:

Исмаил, сейчас нет голосового действия для отмены.

Пользователь:

выход

JARVIS завершает работу.

## В конце ответа

Покажи:

1. Какие файлы изменены.
2. Что именно изменено.
3. Какие проверки запустить.
4. Какие риски есть.