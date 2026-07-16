# TASK-079 — Safe Russian Voice Normalization

## Summary

TASK-079 adds a small deterministic normalization boundary for the TASK-078
one-shot voice-to-answer path.

The primary supported Vosk recognition repair is:

```text
статус система -> статус системы
```

## Boundary

The normalizer lives in `voice/russian_voice_normalizer.py` and returns a typed
serializable `RussianVoiceNormalizationResult` with:

- `original_text`
- `normalized_text`
- `changed`
- `applied_rules`
- `safe_to_use_as_command_candidate`

It does not execute commands, call `CommandProcessor`, call `ActionRouter`,
read credentials, call providers, open the network, use LLMs, use embeddings,
or use fuzzy matching.

## AppService Integration

`JarvisAppService.process_one_shot_voice_request()` now runs:

```text
recognized text
-> preserve original recognized text
-> conservative Russian normalization
-> use normalized text only when marked safe
-> execute_contract() exactly once
-> existing CommandProcessor and safety rules
```

The original recognized text remains available as `recognized_text`.
`AppVoiceRequestResult` also reports `normalized_text`,
`normalization_applied`, and `normalization_rules`.

## Safe Scope

Only conservative Russian one-shot voice command forms for the local system
status command are repaired. Examples:

- `статус системы`
- `статус система`
- `статус систем`
- `СТАТУС СИСТЕМА`
- `джарвис статус система`
- `джарвис, статус системы`
- `пожалуйста статус система`

Natural-language questions, risky misspellings, file paths, URLs, email
addresses, quoted content, provider prompts, and typed commands are not
rewritten.

Unsupported future locales return text unchanged.

## Verification

Automated tests cover the pure normalizer, AppService one-shot integration,
Desktop Shell display, typed-command compatibility, provider non-use, and
risky misspelling non-repair.
