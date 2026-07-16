# TASK-086 - User Language Preference

## Summary

TASK-086 adds one persistent assistant interaction language preference.
The canonical supported language codes are:

- `ru-RU` - Russian
- `en-US` - English

Russian remains the default because existing installations and historical
command behavior are Russian-first. Missing, invalid, unsupported, or corrupt
profile values safely fall back to `ru-RU`.

## Boundary

The single source of truth is:

`UserProfileManager` -> `ApplicationLanguageManager` -> `JarvisAppService`
-> text, voice, and provider-language consumers.

Desktop Shell uses AppService only. It does not read or write profile storage.

## Normalization

Supported aliases:

- Russian: `русский`, `русский язык`, `ru`, `ru-ru`, `russian`
- English: `английский`, `английский язык`, `english`, `en`, `en-us`

Normalization ignores surrounding whitespace and is case-insensitive.
Unsupported languages are rejected without changing the current preference.

## Persistence And Fallback

The preference is stored in the existing user profile `language` field.
Profiles without the field remain valid. Saves use the existing profile
boundary and atomic replace. Corrupt storage or raw persistence exceptions
produce redacted safe fallback messages and do not expose credentials or stack
traces.

Tests use temporary profile files only.

## AppService API

AppService exposes:

- `get_language_preference()`
- `set_language_preference(language_code)`
- `reset_language_preference()`

Returned DTOs are immutable, serializable, and redacted.

## Commands

Russian examples:

- `текущий язык`
- `язык английский`
- `переключить язык на русский`
- `сбросить язык`

English examples after English is selected:

- `current language`
- `set language to Russian`
- `language English`
- `reset language`

Vague requests such as `поменяй язык` require clarification. Clarification
options are bounded to Russian and English and do not change the preference
until a supported option is selected.

## Voice And Provider Propagation

One-shot voice receives the canonical runtime locale hint:

- `ru-RU` for Russian
- `en-US` for English

No model is downloaded and no microphone capture starts when changing the
preference. Unavailable English voice resources fail safely.

Provider requests receive the preferred provider language (`ru` or `en`) when
a provider request is explicitly made. Changing the preference does not call a
provider, read credentials, or use the network.

## Known Limitations

This task does not implement automatic language detection, automatic
translation, full GUI localization, operating-system language changes, keyboard
layout switching, or languages beyond Russian and English.

Future languages should be added by extending `SupportedLanguage`, aliases,
localized messages, voice mapping, provider mapping, and focused tests.

## Verification Order

1. `python -m pytest tests/unit/test_user_language_preference.py -v`
2. `python -m pytest tests/integration/test_task_086_user_language_preference.py -v`
3. `powershell -ExecutionPolicy Bypass -File scripts/assistant_smoke.ps1`
4. Targeted compatibility tests for language manager, user profile, provider
   language policy, AppService, and Desktop Shell.
5. Full pytest suite and deprecation-warning run.
6. Health check, diff check, status, stat, and changed-file review.

