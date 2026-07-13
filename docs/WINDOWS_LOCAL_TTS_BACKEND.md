# Windows Local TTS Backend

TASK-045 adds a gated local Windows text-to-speech backend for real voice playback.

## What It Does

- Adds `WindowsLocalSpeechSynthesisBackend`.
- Uses local Windows `System.Speech.Synthesis` through PowerShell.
- Plays speech only after explicit user commands.
- Keeps voice output `OFF` by default.
- Keeps `DRY_RUN` available for safe testing without audio.

## Difference From DRY_RUN

- `DRY_RUN` only prints what JARVIS would say.
- `WINDOWS_LOCAL` uses local Windows TTS and can play real audio.
- Both modes are explicit. JARVIS does not speak every response automatically.

## Safety

- Cloud TTS is not used.
- Text and audio are not sent to external services.
- Generated audio files are not saved.
- No background speech loop is created.
- No automatic replies are spoken.
- User text is passed through `JARVIS_TTS_TEXT` environment variable.
- PowerShell is called with `subprocess.run(..., shell=False)`.
- The PowerShell script is static and does not interpolate user text.
- Text is trimmed and capped before playback.

## Commands

Diagnostics:

- `диагностика локального голоса`
- `проверить локальный голос`
- `проверить голос windows`
- `статус локального голоса windows`
- `доступен ли голос windows`

Enable:

- `включить локальный голос`
- `включить голос windows`
- `включи локальный голос`
- `режим голоса windows`
- `режим голоса локальный`

Disable:

- `выключить голос`
- `отключить голосовой ответ`

Speak explicitly:

- `скажи: <текст>`
- `произнеси: <текст>`
- `озвучь: <текст>`

Test:

- `тест локального голоса`
- `проверка локального голоса`
- `тест голоса`

## Known Limitations

- Requires Windows local speech capability.
- PowerShell and `System.Speech` may be unavailable in some environments.
- Voice selection, speed, and volume are planned for later tasks.
- Tests mock platform and subprocess behavior; they do not require real playback.
