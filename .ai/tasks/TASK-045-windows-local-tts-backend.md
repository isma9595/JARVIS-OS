# TASK-045 — Windows Local TTS Backend / Real Voice Playback Gate

## Goal

Add a gated local Windows text-to-speech backend for real voice playback.

## Context

TASK-044 added the voice output foundation:

- `SpeechSynthesisBackend`
- `DryRunSpeechSynthesisBackend`
- `VoiceOutputManager`
- `OFF` and `DRY_RUN` modes
- explicit voice output commands
- no real playback
- no cloud
- no audio file saving
- no automatic voice replies

## Commands Added

Diagnostics:

- `диагностика локального голоса`
- `проверить локальный голос`
- `проверить голос windows`
- `статус локального голоса windows`
- `доступен ли голос windows`

Enable local playback:

- `включить локальный голос`
- `включить голос windows`
- `включи локальный голос`
- `режим голоса windows`
- `режим голоса локальный`

Test:

- `тест локального голоса`
- `проверка локального голоса`

Existing explicit speak commands continue to work:

- `скажи: <текст>`
- `произнеси: <текст>`
- `озвучь: <текст>`

## Safety Boundaries

- No cloud TTS.
- No external text/audio services.
- No audio file saving.
- No background speech loops.
- No automatic voice replies.
- No installs or downloads.
- No `shell=True`.
- No interpolation of user text into PowerShell.
- User text is passed through `JARVIS_TTS_TEXT`.
- Static PowerShell scripts only.
- CommandProcessor and ActionRouter boundaries are preserved.

## Tests

- `tests/unit/test_windows_local_tts_backend.py`
- `tests/unit/test_speech_synthesis_backend.py`
- `tests/unit/test_voice_output_manager.py`
- `tests/unit/test_command_processor.py`
- voice recognition regression tests from TASK-038 through TASK-043

## Manual Verification Commands

```powershell
python -m pytest tests/unit/test_windows_local_tts_backend.py
python -m pytest tests/unit/test_speech_synthesis_backend.py
python -m pytest tests/unit/test_voice_output_manager.py
python -m pytest tests/unit/test_command_processor.py
python -m pytest tests/unit/test_voice_recognition_typed_simulation.py
python -m pytest tests/unit/test_voice_recognition_corrections.py
python -m pytest tests/unit/test_voice_command_confirmation_flow.py
python -m pytest tests/unit/test_voice_command_history.py
python -m pytest tests/unit/test_voice_command_allowlist.py
python -m pytest tests/unit/test_one_shot_vosk_real_recognition.py
python -m pytest
.\scripts\health_check.ps1
git status
```

Manual `run.py` flow:

```text
статус голосового ответа
диагностика локального голоса
включить локальный голос
статус голосового ответа
тест локального голоса
скажи: Ассаламу алайкум Исмаил
произнеси: локальный голос работает
выключить голос
скажи: это не должно быть произнесено
включить тестовый голос
скажи: это тестовый режим
выключить голос
помощь
выход
```

## Expected Result

- Voice output starts `OFF`.
- Local Windows TTS diagnostics explain availability.
- Real local voice can be enabled only if available.
- Real playback happens only for explicit speak/test commands.
- If unavailable, the response is graceful and `DRY_RUN` still works.
- Disabling stops speech.
- No cloud, no audio files, no automatic voice replies.
- Full tests and health check pass.

## Commit Message Suggestion

`Add Windows local TTS backend gate`
