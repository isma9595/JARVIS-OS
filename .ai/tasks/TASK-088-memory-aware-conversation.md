# TASK-088 Memory-Aware Conversation

## Summary

TASK-088 adds one safe memory-aware AppService boundary with two separate memory layers:

- Session conversation context: bounded, in-memory recent safe turn summaries only.
- Explicit persistent user memory: local facts written only after deterministic remember commands.

Desktop Shell and future clients continue to use AppService only.

## Explicit-Memory-Only Rule

Ordinary conversation is not automatically persisted. Provider output is not allowed to write memory, execute commands, or become a command through memory.

## Supported Commands

Russian:

- `запомни, что мой любимый цвет — зелёный`
- `запомни: любимый цвет = зелёный`
- `запомни мой город: Грозный`
- `сохрани в памяти, что тестовое слово — север`
- `какой мой любимый цвет`
- `что ты помнишь о моём любимом цвете`
- `что ты запомнил про тестовое слово`
- `покажи, что ты помнишь обо мне`
- `забудь мой любимый цвет`
- `удали из памяти тестовое слово`
- `забудь всё, что ты помнишь обо мне`

English:

- `remember that my favorite color is green`
- `remember: favorite color = green`
- `what is my favorite color`
- `what do you remember about my favorite color`
- `forget my favorite color`
- `delete test word from memory`
- `forget everything you remember about me`

Vague commands such as `запомни это`, `помни`, `забудь это`, `удали память`, `remember this`, and `forget it` request clarification.

## Normalization And Limits

Memory keys are trimmed, whitespace-collapsed, case-insensitive, and matched deterministically. Common equivalents such as `мой любимый цвет`, `любимый цвет`, and `Favorite Color` map to one normalized key. Empty keys, empty values, oversized keys or values, control characters, multiline values, and credential-like values are rejected.

## Persistence

Persistent user facts use `LocalMemoryManager`. No memory file is created at AppService startup or manager construction. Missing storage behaves as empty memory. Writes are atomic through a temporary file replacement. Corrupt storage returns empty memory safely and redacts raw exceptions.

Legacy note-style memory remains readable through existing `LocalMemoryManager` methods. TASK-088 facts use the existing storage file with `type = persistent_user_fact`; no second JSON database is introduced.

## Recall And Unknown Facts

Known facts are answered as remembered information. Unknown facts clearly say they are not remembered. Missing personal facts are never inferred or fabricated.

## Deletion

Deleting one named memory key is local to explicit user memory. Delete-all affects only explicit persistent user facts and requires scoped confirmation. Cancellation preserves memory. Duplicate confirmation does not delete twice.

## Language Behavior

Russian remains the default. After switching to English, memory command responses are English. Stored values are preserved as written and are not rewritten when the language changes.

## Privacy Boundary

Credential-like values are rejected and not printed back. Memory is not sent to providers automatically. Provider context may receive memory only through the existing context privacy policy on an explicit provider request; no provider memory injection is implemented in TASK-088.

## Startup And Lazy Initialization

Memory-aware conversation does not initialize providers, credentials, network, microphone, Vosk, or TTS. AppService startup does not create or rewrite memory storage. Optional heavy components remain deferred.

## Manual Smoke Steps

1. Start with isolated memory storage.
2. Confirm `JarvisAppService()` starts with Russian default and no memory file created.
3. Run `запомни: smoke task088 = isolated`.
4. Run `что ты помнишь о smoke task088`.
5. Run `забудь smoke task088`.
6. Confirm the isolated memory list is empty before test completion.
7. Confirm no provider, network, credential, microphone, Vosk, TTS, or arbitrary filesystem boundary was used.

## Verification Order

Run:

```powershell
python -m pytest tests/unit/test_memory_aware_conversation.py -v
python -m pytest tests/integration/test_task_088_memory_aware_conversation.py -v
python -m pytest tests/unit/test_memory_manager.py -v
powershell -ExecutionPolicy Bypass -File scripts/assistant_smoke.ps1
python -m pytest tests/unit/test_app_service.py tests/unit/test_desktop_shell.py -v
python -m pytest tests/unit/test_user_language_preference.py tests/integration/test_task_086_user_language_preference.py -v
python -m pytest tests/unit/test_lazy_initialization.py tests/integration/test_task_087_startup_lazy_initialization.py -v
python -m pytest
python -m pytest -W error::DeprecationWarning
powershell -ExecutionPolicy Bypass -File scripts/health_check.ps1
git diff --check
git status --short
git diff --stat
git diff --name-only
```

## Known Limitations

TASK-088 does not implement vector search, embeddings, semantic similarity, automatic fact extraction, cloud memory, memory sync, provider summarization, autonomous learning, full coreference resolution, replay of arbitrary prior commands, or a general planner.
