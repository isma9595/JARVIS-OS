# Vosk Settings

## Goal

Локальное безопасное сохранение настроек Vosk.

## Stored values

- vosk_model_path
- vosk_language

## Storage

config/local/vosk_settings.json

## Git safety

Файл config/local/vosk_settings.json должен игнорироваться через:

config/local/*.json

## Commands

- сохранить путь модели vosk ...
- настройки vosk
- очистить путь модели vosk
- язык vosk
- установить язык vosk ru

## Safety rules

- no audio recording
- no microphone activation
- no dependency installation
- no model download
- local only
- do not commit local JSON settings
