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
- проверить зависимости микрофона
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

## Safety boundaries

Only read-only commands are allowed. Modifying, file, system, shell, install, download, email, internet, automation, and destructive commands still require confirmation or are blocked by the normal safety flow.

Allowlisted commands are still executed through `CommandProcessor`. The allowlist does not duplicate command behavior and does not bypass `ActionRouter`.

## What still requires confirmation

Examples that are not allowlisted:

- запомни ...
- добавь идею ...
- удали ...
- очисти ...
- установи ...
- скачай ...
- запусти ...
- открой ...
- закрой ...
- выполни powershell ...
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
