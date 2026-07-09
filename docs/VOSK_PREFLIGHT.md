# Vosk preflight

`VoskLocalBackend` performs read-only prerequisite checks for a future local
Vosk integration. It does not implement speech recognition.

The preflight checks:

- package discoverability through `importlib.util.find_spec("vosk")`;
- whether a model directory path is configured in memory;
- whether that path currently points to an existing directory;
- which prerequisite identifiers are missing.

The package is never imported. The model is not loaded, downloaded, created, or
modified. No microphone is enabled, no audio is recorded, no external command
is executed, and no data is sent over the network.

## Result contract

`VoskLocalBackend.preflight_check()` returns:

```python
{
    "dependency_available": False,
    "model_path_configured": False,
    "model_path_exists": False,
    "ready": False,
    "missing_requirements": ["vosk_dependency", "model_path"],
}
```

`ready` means only that the two prerequisites are detectable. The backend
remains a non-operational skeleton and `is_available()` remains `False`.

`configure_model_path(path)` stores the value only in the current backend
instance. An empty value clears it. There is no configuration-file write.

## Text commands

- `проверка vosk` — show the complete preflight state;
- `чего не хватает для vosk` — list missing prerequisites;
- `укажи путь к модели vosk <path>` — store and check a local path in memory.

These commands do not install Vosk or download a model.
