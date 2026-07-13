# TASK-048 - Voice Dialogue Stop / Mute / Output Safety Controls

## Goal

Add safe session-only voice output stop, mute, skip-next, and status controls for JARVIS voice dialogue and explicit speaking.

## Context

TASK-047 added manual voice dialogue mode and current response speaking after explicit user opt-in. TASK-048 adds a user-facing brake before expanding voice dialogue further.

Current stable commit before this task:

- Commit: `ad8ffd8`
- Message: `Add manual voice dialogue mode`

## Commands Added

- `замолчи`
- `тихо`
- `стоп голос`
- `останови голос`
- `остановить голос`
- `перестань говорить`
- `не говори`
- `отключи речь`
- `выключи речь`
- `снова говори`
- `можешь говорить`
- `включи речь`
- `разреши голос`
- `выключи тихий режим`
- `отключи тихий режим`
- `размутить голос`
- `не озвучивай следующий ответ`
- `пропусти следующую озвучку`
- `следующий ответ не озвучивай`
- `один ответ без голоса`
- `статус голосовой безопасности`
- `статус тихого режима`
- `статус mute`
- `голос заблокирован?`
- `можно ли говорить голосом`

## Safety Boundaries

- No continuous listening.
- No background loops.
- No async or background speech playback.
- No claim that synchronous Windows speech can always be interrupted.
- No cloud TTS.
- No external text/audio services.
- No generated audio files.
- No persisted mute state.
- No persisted voice dialogue state.
- No package installs or downloads.
- All speech remains routed through `VoiceOutputManager`.
- Commands remain routed through `CommandProcessor` and `ActionRouter` conventions.

## Tests

Added or updated:

- `tests/unit/test_voice_output_safety.py`
- `tests/unit/test_voice_output_manager.py`
- `tests/unit/test_command_processor.py`
- `tests/unit/test_voice_command_allowlist.py`

## Manual Verification Commands

```powershell
python -m pytest tests/unit/test_voice_output_safety.py
python -m pytest tests/unit/test_voice_output_manager.py
python -m pytest tests/unit/test_command_processor.py
python -m pytest tests/unit/test_voice_dialogue_mode.py
python -m pytest tests/unit/test_assistant_response_history.py
python -m pytest tests/unit/test_windows_local_tts_backend.py
python -m pytest tests/unit/test_speech_synthesis_backend.py
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
статус голосовой безопасности
включить тестовый голос
скажи: голос работает
замолчи
скажи: это не должно быть озвучено
статус голосовой безопасности
снова говори
скажи: голос снова разрешен
не озвучивай следующий ответ
скажи: этот ответ должен быть пропущен
скажи: этот ответ снова можно озвучить
включить голосовой диалог
статус системы
замолчи
статус системы
снова говори
включить голосовой диалог
статус системы
выключить голос
статус голосовой безопасности
помощь
выход
```

## Expected Result

- Default safety status is not muted.
- Test voice works before mute.
- Mute blocks explicit speaking and disables manual dialogue.
- Status shows muted state.
- Unmute allows explicit speaking again but does not re-enable manual dialogue.
- Skip-next blocks exactly one speech attempt and clears.
- Manual voice dialogue respects mute and skip-next.
- Disabling voice output disables dialogue but does not force mute.
- No cloud TTS, audio files, continuous listening, downloads, installs, or background speech loops.

## Commit Message Suggestion

`Add voice output safety controls`
