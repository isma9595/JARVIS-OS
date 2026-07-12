# Safe Voice Command Allowlist

TASK-039 adds a small safe allowlist for one-shot Vosk voice recognition after the TASK-038 confirmation flow.

## Why it exists

Some voice commands are read-only and low-risk. Requiring typed confirmation for every recognized status or help command slows normal use without improving safety much.

The allowlist lets only known safe commands run without an extra `да / нет` confirmation.

## Initially allowed commands

Read-only canonical commands:

- статус системы
- помощь
- статус vosk
- проверить модель vosk
- проверка аудио зависимостей
- диагностика микрофона
- проверить numpy
- проверить sounddevice
- проверить vosk пакет
- как тебя зовут
- имя ассистента
- ожидающая голосовая команда
- сколько идей
- список идей
- что ты запомнил
- локальная память

Aliases may normalize to these canonical commands, but unknown text is never treated as safe.

## Conservative safe aliases

TASK-040 adds conservative normalization and explicit safe aliases for known read-only commands only.

Normalization handles leading and trailing spaces, duplicate spaces, case differences, `ё` / `е`, and punctuation. It does not use broad fuzzy matching.

Allowed alias examples:

- статус систем -> статус системы
- статусе системы -> статус системы
- статуя система -> статус системы
- помоги -> помощь
- справка -> помощь
- статус воска -> статус vosk
- проверка аудио зависимости -> проверка аудио зависимостей
- проверить аудио зависимости -> проверка аудио зависимостей
- как твое имя -> как тебя зовут

Aliases are explicit code entries. Only read-only commands may have aliases. Risky commands are never guessed into the allowlist.

## Safety boundaries

Only read-only commands are allowed. Modifying, file, system, shell, install, download, email, internet, automation, and destructive commands still require confirmation or are blocked by the normal safety flow.

Allowlisted commands are still executed through `CommandProcessor`. The allowlist does not duplicate command behavior and does not bypass `ActionRouter`.

## What still requires confirmation

Examples that are not allowlisted:

- открой браузер
- открой файл
- запомни ...
- добавь идею ...
- удали файл
- очисти память
- установи ...
- скачай ...
- запусти ...
- открой ...
- закрой ...
- выполни powershell ...
- cmd
- отправь ...
- измени ...
- включи постоянное прослушивание

## Audio and listening policy

Continuous listening is not enabled.

Background microphone listeners are not added.

Audio is not sent to cloud services.

Audio files are not saved by default.

## Future direction

User-customizable safe command policy can be considered after more safety layers exist. Until then, the allowlist stays small, explicit, read-only, and controlled in code.
