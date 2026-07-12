# Vosk Model Readiness

TASK-035 adds a safe check for the configured Vosk model folder.

Model readiness means JARVIS can inspect the configured path and report whether it looks like a manually extracted Vosk model folder. The check is filesystem-only: path exists, path is a directory, directory is empty or not, and common Vosk model markers such as `conf`, `am`, `graph`, `ivector`, `README`, or model/config files are present.

Model readiness does not mean real recognition is enabled. TASK-035 does not import Vosk, does not load a model, does not start the microphone, does not record audio, does not recognize speech, and does not execute recognized text.

## Manual Installation Flow

1. Download a Vosk model manually from a trusted source.
2. Extract the archive manually.
3. Put the extracted model folder in a local folder such as:

```text
C:\JARVIS-OS\models\<model-folder>
```

For example, you may choose a Russian small-model Vosk variant, without assuming it is the latest version.

4. Tell JARVIS where the extracted model folder is:

```text
установи путь модели vosk C:\JARVIS-OS\models\<model-folder>
```

5. Check readiness:

```text
проверить модель vosk
статус vosk
```

## States

- Path configured: JARVIS has a saved path string.
- Model folder looks valid: the saved path points to a directory with common Vosk model markers.
- Real recognition enabled: not part of TASK-035. This requires a later approved task.

## Commands

- `проверить модель vosk`
- `готовность модели vosk`
- `диагностика модели vosk`
- `модель vosk статус`
- `проверка модели vosk`
- `проверить установленную модель vosk`
- `как установить модель vosk`
- `инструкция установки модели vosk`
- `куда положить модель vosk`

TASK-035 exists so the user can prepare the model folder safely before any future real local recognition task.
