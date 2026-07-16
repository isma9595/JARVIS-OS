# TASK-080 Hybrid Intent Resolver and Clarification

Implemented a typed deterministic resolver at the AppService boundary.

Resolution order:

1. Exact command or registered alias from `CommandRegistry`.
2. Safe source-specific voice normalization already applied by AppService.
3. Small explicit semantic patterns for known read-only status commands.
4. Explicit provider request syntax already present in the command registry.
5. Confirmation and cancellation response words.
6. Ambiguous status request with typed clarification options.
7. Ordinary conversational fallback or safe unsupported result.

Intent categories:

- `local_command`
- `ordinary_conversation`
- `provider_request`
- `confirmation_response`
- `cancellation_response`
- `ambiguous`
- `unsupported`

Confidence policy:

- `high`: exact registry command, registered alias, explicit provider syntax, or unique safe read-only pattern.
- `medium`: ambiguous but bounded request with explicit safe options.
- `low`: ordinary conversation or unsupported input.

Clarification contract:

- Clarification state is local to `JarvisAppService`.
- It is in memory only, single-use, and not persisted.
- It stores only the Russian question and serializable options.
- It is cleared after a selected option, cancellation, or unrelated request.
- Selecting an option routes through the existing AppService execution path.

Safety:

- The resolver does not execute commands.
- The resolver does not call `CommandProcessor`, `ActionRouter`, providers, credentials, microphone, or GUI objects.
- Clarification never counts as dangerous-action confirmation.
- Exact risky commands keep the existing confirmation path.
- Vague or misspelled risky commands are not repaired or executed.
- Provider output is not re-executed as a command.

Voice and typed integration:

- Typed text is not destructively normalized.
- One-shot voice keeps TASK-079 safe Russian normalization first.
- Voice and typed text enter the same AppService resolver boundary.
- Desktop Shell still depends only on AppService and structured DTOs.

Known limitations:

- No fuzzy matching, embeddings, LLM classification, external NLP, or morphology.
- Clarification currently covers only bounded status ambiguity.
- Microphone status is resolved to the existing `CommandProcessor` command text because it is not yet in `CommandRegistry`.

Manual smoke steps:

```powershell
python -m pytest tests/unit/test_hybrid_intent_resolver.py tests/integration/test_task_080_hybrid_intent_resolver.py tests/unit/test_desktop_shell.py
python -m pytest
python -W error::DeprecationWarning -m pytest
powershell -ExecutionPolicy Bypass -File scripts\health_check.ps1
```
