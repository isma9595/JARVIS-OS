# TASK-012 — Voice Input Foundation

## Роль Codex

Ты инженер-исполнитель проекта JARVIS OS.

Архитектурные решения не принимаешь самостоятельно.
Работаешь строго по задаче.

## Главный архитектурный принцип

JARVIS OS должен всегда оставаться расширяемой платформой.

Voice Input должен быть построен так, чтобы в будущем можно было добавить:

- микрофон;
- wake word;
- локальное распознавание речи;
- Whisper;
- Vosk;
- Windows Speech Recognition;
- голосовой ответ;
- голосовые команды;
- screen awareness;
- workflow automation;
- безопасное подтверждение действий голосом.

Любое изменение должно сохранять модульность проекта.

## Цель

Добавить Voice Input Foundation — фундамент голосового ввода.

На этом этапе JARVIS НЕ должен реально слушать микрофон.

Он должен только:

- иметь отдельный слой voice;
- принимать “распознанный текст” как будто он пришёл из голоса;
- передавать этот текст в CommandProcessor;
- возвращать ответ;
- сохранять безопасность SafeActionRouter;
- не выполнять реальные системные действия;
- не использовать внешние библиотеки.

## Приватность

Голос пользователя является чувствительными данными.

В этой задаче запрещено:

- включать микрофон;
- записывать аудио;
- сохранять аудио;
- отправлять аудио в интернет;
- использовать внешние API;
- использовать облачные сервисы;
- подключать онлайн-распознавание.

В будущем микрофон можно будет включать только после явного разрешения пользователя.

## Разрешённые зоны изменений

Можно изменять или создавать только:

- voice/
- voice/__init__.py
- voice/voice_input_manager.py
- core/kernel.py
- core/command_processor.py
- dialogue/dialogue_manager.py
- tests/unit/
- .ai/tasks/

Можно создать:

- tests/unit/test_voice_input_manager.py

Можно обновить:

- tests/unit/test_kernel.py
- tests/unit/test_command_processor.py
- tests/unit/test_dialogue_manager.py

## Запрещено

Нельзя:

- менять brain;
- менять memory;
- менять users;
- менять security;
- менять integrations;
- менять vision;
- реализовывать screen awareness;
- реализовывать workflow automation;
- реализовывать installer;
- включать микрофон;
- записывать звук;
- использовать внешние библиотеки;
- использовать speech_recognition;
- использовать pyaudio;
- использовать whisper;
- использовать vosk;
- отправлять данные пользователя в интернет;
- выполнять реальные системные команды;
- удалять файлы пользователя.

## Нужно реализовать

### 1. VoiceInputManager

Создать файл:

voice/voice_input_manager.py

В нём создать класс:

VoiceInputManager

Он должен принимать:

- command_processor
- dialogue_manager
- user_profile

Если параметры отсутствуют, использовать безопасные значения по умолчанию.

### 2. Состояние VoiceInputManager

VoiceInputManager должен иметь состояние:

- disabled
- ready
- listening
- stopped

По умолчанию:

disabled

Почему disabled?

Потому что микрофон и голосовые функции должны включаться только по разрешению пользователя.

### 3. Методы VoiceInputManager

Добавить методы:

- get_state()
- enable()
- disable()
- start_listening()
- stop_listening()
- process_recognized_text(text)
- is_enabled()

### 4. Поведение методов

#### enable()

Переводит состояние в:

ready

Возвращает словарь:

{
  "state": "ready",
  "message": "..."
}

#### disable()

Переводит состояние в:

disabled

#### start_listening()

Если VoiceInputManager disabled:

- не начинать слушать;
- вернуть понятное сообщение, что голосовой ввод отключён.

Если ready:

- перевести состояние в listening.

Важно:

На этом этапе start_listening() НЕ должен реально включать микрофон.

#### stop_listening()

Если состояние listening:

- перевести в ready.

Если уже не listening:

- вернуть понятное сообщение.

#### process_recognized_text(text)

Принимает текст, как будто он уже распознан из голоса.

Пример:

process_recognized_text("кто я")

Должен передать текст в CommandProcessor и вернуть его результат.

Если текст пустой:

- вернуть intent voice.empty
- should_exit false
- понятный ответ.

### 5. DialogueManager

Добавить методы, если нужно:

- voice_disabled_response()
- voice_enabled_response()
- voice_listening_started_response()
- voice_listening_stopped_response()
- voice_empty_input_response()
- voice_not_real_microphone_response()

Примеры:

Голосовой ввод подготовлен, но микрофон в этой версии не включается.

Голосовой ввод отключён. Я не слушаю микрофон.

Я принял распознанный текст и обработал его как команду.

### 6. Kernel integration

JARVISKernel должен создавать VoiceInputManager как системный сервис.

Добавить сервис:

- voice_input_manager

Метод get_service("voice_input_manager") должен возвращать VoiceInputManager.

Старые сервисы должны продолжить работать:

- logger
- event_bus
- module_manager
- command_processor
- action_router
- idea_manager
- memory_manager

Kernel startup должен выводить:

VoiceInputManager: OK

Но важно:

Это означает, что фундамент голосового ввода создан.
Это НЕ означает, что микрофон включён.

### 7. CommandProcessor integration

CommandProcessor должен понимать команды:

#### Голосовой статус

Команды:

- голос
- статус голоса
- голосовой ввод
- голосовой режим

Intent:

voice.status

Ответ должен объяснить:

- голосовой фундамент есть;
- микрофон пока не включается;
- голосовые команды будут добавлены безопасно позже.

#### Включить голос

Команды:

- включи голос
- включить голосовой ввод
- активируй голос

Intent:

voice.enable

Поведение:

- на этом этапе можно только вернуть сообщение, что голосовой фундамент подготовлен;
- реальный микрофон не включать.

#### Отключить голос

Команды:

- отключи голос
- отключить голосовой ввод

Intent:

voice.disable

Ответ:

Голосовой ввод отключён. Я не слушаю микрофон.

### 8. Tests

Добавить:

tests/unit/test_voice_input_manager.py

Тесты должны проверять:

- создание VoiceInputManager без параметров;
- начальное состояние disabled;
- enable();
- disable();
- start_listening() когда disabled;
- start_listening() когда ready;
- stop_listening();
- process_recognized_text("кто я");
- process_recognized_text("").

Обновить tests/unit/test_command_processor.py

Проверить команды:

- голос
- статус голоса
- включи голос
- отключи голос

Проверить intents:

- voice.status
- voice.enable
- voice.disable

Обновить tests/unit/test_kernel.py

Проверить:

- get_service("voice_input_manager");
- list_services() содержит voice_input_manager;
- get_system_status() содержит voice_input_manager;
- старые сервисы продолжают работать;
- неизвестный сервис всё ещё вызывает KernelError.

Обновить tests/unit/test_dialogue_manager.py

Проверить новые voice-методы DialogueManager.

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

Должна запускать JARVIS в интерактивном режиме.

При запуске должно быть:

VoiceInputManager: OK

Пример команд:

Пользователь:

голос

JARVIS:

Исмаил, голосовой фундамент подготовлен, но микрофон в этой версии не включается.

Пользователь:

включи голос

JARVIS:

Исмаил, голосовой ввод подготовлен, но реальный микрофон пока не включается. Это будет добавлено безопасно позже.

Пользователь:

отключи голос

JARVIS:

Исмаил, голосовой ввод отключён. Я не слушаю микрофон.

Пользователь:

выход

JARVIS завершает работу.

## В конце ответа

Покажи:

1. Какие файлы изменены.
2. Что именно изменено.
3. Какие проверки запустить.
4. Какие риски есть.