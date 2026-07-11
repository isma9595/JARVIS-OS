# TASK-033 — Assistant Name Configuration Commands

## Goal

Add safe Russian-first commands so the user can view, change, and reset the assistant name at any time.

## Why This Is Needed

After TASK-032 live `run.py` verification, the assistant greeted the user with a custom assistant name from profile data. That behavior is useful, but it must be visible and controllable through explicit local commands instead of being hidden only in profile setup data.

## Commands Added

View assistant name:

- `как тебя зовут`
- `как зовут ассистента`
- `имя ассистента`
- `покажи имя ассистента`

Change assistant name:

- `измени имя ассистента на JARVIS`
- `поменяй имя ассистента на JARVIS`
- `назови себя JARVIS`
- `теперь тебя зовут JARVIS`
- `зови себя JARVIS`

Reset assistant name:

- `сбрось имя ассистента`
- `верни имя ассистента по умолчанию`
- `сбросить имя ассистента`
- `удали имя ассистента`

## Profile Behavior

- Default assistant name remains `JARVIS`.
- The command processor updates the in-memory profile and dialogue profile together.
- If a saved profile manager is provided, the new assistant name is persisted through `UserProfileManager`.
- During normal `run.py` use, a loaded saved profile is persisted back through the existing local profile path.
- No separate storage file is created.

## Safety Rules

- Names are trimmed.
- Empty names are rejected.
- Names longer than 40 characters are rejected.
- Multiline names and control characters are rejected.
- Allowed characters are Russian letters, English letters, digits, spaces, hyphen, and underscore.
- Assistant names are stored as data only and are not executed or routed as commands.

## Intentionally Not Changed

- No voice functionality was added.
- No real speech recognition was enabled.
- No microphone capture was started.
- Vosk recognition, gates, dry-run logic, and runtime loading were not changed.
- No automation was added.
- `run.py` was not modified.

## Tests

Added or updated tests for:

- Default assistant name fallback to `JARVIS`.
- Setting and resetting assistant name.
- Rejecting empty, too-long, multiline, control-character, and unsupported-character names.
- Viewing assistant name through Russian commands.
- Changing assistant name through Russian commands.
- Greeting using the current assistant name.
- Resetting assistant name to `JARVIS`.
- Help mentioning assistant name configuration.
- Existing TASK-032 command behavior remaining compatible.

## Manual Verification Commands

Run automated verification:

```powershell
python -m pytest tests/unit/test_user_profile.py
python -m pytest tests/unit/test_command_processor.py
python -m pytest
.\scripts\health_check.ps1
```

Run interactive verification:

```powershell
python run.py
```

Then test:

```text
как тебя зовут
имя ассистента
привет
измени имя ассистента на JARVIS
как тебя зовут
привет
назови себя ВанДам
как тебя зовут
привет
сбрось имя ассистента
как тебя зовут
привет
помощь
```

## Expected Result

- User can view assistant name.
- User can change assistant name.
- User can reset assistant name.
- Greeting uses the current assistant name.
- Help mentions assistant name settings.
- Invalid names are handled safely.
- No microphone starts.
- No real recognition starts.
- Full test suite passes.
- Health check passes.
- Commit happens only after user verification.

## Commit Message Suggestion

`Add assistant name configuration commands`
