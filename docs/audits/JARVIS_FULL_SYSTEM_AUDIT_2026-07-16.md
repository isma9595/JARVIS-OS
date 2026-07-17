# JARVIS OS Full System Audit

## 1. Executive Summary

TASK-090 audited the repository at `main` / `9f2080a Add general multi-step planner` without changing production code, tests, or configuration.

Verdict: HEALTHY WITH REMEDIATION REQUIRED.

This HEALTHY WITH REMEDIATION REQUIRED verdict applies to the repository state,
automated safety boundaries, tested application contracts, clean-export
verification, and the completed 2026-07-17 manual runtime audit. No critical or
high-severity safety failure was found. The remediation requirement is caused by
multiple important MEDIUM contract, metadata, Preview parity, planner-language,
and command-classification inconsistencies. This verdict is not production
certification and does not mean feature completeness.

No critical or high findings were confirmed. The system passed full pytest, strict DeprecationWarning pytest, assistant smoke, health check, focused critical suites, clean-export verification, safe startup, destructive confirmation/cancellation, document write isolation, real microphone/Vosk, local TTS, and hardware denial recovery after rerunning pytest/health with normal temp-directory access because the Codex sandbox blocked pytest's default temp cleanup path.

Confirmed work is bounded to maintainability, documentation, tooling, command-contract parity, metadata consistency, planner-language coverage, and Desktop Shell result usability:

- large orchestration classes remain a development-risk hotspot;
- `PlanExecutor` depends on planner private state for snapshot reconstruction;
- AppService architecture documentation is stale;
- root onboarding documentation is missing;
- coverage tooling is unavailable;
- four tracked files have mixed line endings;
- Preview/Execute, risk, operation, and confirmation metadata are inconsistent across equivalent routes;
- Russian memory/planner command grammar is linguistically brittle;
- local voice/TTS user-facing metadata and error presentation need correction;
- Desktop Shell result panes need clearer action identity and copy/export controls.

## 2. Final Verdict

HEALTHY WITH REMEDIATION REQUIRED

Rationale: zero confirmed CRITICAL findings, zero confirmed HIGH findings, all required automated verification passed under normal temp access, and the completed 2026-07-17 manual runtime audit passed the safety and reliability scenarios for safe startup, destructive confirmation/cancellation, document write isolation, real microphone/Vosk, local TTS, and microphone denial/recovery.

Scope qualification: HEALTHY WITH REMEDIATION REQUIRED applies to repository integrity, automated safety boundaries, tested AppService/Desktop/planner/workflow/provider contracts, clean-export portability, and the manual runtime checks recorded in this report. No external provider request was made. The remediation requirement is caused by multiple important MEDIUM contract, metadata, Preview parity, planner-language, and command-classification inconsistencies. The verdict is not a feature-completeness claim or production certification.

## 3. Audit Scope

Audited areas:

- Git/repository integrity;
- task traceability for all `.ai/tasks/TASK-*.md`;
- Desktop Shell, AppService, contracts, CommandProcessor, registry, resolver, policy, execution coordinator/journal;
- workflows, document review, platform adapter, multi-step planner;
- memory, language preference, user profile, provider runtime, secure key storage;
- voice/audio lifecycle, one-shot Vosk path, TTS boundary;
- tests, clean export, startup, portability, code quality, and documentation.

Out of scope by safety rule:

- no production remediation;
- no real provider/network call;
- no credential value reads or prints.

Manual runtime audit exception:

- authorized manual runtime verification on 2026-07-17 covered status and language, memory, read-only planner execution, destructive forget-all confirmation and cancellation, temporary local TXT document workflow, real microphone and Vosk recognition, audible local Windows TTS, microphone-permission denial and recovery, and safe Desktop Shell restart behavior as explicitly supplied manual evidence for TASK-090.

## 4. Baseline and Environment

- Repository: `C:\JARVIS-OS`
- Branch: `main`
- HEAD: `9f2080a Add general multi-step planner`
- Initial working tree: clean
- Platform target: Windows 11
- Python observed in command paths: Python 3.14 runtime
- Default language requirement: Russian
- Additional supported language: English
- Audit temp directory: `C:\Users\User\AppData\Local\Temp\jarvis-task090-audit`

## 5. Evidence Collected

Required baseline commands:

- `git status`: branch `main`, up to date with `origin/main`, clean.
- `git branch --show-current`: `main`.
- `git log -1 --oneline`: `9f2080a Add general multi-step planner`.

Repository commands:

- `git log --oneline --decorate -30`
- `git tag --list`
- `git fsck --full`
- `git ls-files`
- `git status --ignored --short`
- `git diff --check`
- `git count-objects -vH`

Verification commands:

- `python -m pytest --collect-only -q`: collected 1542 tests.
- `powershell -ExecutionPolicy Bypass -File scripts\assistant_smoke.ps1`: SUCCESS.
- `python -m pytest`: `1540 passed, 2 skipped in 4.98s` after sandbox-related rerun.
- `python -W error::DeprecationWarning -m pytest`: `1540 passed, 2 skipped in 4.97s`.
- Focused critical suites: `199 passed in 2.10s`.
- `powershell -ExecutionPolicy Bypass -File scripts\health_check.ps1`: SUCCESS after sandbox-related rerun.
- `python -m coverage --version`: coverage unavailable, not installed.
- Clean export: smoke, pytest, strict pytest, and health check all passed.

Previous post-edit sequential verification:

- `python -m pytest -q`: `1540 passed, 2 skipped in 4.83s`.
- `python -W error::DeprecationWarning -m pytest -q`: `1540 passed, 2 skipped in 4.92s`.
- `health_check`: SUCCESS.
- `assistant_smoke`: JARVIS ASSISTANT SMOKE: SUCCESS.

Final correction-pass sequential verification:

- `python -m pytest -q`: `1540 passed, 2 skipped in 4.86s`.
- `python -W error::DeprecationWarning -m pytest -q`: `1540 passed, 2 skipped in 4.85s`.
- `health_check`: SUCCESS after rerun outside the sandbox because of sandbox temporary-directory permission restrictions.
- `assistant_smoke`: JARVIS ASSISTANT SMOKE: SUCCESS.

The first attempted normal pytest rerun was accidentally launched concurrently with strict pytest and encountered a Windows file-lock race involving `workspace/assistant_smoke_task088_memory.json`. The suites were then rerun sequentially and both passed cleanly. The concurrent file-lock event is not treated as a product test failure.
- `python -m pip check`: `No broken requirements found.`

Manual runtime evidence supplied for 2026-07-17:

- Desktop Shell startup was safe: no automatic microphone, TTS, provider call, old plan, confirmation, or document workflow resume.
- `system.status`, `language.get`, running-session language change, restart behavior, memory preview/remember/recall/persistence/delete, destructive planner confirmation/cancellation, read-only planner completion, TXT document review, real one-shot microphone/Vosk, local audible TTS, and microphone denial/recovery all passed the safety scenarios described in section 23.
- Document workflow hash evidence: source SHA256 before and after `1A117FC78F228538479ABE6A771C7DDDF5CE8C37EB996CDD9CDD06BEEE71F034`; output SHA256 `213BB1DD0559EB47AA36AD1BDFD31AFB88D5EBB4C94A06C5A7926270AE3FCBDA`; repeated confirmation left output unchanged.
- Destructive planner evidence: exact English command `create plan: forget everything you remember about me` selected the real forget-all capability, `execute plan` assigned a non-empty operation ID, paused at `awaiting_confirmation`, and cancellation preserved the test memory marker.

## 6. Repository Integrity

Integrity verdict: healthy.

Evidence:

- Initial status was clean.
- `git fsck --full` reported only `dangling tree 4b825dc642cb6eb9a060e54bf8d69288fbee4904`; no corruption, missing objects, or broken refs were reported.
- `git diff --check` produced no whitespace errors.
- `git count-objects -vH`: 564 loose objects, 2.07 MiB loose size, 1450 packed objects, 714.91 KiB pack size, zero garbage.
- Tags: no release tags were present locally.
- Tracked file count: 505.
- Tracked Python file count: 235.
- No case-insensitive tracked path collisions found.
- No Windows reserved tracked filenames found.
- No tracked files over 512 KiB found.

Ignored/generated local state observed:

- `.pytest_cache/`, `__pycache__/`, local profile/memory/settings files, and local Vosk model files are ignored.
- Ignored local Vosk assets are portability dependencies for real hardware/manual speech tests, not clean-export dependencies.

Portability risks:

- Mixed line endings in `.gitignore`, `core/base_module.py`, `core/event_bus.py`, and `core/module_manager.py`.
- Clean export passed without ignored models, profiles, memories, keys, or local settings.

## 7. Architecture Map

Current dependency direction observed:

Desktop Shell -> JarvisAppService -> stable DTOs/application services -> subsystem boundaries.

Primary entry points:

- `run.py`: CLI/runtime entry.
- `run_desktop.py`: desktop shell launcher.
- `app/desktop_shell.py`: Tkinter shell; uses `JarvisAppService`.

Core map:

- `app/app_service.py`: app boundary, preview/execution contracts, language, memory, document workflow, planner, voice, provider runtime lazy access.
- `app/app_contracts.py`: DTO contracts.
- `core/command_processor.py`: legacy text command orchestrator.
- `core/command_registry.py`: capability metadata.
- `app/intent_resolver.py`: hybrid intent and clarification.
- `core/policy_boundary.py`: deterministic policy decisions.
- `core/execution_coordinator.py` and `core/execution_journal.py`: operation state, idempotency, cancellation, safe metadata.
- `workflows/runner.py`: reusable linear workflow runner.
- `workflows/document_review.py`: local TXT document workflow.
- `platform_adapters/local_filesystem.py`: local filesystem port implementation.
- `planner/`: bounded deterministic multi-step planner.
- `memory/`: local memory and session conversation context.
- `language/`: ru/en preference.
- `ai/`: provider contracts, router, gates, secure runtime, adapters.
- `voice/`: lifecycle, one-shot capture/recognition, normalization, output safety.
- `security/`: secure key storage and API-key manager.

## 8. Dependency and Boundary Review

Verified boundary behavior:

- Desktop shell imports `JarvisAppService` and does not import `ActionRouter`, provider adapters, memory storage, or filesystem adapter directly.
- AppService preview uses metadata and does not execute commands.
- AppService owns planner and document workflow orchestration; side effects still pass through policy/execution boundaries.
- `PolicyDecisionBoundary` is metadata-only and does not call providers, ActionRouter, audio, GUI, or credential stores.
- `WorkflowRunner` evaluates policy before each step and pauses before confirmation-required side effects.
- `PlannerCapabilityRegistry` requires explicit registered capabilities; arbitrary AppService reflection was not found.

Boundary concerns:

- `CommandProcessor` remains a very large legacy orchestrator.
- `JarvisAppService` has accumulated many responsibilities.
- `PlanExecutor` imports private `_PlanState` from `planner.multi_step_planner`.

Published AST/import evidence:

- Import-cycle analysis reported candidate cycles centered on `ai/__init__.py`, `ai/providers/__init__.py`, request gates, `ai/provider_router.py`, and provider adapter modules. These are package re-export/provider-router cycles, not a confirmed runtime failure in the tested suite.
- Highest direct import counts: `app/app_service.py` 76, `tests/unit/test_command_processor.py` 74, `ai/__init__.py` 73, `core/command_processor.py` 59, `voice/__init__.py` 55.
- Modules with the most unique direct local dependencies: `core/command_processor.py` 28, `ai/__init__.py` 28, `voice/__init__.py` 24, `app/app_service.py` 22, `core/kernel.py` 10.
- Largest functions by logical line count: `core/command_processor.py:1677 process` 1381, `core/command_processor.py:1408 __init__` 252, `tests/smoke/test_assistant_smoke.py:148 test_assistant_smoke_appservice_safe_path` 215, `core/command_registry.py:371 default_command_metadata` 197, `app/desktop_shell.py:363 _build` 172.
- Recent Git change-concentration hotspots: `core/command_processor.py` touched in 47 recent commits, `.ai/CHECKPOINT.md` 45, `tests/unit/test_command_processor.py` 42, `voice/voice_command_allowlist.py` 33, `tests/unit/test_voice_command_allowlist.py` 30, `app/app_service.py` 19.
- Global mutable state review found module-level export lists, constant lookup dictionaries/sets, and terminal-status sets. No confirmed unbounded mutable singleton state was identified as a defect; runtime mutable state is primarily instance-owned.
- Service-locator-like behavior review found `JarvisAppService` and `CommandProcessor` acting as composition/orchestration roots by constructing or holding subsystem managers. This supports AUD-001 as a maintainability concern, but no unsupported behavior defect was confirmed.

Size, import count, and change frequency are supporting maintainability evidence only. They are not findings by themselves.

## 9. Security and Safety Review

Static safety scan:

- No `eval(`, `exec(`, `os.system`, unsafe `pickle`, or `yaml.load` use found in tracked Python.
- One `shell=True` match was in test context, not production execution.
- `subprocess` use is limited to scripts/tests/tooling; no provider-output-to-shell path was confirmed.
- `urllib`/`socket` are present in provider adapters and Ollama runtime, controlled by explicit provider/request gates or localhost runtime paths.
- `ActionRouter` usage from UI/AppService was not confirmed; `CommandProcessor` owns legacy router delegation.

Secret scan:

- Tracked source and Git history scans were run with redacted reporting only.
- Matches were dominated by tests, docs, placeholder values, redaction patterns, and long mojibake/identifier strings.
- No plausible real credential exposure was confirmed.
- No secret values were printed into this report.

Provider-output execution:

- Provider responses are returned as text DTOs/results.
- AppService result fields include `response_executed_as_command=False`.
- Planner capability outputs are safe messages and are not re-parsed into new steps.

Confirmation/idempotency:

- `ExecutionCoordinator` tracks idempotency keys and conflicts.
- `WorkflowRunner` pauses before confirmation-required side effects.
- Memory delete-all has scoped pending confirmation state.
- Tests cover duplicate confirmation and cancellation paths.

## 10. Data, Persistence and Privacy

Persistence review:

| Format | Persisted or Session-Only | Path Ownership | Schema/Version | Validation | Atomic Write Behavior | Corruption Handling | Migration Support | Locking/Concurrency | Backup/Recovery Expectation | Audit Conclusion |
|---|---|---|---|---|---|---|---|---|---|---|
| User profile | Persisted JSON | `users/profiles/default_user.json` by default; local ignored user state | No explicit schema/version; fields include names, language, timestamps | Assistant name and language setters validate bounded inputs; load is raw JSON | Temp file plus `os.replace` | No explicit corrupt-profile recovery in `load_profile`; invalid JSON would raise | None confirmed | No file lock; single-process expectation | User/local backup only | No confirmed defect in tested paths; future schema migration risk |
| Memory | Persisted JSON | `memory/local/memory.json` by default; local ignored memory state | `version: 0.1` plus `items` | Rejects empty/control/multiline/credential-like explicit facts; normalizes keys | Temp file plus `Path.replace` | Unreadable/invalid storage returns empty memory and sets safe error code | Version field exists; no migration path confirmed | No file lock; single-process limitation | User/local backup only; no automatic backup | Safe for current single-process use; concurrency and migration are future risks |
| Vosk settings | Persisted JSON | `config/local/vosk_settings.json`; local ignored configuration | No explicit schema/version | Normalizes optional `model_path` and `language`; ignores non-dict/invalid values | Direct write to target file, no temp replacement | Missing, invalid JSON, Unicode, or OS read errors return `{}` | None confirmed | No file lock; single-process expectation | User can reconfigure model path | Direct-write behavior is a confirmed limitation, not a runtime safety defect |
| Secure key storage metadata | Persisted when DPAPI backend is available; otherwise unavailable/session test backend only | `%APPDATA%/JARVIS-OS/secure_keys.json` for Windows DPAPI | `version: 1`, backend name, entries | Provider/secret names normalized; secret values required; public records expose masked hints only | Temp file plus `os.replace` | Invalid encrypted payload/read errors are not silently migrated; unavailable backend refuses plaintext persistence | None confirmed | No file lock; single-process expectation | User/OS profile backup; DPAPI user binding applies | Encrypted-at-rest design verified by tests; concurrency/migration not deeply covered |
| Execution journal | Session-only | Instance-owned `ExecutionJournal` | Typed dataclass snapshots | Safe text/metadata redaction and blocked keys | Not persisted | Process restart clears journal | Not applicable | Uses `RLock`; bounded in-process journal | No recovery expected | Intentional volatile audit trail for current AppService operations |
| Planner state | Session-only | Instance-owned `MultiStepPlanner` | Typed `PlanSnapshot`; no durable schema | Bounded step count, text length, credential/control-character rejection | Not persisted | Process restart clears active plan | Not applicable | No cross-process lock; single AppService session | No recovery expected | Intentional session-only behavior; AUD-002 covers private snapshot coupling |
| Conversation context | Session-only | Instance-owned `SessionConversationContext` | Typed bounded turn snapshots | Redacts credential-like values and truncates summaries | Not persisted | Process restart clears context | Not applicable | No cross-process lock; bounded deque | No recovery expected | Intentional volatile conversation summary |
| Provider session state | Session-only | Instance-owned `AIProviderSessionState` | Typed `AIProviderSessionSnapshot` | Normalizes provider/model metadata; stores no prompts, responses, keys, tokens, memory, files, or logs | Not persisted | Process restart clears provider selection/last-success metadata | Not applicable | No cross-process lock; current-process state only | No recovery expected | Intentional volatile provider metadata |

Confirmed safe behaviors:

- Startup measurement with isolated managers did not create profile or memory files.
- Planner startup created no active plan.
- Explicit memory validation rejects credential-like values.
- Journal metadata uses safe text/metadata helpers.
- Document workflow does not overwrite source and writes only a new sibling output after confirmation.

Limitations:

- Memory JSON writes are safe for current single-process use but do not implement file locking.
- Migration coverage is basic; future schema changes should include migration tests.
- Some raw absolute paths are necessarily exposed in local document workflow results; user-facing display should continue to prefer filenames where possible.

## 11. Provider and Network Boundaries

Network-capable locations:

- `ai/providers/openai_provider.py`: HTTPS Responses API via `urllib`, gated by `allow_network` and API key.
- `ai/providers/gemini_provider.py`: Gemini HTTP client path, gated by request gate.
- `ai/providers/groq_provider.py`: Groq HTTPS via `urllib`, gated by request gate and `allow_network`.
- `ai/providers/gigachat_provider.py`: GigaChat HTTP/token paths, gated by request gate.
- `ai/providers/ollama_provider.py` and `ai/ollama_runtime.py`: localhost Ollama only.
- Provider request gates: `*_request_gate.py`.
- Provider fallback/consensus/live verification helpers: explicit-only command paths.

Verified without network:

- AppService startup did not initialize provider runtime factory in isolated startup measurement.
- Preview/status/language/memory/planner creation did not require provider calls.
- Provider adapters default to no network unless explicit gate builds an allowed provider.
- Provider failures are typed text responses; Groq/GigaChat sanitize error bodies and bearer/token-like fragments.
- API keys do not appear in public DTOs or reports.

## 12. Voice and Audio

Voice/audio map:

- `voice/audio_lifecycle.py`: metadata lifecycle.
- `voice/one_shot_microphone_capture.py`: explicit one-shot capture adapter.
- `voice/one_shot_vosk_real_recognition.py`: explicit local Vosk recognition path.
- `voice/russian_voice_normalizer.py`: conservative normalization.
- `voice/voice_command_allowlist.py`: safe voice command allowlist.
- `voice/voice_output_safety.py`: TTS safety/mute/redaction.
- `voice/windows_local_tts_backend.py`: Windows TTS backend.

Verified without real devices:

- AppService startup did not call the injected one-shot voice factory.
- Audio lifecycle status is metadata-only.
- Vosk model loading is behind explicit one-shot recognition path.
- Tests cover unavailable dependencies, dry-run recognition, one-shot recognized text routing through the normal AppService execution path, normalization safety, allowlist, confirmation, output safety, and TTS backend behavior without opening real hardware.

Manual hardware evidence completed on 2026-07-17:

- Real microphone and Vosk recognition worked; "статус система" normalized to "статус системы"; "текущий язык" returned Russian `ru-RU`; multiple consecutive captures worked.
- Recognized text was processed through normal AppService, raw audio was not sent externally, responses were not executed as commands, and no secrets were exposed.
- `windows_local_tts` was available; audible local speech was heard; cloud was not used; audio files were not saved; Desktop Shell stayed responsive.
- With Windows desktop-app microphone access disabled, One-Shot Voice returned `voice_recognition_blocked` / `recognition_blocked`; capture, recognition, and text processing did not run; no accidental command executed; Desktop Shell did not crash or hang. After permission restoration, "статус системы" worked normally again.

## 13. Workflows and Platform Adapters

Workflow runner:

- `WorkflowRunner` is the authoritative reusable linear workflow lifecycle.
- It enforces unique step IDs, bounded progress, cancellation, terminal status handling, and policy evaluation before steps.

Document workflow:

- Accepts only local absolute `.txt` files.
- Rejects UNC/network paths, symlinks, directories, unsupported extensions, invalid UTF-8, binary files, oversized files, output conflicts, source changes, and same source/output paths.
- Writes new sibling file with `atomic_write_new_file`.
- Verifies written bytes and source hash.

Platform adapter:

- `WindowsLocalFileSystemAdapter` rejects network paths and symlinks.
- Uses exclusive create/link/open behavior to avoid overwrite.
- Cleans temporary file in normal/error paths.

## 14. General Multi-Step Planner

Planner behavior:

- Explicit creation commands only.
- Session-only active plan.
- Maximum 8 steps.
- Deterministic parser.
- Registered capabilities only.
- Plan creation/preview is separate from execution.
- Execution uses `PlanExecutor` over `WorkflowRunner`.
- Policy is re-evaluated per step.
- Confirmation-required steps pause before side effects.
- Failed/denied/cancelled steps stop later steps.

Verified by tests:

- `tests/unit/test_multi_step_planner.py`
- `tests/unit/test_plan_executor.py`
- `tests/integration/test_task_089_general_multi_step_planner.py`

Concern:

- `PlanExecutor` reconstructs snapshots through private `_PlanState`; see AUD-002.

## 15. Startup and Performance

Startup measurement method:

- 25 isolated AppService constructions.
- Isolated temp profile and memory paths.
- Provider and voice factories injected to raise if touched.
- `tracemalloc` used for indicative construction memory.

Results:

- Samples: 25
- Minimum: 0.392 ms
- Median: 0.467 ms
- Maximum: 0.962 ms
- Approximate p95: 0.712 ms
- Peak traced construction allocation: 33,631 bytes
- Active plan on startup: no
- Memory file created on startup: no
- Profile file created on startup: no

Label: environment-specific; not a release gate.

## 16. Automated Test Assessment

Collected tests: 1542.

Full suite:

- `1540 passed, 2 skipped in 4.98s`

Strict DeprecationWarning suite:

- `1540 passed, 2 skipped in 4.97s`

Focused critical suites:

- `199 passed in 2.10s`

Skips:

- `tests/unit/test_document_review_workflow.py`: symlink creation unavailable.
- `tests/unit/test_local_filesystem_adapter.py`: symlink creation unavailable.

Sandbox note:

- Initial non-escalated full pytest and health-check attempts failed because pytest could not access/clean `C:\Users\User\AppData\Local\Temp\pytest-of-User` under Codex sandbox permissions.
- Rerun with normal temp access passed. This is recorded as an audit environment limitation, not a product failure.

Test gaps:

- Real provider request is intentionally excluded from default tests.
- Concurrency/file-locking behavior for JSON persistence is not deeply tested.
- Coverage tooling is unavailable.
- Hardware voice/TTS now has manual evidence, but should be standardized into a reusable manual regression checklist.

## 17. Coverage Assessment

`python -m coverage --version` result:

- `No module named coverage`

Coverage was not installed and was not installed during the audit. No line coverage percentage is claimed.

Manual mapping shows critical modules have direct tests, including policy, execution coordinator/journal, workflow runner, planner, memory-aware conversation, secure key store/runtime, AppService, Desktop Shell, and integrations TASK-081 through TASK-089.

## 18. Clean Export and Portability

Clean export method:

- `git archive HEAD`
- Extracted outside repository under audit temp directory.
- No ignored local models, profiles, memories, keys, or settings copied.

Clean export results:

- Assistant smoke: SUCCESS.
- Full pytest: `1540 passed, 2 skipped in 7.03s`.
- Strict DeprecationWarning pytest: `1540 passed, 2 skipped in 5.27s`.
- Health check: SUCCESS.

Dependency/packaging:

- `python -m pip check`: no broken requirements.
- No `pyproject.toml`, `setup.cfg`, `tox.ini`, `.ruff.toml`, `mypy.ini`, or `pyrightconfig.json` tracked.
- Windows is the current target; PowerShell scripts are part of verification.
- Linux portability blockers include Windows TTS backend, PowerShell verification scripts, and Windows-first filesystem behavior.

## 19. Code Quality and Maintainability

Largest Python files by logical lines:

- `core/command_processor.py`: 5153
- `app/app_service.py`: 3516
- `voice/voice_command_allowlist.py`: 703
- `app/desktop_shell.py`: 689
- `ai/provider_selection_policy.py`: 564

Largest classes by method count:

- `CommandProcessor`: 142 methods
- `JarvisAppService`: 115 methods
- `DialogueManager`: 91 methods

Largest function/class hotspots are not findings by size alone. AUD-001 is based on mixed responsibilities plus size.

Static tooling:

- `ruff`: unavailable
- `mypy`: unavailable
- `pyright`: unavailable
- `bandit`: unavailable
- common config files: not present

Search findings:

- `except Exception` appears in controlled fail-safe paths and tests; no confirmed unsafe swallowing finding.
- Network client imports are localized to provider/runtime modules.
- `ActionRouter` remains in `CommandProcessor` only; no UI/AppService direct call confirmed.

## 20. Documentation Accuracy

Accurate/current:

- Desktop shell launch command: `python run_desktop.py`.
- Provider docs describe explicit request gates and no default network.
- Language docs align with Russian default and English support.
- Memory docs align with explicit remember/recall semantics.
- Planner task record aligns with current TASK-089 behavior.

Stale/incomplete:

- `docs/JARVIS_APP_SERVICE.md` still says AppService has no file/document reading and no disk writes by AppService itself, while current AppService owns document workflow and memory/planner integration.
- `docs/ARCHITECTURE.md` still frames the project as an "operating system" and mentions broad future multi-device/multi-language scope; current constraint is assistant, Windows 11, Russian default plus English only.
- No root README exists for setup/onboarding.

## 21. Findings by Severity

| ID | Severity | Confidence | Subsystem | Finding | Evidence | Impact | Release Blocker | Recommended Remediation | Proposed Task |
|---|---|---|---|---|---|---|---|---|---|
| AUD-001 | MEDIUM | High | Architecture / orchestration | `CommandProcessor` and `JarvisAppService` are mixed-responsibility orchestration hotspots. | `core/command_processor.py:44` has 5153 logical lines and 142 methods; it constructs memory, ActionRouter, provider gates/runtime, and handles memory/provider/status commands. `app/app_service.py:208` has 3516 logical lines and 115 methods; it owns preview/execute, memory, document workflow, planner, language, voice, provider runtime access. | Increases regression risk and slows future safety changes. | No | Characterize existing behavior, then extract bounded services behind existing contracts without changing behavior. | TASK-091, TASK-093, TASK-094 |
| AUD-002 | MEDIUM | High | Planner | `PlanExecutor` depends on private planner state for snapshots. | `planner/plan_executor.py:214` imports `planner.multi_step_planner._PlanState`; lines 216-225 reconstruct state with empty arguments/risk metadata. | Internal coupling can break planner execution snapshots during refactors and blurs ownership of planner state serialization. | No | Add public snapshot builder/update API or shared immutable snapshot factory. | TASK-092 Planner Snapshot Boundary Cleanup |
| AUD-003 | MEDIUM | High | Documentation | AppService documentation is stale against current behavior. | `docs/JARVIS_APP_SERVICE.md` states no file/document reading and no disk writes by AppService; current `app/app_service.py:313` constructs document workflow, `app/app_service.py:1894` executes document review, and `app/app_service.py:3005` handles memory writes. | Misleads future UI/security work about AppService responsibilities. | No | Update AppService docs after approved remediation planning. | TASK-098 Documentation Alignment |
| AUD-004 | MEDIUM | High | Documentation / product scope | Architecture docs overstate OS/multi-language scope. | `docs/ARCHITECTURE.md` title and purpose describe an operating system and broad multi-device/multi-language aspirations; current requirement is assistant, Windows 11, Russian default, English only. | Can steer future tasks toward unsupported architecture decisions. | No | Rewrite architecture overview to current assistant scope and defer OS-like language to future vision only if approved. | TASK-098 Documentation Alignment |
| AUD-008 | MEDIUM | High | Preview / memory commands | Preview and Execute command recognition are inconsistent for supported memory commands. | Manual runtime audit found supported memory remember/recall/forget commands were sometimes unknown in Preview but recognized and executed by Execute. Preview remained non-mutating. | Preview cannot reliably describe the operation that Execute will perform. | No | Add Preview/Execute parity characterization tests, then align command recognition through one shared route. | TASK-091, TASK-093, TASK-094 |
| AUD-009 | MEDIUM | High | Memory / Russian language | Russian memory-key inflection is not normalized. | A fact saved under "маркер аудита 9073" could not be recalled using the naturally inflected phrase "о маркере аудита 9073"; exact-key paths still work. | Natural Russian recall is linguistically brittle. | No | Characterize exact-key and inflected recall behavior, then add approved Russian key-normalization rules without broad fuzzy deletion. | TASK-091, TASK-093, TASK-094 |
| AUD-010 | MEDIUM | High | AppService / metadata | State-changing operation metadata is inconsistent. | Manual runtime audit found `profile.language.set` and some `memory.remember` / `memory.forget` paths changed persistent or session state while showing read-only risk and/or `operation_id` none; other recognition paths showed `local_write`. | Risk and operation tracking are not stable across equivalent commands. | No | Define operation metadata rules for state changes and add equivalent-route characterization tests. | TASK-091, TASK-093, TASK-094 |
| AUD-011 | MEDIUM | High | Planner / Russian grammar | Natural Russian forget-all phrase is misclassified. | "составь план: забудь всё, что ты обо мне помнишь" created an ordinary single-key `memory.forget` step using the literal key text; it did not delete memory and did not bypass confirmation. Exact English forget-all selected the correct destructive capability. | Russian planner grammar does not reach the intended capability reliably. | No | Add planner-language characterization tests and approved Russian forget-all grammar mapping with destructive confirmation retained. | TASK-091, TASK-092 |
| AUD-012 | MEDIUM | High | Planner / Preview policy | Planner execution Preview does not expose the active step's confirmation policy. | Preview of `execute plan` showed `read_only` / `requires_confirmation=no`; actual execution of the active forget-all plan correctly paused at `awaiting_confirmation`. | Safety enforcement worked, but Preview metadata was inaccurate. | No | Project active-step policy into planner execution preview and include destructive confirmation requirements. | TASK-091, TASK-092 |
| AUD-013 | MEDIUM | High | Voice output / metadata | Local TTS result metadata is inconsistent with actual execution. | Manual runtime audit found "диагностика локального голоса" and "тест локального голоса" returned result type `confirmation_required`, category `unknown`, requires confirmation `yes`, but executed immediately and audible TTS succeeded. | Consumers cannot trust category/result/confirmation metadata. | No | Correct local TTS command result metadata and add manual hardware regression checklist coverage. | TASK-096 |
| AUD-005 | LOW | High | Tooling | Coverage tooling is unavailable. | `python -m coverage --version` returned `No module named coverage`; no coverage config tracked. | Audit cannot quantify line/branch coverage; no behavioral failure. | No | Add optional coverage configuration in a future tooling task if desired. | TASK-097 Test Tooling and Coverage Baseline |
| AUD-006 | LOW | High | Repository portability | Four tracked files have mixed line endings. | Mixed line-ending scan: `.gitignore`, `core/base_module.py`, `core/event_bus.py`, `core/module_manager.py`. `git diff --check` still passes. | Low risk of noisy diffs/tooling inconsistency. | No | Normalize line endings with an approved repository hygiene task. | TASK-099 Repository Hygiene |
| AUD-007 | LOW | High | Documentation / onboarding | No root README is tracked. | `git ls-files README README.md README.rst` returned no files. | New contributors lack a single current entry point for setup, test, safety, and launch commands. | No | Create a concise README reflecting current assistant scope and commands. | TASK-098 Documentation Alignment |
| AUD-014 | LOW | High | Desktop UX | Desktop Preview and Execute panes can show results from different actions at the same time. | Manual runtime audit found an old Execute result could be mistaken for the latest Preview result. | Users can misread stale output as current command metadata or result. | No | Add clearer labels, timestamps, clearing behavior, or action identifiers. | TASK-100 |
| AUD-015 | LOW | High | Desktop UX | Desktop result areas lack convenient copy/export controls. | Manual runtime audit found normal result text could not be copied reliably. | Audit/debug evidence capture is harder than necessary. | No | Add selectable text, Ctrl+C, context-menu copy, Copy Preview, Copy Result, Copy All, and optional text export. | TASK-100 |
| AUD-016 | LOW | High | Voice hardware errors | Microphone permission failure exposes a low-level PortAudio/MME message. | With Windows desktop-app microphone access disabled, user-facing failure included `PaErrorCode -9999` / `MME error 1`. The failure was safe. | User-facing message is too technical and does not clearly explain Windows microphone permission or unavailable input device. | No | Translate hardware permission/device failures for users while preserving technical detail in diagnostics/logs. | TASK-096 |

## 22. Verified Non-Issues

- No confirmed credential exposure.
- No confirmed unsafe arbitrary execution path.
- No provider output becomes executable.
- No Desktop Shell direct ActionRouter/provider/filesystem/memory-storage access found.
- No AppService startup provider call observed in isolated measurement.
- No AppService startup microphone, Vosk, or TTS initialization observed.
- No planner persistence in TASK-089.
- Planner uses registered capabilities only.
- Preview paths are non-mutating by tests and inspection.
- Document workflow preserves source and refuses overwrite.
- Memory delete-all confirmation is scoped and idempotency is tested.
- Clean export passes without ignored local state.

## 23. Manual Runtime Audit Matrix

| # | Manual Test | Command | Preconditions | Expected Visible Result | Expected Internal Status | Prohibited Side Effects | Cleanup | Evidence | Pass/Fail |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Cold Desktop Shell launch | `python run_desktop.py` | Clean repo, no provider credentials needed. | Window opens with status and preview panes. | AppService ready; no active plan. | No provider, mic, Vosk, TTS, memory write. | Close window. | Screenshot, console output. | PASS |
| 2 | Status preview | Type `статус`, click Preview. | Desktop open. | Preview says no execution. | No operation id created. | No command execution. | None. | Screenshot. | PASS |
| 3 | Status execution | Type `статус`, click Execute. | Desktop open. | Status text returned. | Operation/result indicates read-only. | No provider/network. | None. | Screenshot. | PASS |
| 4 | Russian language status | Execute `текущий язык`. | Default language. | Russian/ru-RU status. | Language source default/profile. | No provider/network. | None. | Output text. | PASS |
| 5 | Switch to English | Execute `language english`. | Isolated profile recommended. | English selected. | Preference persisted true. | No provider/mic/workflow. | Later switch back. | Output text. | PASS |
| 6 | English language status | Execute `current language`. | English selected. | English response. | `language_code=en-US`. | No provider/network. | None. | Output text. | PASS |
| 7 | Switch back to Russian | Execute `language russian`. | English selected. | Russian selected. | `language_code=ru-RU`. | No provider/network. | None. | Output text. | PASS |
| 8 | Explicit memory remember | Execute `запомни тестовое слово = аудит090`. | Isolated memory path preferred. | Fact saved. | Memory operation changed true. | No provider/action router. | Delete fact later. | Output text. | PASS |
| 9 | Memory recall | Execute `что ты помнишь о тестовом слове`. | Prior fact exists. | Fact is returned. | Read-only recall. | No write. | None. | Output text. | PASS |
| 10 | Restart and recall persistence | Close/reopen, execute recall. | Prior fact exists. | Fact persists. | Memory storage loaded. | No provider. | None. | Output text. | PASS |
| 11 | Memory deletion | Execute `забудь тестовое слово`. | Fact exists. | Fact removed. | Memory changed once. | No unrelated memory deletion. | None. | Recall shows missing. | PASS |
| 12 | Planner preview | Preview `create plan: system status; current language`. | English selected or use Russian equivalent. | Plan preview, no execution. | No active plan if preview only. | No operation/write. | None. | Preview text. | PASS |
| 13 | Planner creation | Execute `create plan: system status; current language`. | English selected. | Plan created. | Plan status proposed. | No step execution. | Cancel after test. | Output text. | PASS |
| 14 | Planner inspection | Execute `show plan`. | Active plan. | Steps listed. | Same plan id. | No execution. | None. | Output text. | PASS |
| 15 | Planner execution | Execute `execute plan`. | Active read-only plan. | Plan completes. | Status succeeded, progress 100. | No provider/mic. | None. | Output text. | PASS |
| 16 | Confirmation memory delete-all plan | Create/execute plan with `forget everything you remember about me`. | Test memory exists. | Awaiting confirmation. | Current step awaiting confirmation. | No delete before yes. | Cancel or confirm. | Output before/after. | PASS |
| 17 | Cancellation path | Execute `cancel plan` while plan awaits confirmation. | Awaiting plan. | Plan cancelled. | Remaining steps not run. | No memory deletion. | None. | Output text. | PASS |
| 18 | Document review temp TXT | Execute `проверить документ C:\path\temp.txt`. | Local temp `.txt`, output absent. | Issues/proposal shown, awaiting confirmation. | Workflow awaiting confirmation. | No output before confirmation. | Delete temp files. | Source/output hashes. | PASS |
| 19 | Confirmation before write | Execute `да`. | Document workflow awaiting. | Output created. | Same operation id succeeded. | No duplicate writes. | Delete output. | File listing/hash. | PASS |
| 20 | Source file unchanged | Compare source hash before/after. | Document workflow completed. | Source unchanged. | Verified true. | No source rewrite. | Delete temp files. | Hashes. | PASS |
| 21 | Generated output verified | Inspect `.jarvis-reviewed.txt`. | Workflow completed. | Expected cleaned text. | Output verified true. | No overwrite. | Delete output. | File content/hash. | PASS |
| 22 | Real one-shot microphone | Execute one-shot voice command. | Local Vosk configured; user authorizes mic. | One short capture then text result. | Capture stops cleanly; recognized text is processed exactly once through the normal AppService execution path; normal policy, confirmation, allowlist, and safety boundaries remain enforced; no raw/direct execution bypass occurs; unsafe or confirmation-required commands are not silently authorized. | No always-on listening, no cloud, no raw/direct execution bypass. | Close app. | Console/UI logs. | PASS |
| 23 | Windows microphone permission denied | Disable Windows desktop-app microphone access and request one-shot. | Desktop Shell open; Vosk otherwise configured. | Safe permission-denied failure. | `voice_recognition_blocked` / `recognition_blocked`; capture, recognition, and text processing do not run. | No crash, no command execution, no partial capture loop. | Restore Windows microphone access. | Output text and recovery check. | PASS |
| 24 | Vosk model unavailable/missing | Run with unavailable or missing Vosk model and request one-shot. | Model path unavailable or model removed. | Safe unavailable-model failure. | State released, repeat allowed. | No crash, no partial capture loop. | Restore model config. | Not manually run in TASK-090; keep on future hardware checklist. | NOT RUN |
| 25 | Audible local TTS | Use the existing safe speak-last-response/manual TTS command or control documented by the repository. | Windows local TTS backend available; user explicitly authorizes audible output; no sensitive text displayed or spoken. | One bounded local utterance; correct language; no repeated speech loop. | Local TTS path used; output safety/redaction remains active; resource returns to idle after completion. | No network, no provider request, no credential or secret spoken, no always-on microphone, no automatic command execution from spoken output. | Stop/mute output if needed; close application. | Console/UI logs and audible observation. | PASS |
| 26 | Close and restart | Close/reopen shell. | Prior tests complete. | Clean startup. | No active plan carried over. | No startup provider/mic/Vosk/TTS. | None. | Screenshot/output. | PASS |

Manual runtime audit date: 2026-07-17.

Completed manual safety and reliability scenarios:

- Desktop startup passed: Desktop Shell started successfully; microphone, TTS, providers, old plans, confirmations, and document workflows did not start or resume automatically.
- Status and language passed: `system.status` worked through AppService; `language.get` returned Russian `ru-RU`; language change persisted during the running session; restart testing showed no delayed-response execution bug.
- Memory passed: Preview did not mutate memory; exact remember, recall, persistence through restart, and exact deletion worked; a unique marker survived a cancelled destructive plan; actual forget-all capability did not execute before confirmation.
- Destructive planner safety passed: exact English `create plan: forget everything you remember about me` selected the real forget-all capability; `execute plan` assigned a non-empty `operation_id`; the plan paused at `awaiting_confirmation`; `cancel plan` cancelled the same plan and operation; the marker remained intact; no confirmation bypass occurred.
- Read-only planner passed: a two-step plan containing `system.status` and `language.get` completed successfully, progress reached 100%, both steps completed once, and no network was used.
- Local TXT document workflow passed: preview required confirmation and did not create output; execute paused at `awaiting_confirmation`; confirmation used `op-2a2a7bb154d1431f99b4b093e2877fa2`; workflow completed 7/7 steps; `saved=yes`, `verified=yes`, `original modified=no`; source SHA256 remained `1A117FC78F228538479ABE6A771C7DDDF5CE8C37EB996CDD9CDD06BEEE71F034`; output SHA256 was `213BB1DD0559EB47AA36AD1BDFD31AFB88D5EBB4C94A06C5A7926270AE3FCBDA`; repeated confirmation did not modify output; only the original and one `.jarvis-reviewed.txt` copy existed.
- Real One-Shot Voice passed: microphone and Vosk worked locally, Russian normalization worked, multiple consecutive captures worked, text went through normal AppService, raw audio was not sent externally, responses were not executed as commands, and no secrets were exposed.
- Local audible TTS passed: `windows_local_tts` was available, audible test speech was heard, cloud was not used, audio files were not saved, and Desktop Shell remained responsive.
- Microphone denial and recovery passed: disabled Windows desktop-app microphone access produced `voice_recognition_blocked` / `recognition_blocked`; capture, recognition, and text processing did not run; no accidental command executed; Desktop Shell stayed stable; after permission restoration, "статус системы" worked normally.
- Vosk model unavailable/missing was NOT RUN as a manual hardware scenario in TASK-090. The unavailable-model scenario remains covered only by automated or non-hardware evidence where applicable and remains part of the future TASK-096 checklist.

Manual matrix totals: PASS 25, FAIL 0, NOT RUN 1.

Manual findings from this run are recorded as AUD-008 through AUD-016.

## 24. External Integration Tests Requiring Authorization

Optional, not part of default manual matrix:

- One controlled real provider request through an explicit one-shot command.
- Requires explicit user authorization, network, configured credential, and acceptance of cost/privacy implications.
- Must run in a separate session with prompt and provider documented.
- Expected: request gate checks provider config, privacy/cost guard passes, one response returns as text, response is not executed, credential value is not printed.

## 25. Audit Limitations

- No real provider/network request was made.
- Real microphone, Vosk, audible local TTS, and microphone denial/recovery were manually checked on 2026-07-17.
- External provider checks remain manual or separately authorized integration checks.
- HEALTHY WITH REMEDIATION REQUIRED does not mean feature-complete or production-certified.
- Coverage was unavailable.
- Static analysis tools were unavailable.
- Hardware behavior has manual evidence but is not automated.
- Sandbox temp-permission failures required rerunning pytest/health with normal temp access.
- Findings are evidence-based; speculative concerns are listed as limitations or future risks, not findings.

## 26. Recommended Next Actions

1. Review this audit, traceability report, and manual findings AUD-008 through AUD-016.
2. Do not remediate inside TASK-090.
3. Start TASK-091 with Preview/Execute parity, equivalent-route metadata, confirmation metadata, and operation ID characterization tests.
4. Keep all safety-critical behavior covered by existing tests before refactors.
5. Update stale documentation only after remediation sequencing is approved.
