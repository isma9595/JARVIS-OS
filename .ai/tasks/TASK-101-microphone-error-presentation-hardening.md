# TASK-101 - Microphone Error Presentation Hardening

Status: implemented, uncommitted

## Audit Scope

TASK-101 addresses AUD-016 only: microphone permission/device failures could expose low-level PortAudio/MME details in user-facing one-shot microphone/Vosk error text.

Audit severity: LOW. Confidence: High.

AUD-013 and TASK-100 local TTS behavior were not changed.

## Root Cause

`voice/one_shot_vosk_real_recognition.py` converted capture, runtime, and recognition exceptions into user-facing `reasons` using raw exception text. `OneShotVoskRealRecognition.format_result()` then rendered those reasons directly.

`app/app_service.py` also appended raw top-level one-shot recognizer exception text into `AppVoiceRequestResult.user_message`.

## Affected Workflows

- Desktop one-shot voice request through `JarvisAppService.process_one_shot_voice_request()`.
- Text one-shot Vosk commands, including `реальное распознавание vosk` and `проверить голос через vosk`, through `CommandProcessor` intent `speech.backend.vosk.one_shot_real_recognition`.

## Correction Boundary

- Added safe one-shot microphone/Vosk presentation messages.
- Sanitized capture, runtime, and recognizer exception reasons before user-facing formatting.
- Hardened `format_result()` so raw injected/future result reasons are sanitized before display.
- Sanitized AppService top-level one-shot recognizer exceptions before populating `AppVoiceRequestResult.user_message`.

No DTO fields, command ids, aliases, registry metadata, policy definitions, planner behavior, memory behavior, microphone lifecycle behavior, local TTS behavior, configuration, or dependencies were changed.

## Safe User Messages

User-facing microphone failures now use concise Russian guidance:

- Не удалось получить доступ к микрофону.
- Проверьте разрешение на использование микрофона в настройках Windows.
- Убедитесь, что устройство ввода подключено и не используется другим приложением.
- После исправления повторите голосовую команду.

Raw `str(exc)`, `repr(exc)`, tracebacks, paths, PortAudio codes, MME codes, backend names, and device details are not exposed through one-shot user messages.

## Text Command Behavior

Text one-shot Vosk commands now render sanitized blocked/failure output when a recognizer returns raw microphone hardware text.

Operation-status semantics were intentionally preserved: if the existing text-command path registers and completes a legacy operation for a blocked recognizer result, TASK-101 does not reclassify that operation. That broader metadata question is outside AUD-016.

## Privacy Guarantees

- `OneShotVoskRealRecognitionResult.reasons` produced by the real one-shot path are sanitized.
- `OneShotVoskRealRecognition.format_result()` sanitizes display reasons defensively.
- `AppVoiceRequestResult.user_message` and `safe_text_ru()` do not include raw microphone, PortAudio, MME, local-path, backend, or exception details.
- Desktop-rendered one-shot output does not include raw microphone details.
- No raw microphone details enter execution journal metadata in the covered text one-shot path.
- Tests use fakes only and do not access real microphone, audio hardware, providers, or network.

## Changed Files

- `.ai/tasks/TASK-101-microphone-error-presentation-hardening.md`
- `app/app_service.py`
- `docs/architecture/STATE_CHANGING_COMMAND_METADATA.md`
- `docs/testing/TASK_091_CONTRACT_CHARACTERIZATION.md`
- `tests/unit/test_app_service.py`
- `tests/unit/test_desktop_shell.py`
- `tests/unit/test_one_shot_vosk_real_recognition.py`
- `voice/one_shot_vosk_real_recognition.py`

## Tests Added Or Updated

- `tests/unit/test_one_shot_vosk_real_recognition.py`
  - capture exception with `PaErrorCode -9999; MME error 1` is sanitized in reasons and formatted output;
  - recognizer exception with backend/path detail is sanitized.
- `tests/unit/test_app_service.py`
  - blocked one-shot reasons are sanitized in `user_message` and `safe_text_ru()`;
  - top-level recognizer exceptions are sanitized;
  - text one-shot Vosk command output and journal metadata do not expose raw hardware details.
- `tests/unit/test_desktop_shell.py`
  - Desktop one-shot voice failure rendering shows safe microphone guidance and no raw PortAudio/MME text.

## Non-Goals

- No AUD-013 or local TTS changes.
- No microphone device selector.
- No retry framework.
- No hot-plug or reconnect redesign.
- No continuous/partial listening redesign.
- No wake word.
- No new recognition engine.
- No new dependencies.
- No provider/network integration.
- No DTO schema changes.
- No grammar, alias, registry, policy, planner, memory, or local TTS changes.
- No platform adapter rewrite.

## Preserved Invariants

- TASK-095 matcher/import-isolation invariants preserved.
- TASK-096 real confirmation and operation semantics preserved.
- TASK-097 memory Preview/Execute recognition parity preserved.
- TASK-098 recall-only Russian alias behavior preserved.
- TASK-099 Russian planner forget-all classification and confirmation safety preserved.
- TASK-100 local TTS execution metadata consistency preserved.
- Preview remains side-effect free.
- Automated tests do not use real microphone/audio hardware.

## Verification

- `python -m pytest -q tests/unit/test_one_shot_vosk_real_recognition.py`: 24 passed.
- `python -m pytest -q tests/unit/test_app_service.py tests/unit/test_desktop_shell.py`: 121 passed.
- `python -m pytest -q tests/unit/test_one_shot_microphone_capture.py tests/unit/test_microphone_input_adapter.py tests/unit/test_voice_input_manager.py tests/unit/test_vosk_local_recognition_gate.py tests/unit/test_vosk_model_readiness_verifier.py`: 94 passed.
- `python -m pytest -q tests/integration/test_task_078_one_shot_voice_to_answer.py tests/characterization/test_preview_execute_contracts.py tests/characterization/test_local_tts_contracts.py`: 10 passed.
- `python -m pytest -q tests/unit/test_execution_coordinator.py tests/unit/test_execution_journal.py tests/unit/test_policy_decision_boundary.py`: 17 passed.
- TASK-095 invariant tests: 3 passed.
- `python -m pytest -q`: 1700 passed, 2 skipped.
- `python -W error::DeprecationWarning -m pytest -q`: 1700 passed, 2 skipped.
- `powershell -ExecutionPolicy Bypass -File scripts/health_check.ps1`: SUCCESS, 1700 passed, 2 skipped.
- `powershell -ExecutionPolicy Bypass -File scripts/assistant_smoke.ps1`: JARVIS ASSISTANT SMOKE: SUCCESS.
- Import probes:
  - COMMAND RESOLUTION SERVICE IMPORT: SUCCESS.
  - COMMAND PROCESSOR LOADED: False.
  - APP SERVICE IMPORT: SUCCESS.
  - DESKTOP SHELL IMPORT: SUCCESS.
- Changed Python files compiled successfully with `PYTHONDONTWRITEBYTECODE=1`.

Commit: unchecked.
Push: unchecked.
