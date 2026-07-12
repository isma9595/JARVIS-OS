# Audio Capture Dependencies

JARVIS uses local dependencies for explicit one-shot microphone capture and local Vosk speech recognition.

## Why They Matter

- `numpy` is used by the audio stack to represent captured microphone samples.
- `sounddevice` captures one short microphone recording after an explicit one-shot command.
- `vosk` performs local speech recognition from captured audio.

If one of these packages is missing, JARVIS should explain the missing dependency and show a manual command. JARVIS must not install packages automatically.

## Check From Inside JARVIS

Use one of these commands:

- `проверка аудио зависимостей`
- `проверить аудио зависимости`
- `проверить зависимости микрофона`
- `диагностика микрофона`
- `почему не работает микрофон`
- `проверить numpy`
- `проверить sounddevice`
- `проверить vosk пакет`

When everything is ready, JARVIS reports that audio capture dependencies are available and suggests the explicit command:

`распознай голос один раз`

## Manual Install Commands

Run only the command for the missing package:

```powershell
python -m pip install numpy
python -m pip install sounddevice
python -m pip install vosk
```

## Safety Rules

- JARVIS does not install packages automatically.
- JARVIS does not download anything automatically.
- JARVIS does not enable continuous listening.
- JARVIS does not start a background listener.
- JARVIS does not send audio to cloud services.
- JARVIS does not store audio files by default.
- JARVIS does not execute recognized text automatically.
