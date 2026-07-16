# TASK-078 - One-Shot Voice-to-Answer Path

## Objective

Add a safe AppService-level operation that captures one explicit local voice
request, recognizes it through the existing Vosk one-shot path, and processes
the recognized text through the same typed text execution contract used by the
Desktop Shell.

JARVIS remains a Russian-first end-user assistant. The default runtime locale
is `ru-RU`; Russian typed commands and Russian voice commands remain supported;
the Vosk one-shot path keeps the existing Russian model-language default; and
recognized Cyrillic text is not translated or transliterated before normal
AppService text processing.

## Inspected Baseline

- Branch: `main`
- HEAD: `013f1b9 Add secure provider runtime integration`
- Working tree before edits: clean
- Relevant contracts inspected: `JarvisAppService`, `AppExecutionContract`,
  `CommandProcessor`, `CommandRegistry`, voice one-shot Vosk recognition,
  microphone modes, audio lifecycle, provider router, `SecureProviderRuntime`,
  Desktop Shell ViewModel/Tk wrapper, language/profile settings, Vosk language
  metadata, provider language policy, and existing unit/integration tests.

## Architecture

The new runtime flow is:

```text
Desktop Shell / caller
    -> JarvisAppService.process_one_shot_voice_request()
    -> OneShotVoskRealRecognition.run_once(explicit_one_shot_requested=True)
    -> JarvisAppService.execute_contract(recognized_text, source)
    -> JarvisAppService.execute_command()
    -> CommandProcessor
    -> local command or existing AI/provider abstraction
    -> AppVoiceRequestResult
```

The voice path does not call command handlers, providers, credential storage,
or Desktop Shell widgets directly.

Language architecture:

```text
ApplicationLanguageManager default ru-RU
    -> command/dialogue/intent language default ru
    -> Vosk speech-recognition language default ru
    -> UI and assistant-response language default ru
    -> provider language policy preserves Russian by default
```

This is only a future extension point. TASK-078 does not implement full
multilingual support.

## Implementation Decisions

- Added `AppVoiceRequestResult` as a small composed DTO around the existing
  `AppExecutionContract`.
- Added `JarvisAppService.process_one_shot_voice_request()` and text helper.
- Added a nonblocking lock to reject overlapping one-shot voice requests.
- Reused `AudioLifecycleController` metadata start/reset around the request.
- Reused `OneShotVoskRealRecognition` as the local recognition boundary.
- Delegated recognized text to `execute_contract()` instead of duplicating text
  processing.
- Added a minimal Desktop Shell `Микрофон` button and worker thread.
- Added an application language boundary with `ru-RU` default and kept Vosk
  speech recognition on the existing Russian `ru` model-language default.
- Localized TASK-078 user-facing AppService/Desktop Shell messages to Russian.

## Safety Boundaries

- No continuous listening.
- No wake-word behavior.
- No microphone startup during app startup.
- No automatic dangerous-action confirmation.
- No direct provider calls from the voice orchestration layer.
- No credential reads from the voice layer or Desktop Shell.
- No raw exception objects exposed in the voice DTO.
- Raw English exceptions are normalized behind Russian user-facing messages.
- Overlapping requests are rejected with `overlapping_one_shot_request`.

## Privacy Boundary

- Microphone audio remains local to the existing capture/recognition boundary.
- Raw audio is not serialized in AppService or Desktop Shell results.
- Raw audio is not sent to providers.
- Only recognized text can enter provider-backed behavior, and only through the
  normal typed text path.
- Russian provider-backed questions preserve the original Russian text and use
  fake provider transport in automated tests.
- Contract serialization redacts common API key/token patterns.

## Files Changed

- `app/app_contracts.py`: added `AppVoiceRequestResult`.
- `app/app_service.py`: added one-shot voice orchestration, cleanup, language
  settings exposure, and Russian user-facing voice messages.
- `app/__init__.py`: exported the new contract.
- `app/desktop_shell.py`: added ViewModel voice action, worker-backed button,
  and Russian one-shot voice UI messages.
- `language/language_manager.py`: added the Russian-first application language
  extension point for TASK-078.
- `docs/APPSERVICE_CONTRACTS.md`: documented the new AppService voice contract
  and Russian-first behavior.
- `docs/DESKTOP_APP_SHELL.md`: documented the explicit Desktop Shell voice
  action and Russian-first shell messages.
- `tests/unit/test_app_service.py`: added one-shot AppService unit coverage.
- `tests/unit/test_desktop_shell.py`: added Desktop Shell ViewModel voice tests.
- `tests/unit/test_language_manager.py`: added Russian-first language boundary
  tests.
- `tests/integration/test_task_078_one_shot_voice_to_answer.py`: added vertical
  Russian local command, fake-provider, dry-run, and confirmation-required
  cases.

## Tests Added

- Successful one-shot recognition forwarded to the text execution contract.
- Empty recognition does not invoke text processing.
- Vosk/runtime blocked result does not invoke text processing.
- Text-processing failure is serialized and redacted.
- Cleanup after success/failure and repeated calls after failure.
- Overlapping request rejection.
- Desktop Shell ViewModel voice formatting and redaction.
- Russian default locale and Vosk language defaults.
- Russian user-facing microphone/Vosk failure messages from AppService.
- Cyrillic serialization and preservation without translation/transliteration.
- Vertical Russian local command through real AppService and CommandProcessor.
- Vertical Russian provider-backed question through fake provider transport.
- Vertical Russian dry-run provider path preserving Cyrillic.
- Vertical Russian confirmation-required command without automatic execution.

## Verification Performed

See the final TASK-078 report for exact command outputs from targeted tests,
full pytest, strict deprecation-warning pytest, health check, `git diff --check`,
and git status.

## Known Limitations

- Automated tests use deterministic recognition fakes and do not require a
  physical microphone, production Vosk model, internet, or real credentials.
- Manual microphone smoke cannot be claimed unless run in an environment with
  a working microphone, Vosk package, and configured local model.
- The older CLI real-recognition command remains a recognition-focused command;
  TASK-078 adds the AppService/Desktop one-shot voice-to-answer path.
- Full multilingual support is not implemented. Future user-selected language
  handling should extend the application language boundary.

## Manual Smoke Procedure

1. Confirm Vosk package, local model path, and microphone are configured.
2. Run `python run_desktop.py`.
3. Press `Микрофон`.
4. Say a read-only command such as `статус app service`.
5. Verify the shell displays recognized text and the AppService command result.
6. Repeat with `спроси ai: привет` and verify dry-run provider output.
7. Repeat with a risky command and verify confirmation-required behavior rather
   than automatic dangerous execution.
