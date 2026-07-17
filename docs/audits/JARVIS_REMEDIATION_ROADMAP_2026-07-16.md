# JARVIS Remediation Roadmap

Audit source: TASK-090 Full System Architecture, Security & Reliability Audit.

Final verdict: HEALTHY WITH REMEDIATION REQUIRED.

Verdict scope: HEALTHY WITH REMEDIATION REQUIRED applies to repository integrity, automated safety boundaries, tested application contracts, clean-export verification, and the 2026-07-17 manual runtime audit. No critical or high-severity safety failure was found. Automated tests, clean export checks, health check, permanent smoke, destructive confirmation/cancellation, document write isolation, real microphone/Vosk, local TTS, hardware denial recovery, and safe startup passed. The remediation requirement is caused by multiple MEDIUM contract, metadata, Preview parity, planner-language, and command-classification inconsistencies. This verdict is not production certification and does not mean feature completeness.

No TASK-090 remediation was performed. This roadmap proposes future tasks only.

## Priority Order

No confirmed critical or high findings exist. The sequence therefore starts with behavior characterization and contract parity, planner snapshot/policy projection, ownership cleanup, hardware voice metadata/error polish, tooling, documentation, repository hygiene, and Desktop Shell result usability.

## TASK-091 - AppService and CommandProcessor Boundary Design & Characterization Tests

- Finding IDs addressed: AUD-001 design phase only; AUD-008, AUD-009, AUD-010, AUD-011, AUD-012 characterization phase.
- Objective: Define bounded extraction seams for `JarvisAppService` and `CommandProcessor`, and add characterization tests for current behavior before production extraction.
- Required characterization tests: Preview/Execute parity, equivalent command routes, risk metadata, confirmation metadata, operation ID rules, Russian memory inflection behavior, Russian forget-all planner grammar, and planner active-step Preview policy.
- Reason for order: The largest orchestration hotspots and the newly confirmed contract inconsistencies should be characterized before behavior-preserving implementation work.
- Expected files: `.ai/tasks/TASK-091-...md`, focused characterization tests, and possibly architecture notes. Production extraction requires separate approval.
- Testing strategy: Focused AppService/CommandProcessor characterization tests plus existing related suites; full pytest if tests are added.
- Manual check requirement: user review of proposed boundaries.
- Dependencies: TASK-090.
- Estimated size: medium.
- User-visible behavior change: no.

## TASK-092 - Planner Snapshot Boundary Cleanup

- Finding IDs addressed: AUD-002, AUD-011, AUD-012.
- Objective: Remove `PlanExecutor` dependency on private `_PlanState` by introducing a public snapshot builder/update API or shared immutable factory, and expose a planner active-step snapshot/policy projection that Preview can use.
- Reason for order: Planner is new and bounded; cleanup is smaller before additional planner capabilities are added.
- Expected files: `planner/contracts.py`, `planner/multi_step_planner.py`, `planner/plan_executor.py`, planner tests.
- Testing strategy: `tests/unit/test_multi_step_planner.py`, `tests/unit/test_plan_executor.py`, `tests/integration/test_task_089_general_multi_step_planner.py`, new tests for destructive active-step confirmation projection, full pytest, strict DeprecationWarning pytest.
- Manual check requirement: planner create/show/execute/cancel smoke, including destructive forget-all Preview showing confirmation requirements before execution.
- Dependencies: TASK-091 may inform naming, but this can proceed independently if scoped.
- Estimated size: small.
- User-visible behavior change: no.

## TASK-093 - AppService Orchestration Extraction Phase 1

- Finding IDs addressed: AUD-001 partial implementation; AUD-008, AUD-009, AUD-010 ownership and metadata remediation as applicable.
- Bounded responsibility to extract or clarify: one narrow AppService-owned orchestration area, preferably command classification/preview metadata, document workflow, or memory command handling, into an internal helper/service behind existing AppService DTOs.
- Ownership clarification required: define which layer owns command classification, risk, category, operation tracking, and result metadata when AppService and CommandProcessor can both recognize equivalent commands.
- Prohibited behavior changes: no command grammar changes, no new side effects, no provider calls, no microphone/Vosk/TTS initialization, no changed persistence paths, no changed confirmation semantics.
- Required preservation: AppService DTO boundaries; policy boundary; confirmation flow; execution coordinator and journal; lazy startup; provider runtime behavior; memory behavior; planner behavior; voice behavior.
- Expected files: `app/app_service.py`, one new internal app module only if justified by TASK-091, focused AppService tests.
- Testing strategy: focused AppService tests for extracted path, related integration tests, full pytest, strict DeprecationWarning pytest, assistant smoke, health check.
- Manual smoke requirement: required if user-visible document, memory, planner, voice, or desktop paths are touched.
- Dependencies: TASK-091.
- Estimated size: medium.
- User-visible behavior change: no.

## TASK-094 - CommandProcessor Orchestration Extraction Phase 1

- Finding IDs addressed: AUD-001 partial implementation; AUD-008, AUD-009, AUD-010 ownership and metadata remediation as applicable.
- Bounded responsibility to extract or clarify: one narrow CommandProcessor-owned command group, preferably memory command handling, provider status/gating, or command classification metadata, into a helper that preserves current public command behavior.
- Ownership clarification required: define which layer owns command classification, risk, category, operation tracking, and result metadata when CommandProcessor and AppService expose equivalent behavior.
- Prohibited behavior changes: no command grammar changes, no provider/network activation, no ActionRouter expansion, no changed memory/profile paths, no changed confirmation/idempotency semantics.
- Required preservation: AppService DTO boundaries; policy and confirmation behavior; execution journal behavior where routed through AppService; lazy startup; provider gates/runtime behavior; memory behavior; planner behavior; voice normalization/allowlist behavior.
- Expected files: `core/command_processor.py`, one new core helper module only if justified by TASK-091, focused CommandProcessor tests.
- Testing strategy: focused CommandProcessor tests for extracted group, relevant voice/provider/memory tests, full pytest, strict DeprecationWarning pytest, assistant smoke, health check.
- Manual smoke requirement: required if user-visible command output or desktop execution paths are touched.
- Dependencies: TASK-091.
- Estimated size: medium.
- User-visible behavior change: no.

## TASK-095 - Persistence Concurrency and Corruption Test Expansion

- Finding IDs addressed: audit limitations and persistence risks; no direct defect unless tests expose one.
- Objective: Add targeted tests for JSON persistence corruption, partial writes, concurrent-like interleaving, and recovery expectations for memory/profile/Vosk settings/secure key metadata where feasible.
- Reason for order: Persistence behavior should be clarified before broader orchestration changes continue.
- Expected files: memory/profile/Vosk settings/secure key tests; no production code unless tests expose a confirmed defect and user approves remediation.
- Testing strategy: new negative-path unit tests plus full pytest and strict DeprecationWarning pytest.
- Manual check requirement: none unless production behavior changes.
- Dependencies: TASK-091 for ownership clarity if production changes are needed.
- Estimated size: medium.
- User-visible behavior change: no by default.

## TASK-096 - Real Hardware Voice Verification, Metadata, and Error Translation

- Finding IDs addressed: AUD-013, AUD-016, manual hardware regression coverage.
- Objective: Add a documented manual-only verification checklist for one-shot microphone, local Vosk recognition through the normal AppService safety path, unavailable device/model failure, separate audible Windows TTS, local TTS metadata correctness, and user-facing hardware error translation.
- Reason for order: Automated tests intentionally avoid real devices; manual coverage should be standardized, and the 2026-07-17 audit confirmed TTS metadata and microphone permission-message issues.
- Expected files: docs/manual verification document and possibly a non-invasive script wrapper that does not open devices without explicit user action.
- Testing strategy: existing voice unit tests plus focused metadata/error tests where possible, and manual checklist execution by user.
- Manual check requirement: required with user-authorized local hardware/model; one-shot recognized text must be processed exactly once through normal policy/confirmation/allowlist boundaries, audible TTS must be checked separately, denied microphone access must produce a user-readable permission/device message while technical details remain diagnostics-only.
- Dependencies: local Vosk/audio setup by user.
- Estimated size: small.
- User-visible behavior change: no.

## TASK-097 - Test Tooling and Coverage Baseline

- Finding IDs addressed: AUD-005.
- Objective: Decide whether to add coverage tooling/configuration and document how coverage data must be written outside the repo during audits.
- Reason for order: Tooling should follow critical architecture/persistence clarification.
- Expected files: optional config/docs only; dependency changes require explicit approval.
- Testing strategy: run full pytest; if coverage is added, run full suite under coverage and record baseline without setting an arbitrary gate.
- Manual check requirement: no.
- Dependencies: user approval for dependency/tooling addition.
- Estimated size: small.
- User-visible behavior change: no.

## TASK-098 - Documentation Alignment

- Finding IDs addressed: AUD-003, AUD-004, AUD-007, and documentation updates for AUD-008 through AUD-016 after behavior decisions.
- Objective: Update root onboarding and architecture/AppService docs to match current assistant scope, Windows target, Russian default, English support, AppService responsibilities, verified manual behavior, known limitations, and current verification commands.
- Reason for order: Documentation should reflect approved architecture boundaries after TASK-091 through TASK-095 decisions where possible.
- Expected files: `README.md`, `docs/ARCHITECTURE.md`, `docs/JARVIS_APP_SERVICE.md`, possibly `docs/DEVELOPMENT_WORKFLOW.md`.
- Testing strategy: documentation review plus smoke/health if command examples change.
- Manual check requirement: user review for product wording.
- Dependencies: TASK-091 through TASK-095 preferred.
- Estimated size: medium.
- User-visible behavior change: no runtime behavior change.

## TASK-099 - Repository Hygiene

- Finding IDs addressed: AUD-006.
- Objective: Normalize mixed line endings and document line-ending expectations.
- Reason for order: Low risk and should be done separately to keep diffs clean.
- Expected files: `.gitignore`, `core/base_module.py`, `core/event_bus.py`, `core/module_manager.py`, optionally `.gitattributes` if approved.
- Testing strategy: `git diff --check`, full pytest, strict DeprecationWarning pytest, health check.
- Manual check requirement: no.
- Dependencies: none.
- Estimated size: small.
- User-visible behavior change: no.

## TASK-100 - Desktop Shell Result Copy, Export & Action-Clarity UX

- Finding IDs addressed: AUD-014, AUD-015.
- Objective: Improve Desktop Shell result panes so Preview and Execute outputs are clearly tied to actions and easy to copy/export.
- Required UX: selectable result text, Ctrl+C, context-menu copy, Copy Preview, Copy Result, Copy All, timestamps/action identifiers, clearer labels or clearing behavior so stale Execute output cannot be mistaken for a new Preview result, and optional text export.
- Reason for order: This is low-risk UX work and should remain separate from command-contract remediation.
- Expected files: `app/desktop_shell.py`, focused Desktop Shell tests, and optional user-facing docs if controls are documented.
- Testing strategy: Desktop Shell unit tests, manual preview/execute/copy smoke, full pytest if behavior code changes.
- Manual check requirement: verify normal result text can be selected/copied and Preview/Execute outputs show distinct action identity.
- Dependencies: none, but can follow TASK-091 if action metadata shapes are changing.
- Estimated size: small.
- User-visible behavior change: yes, Desktop Shell usability only.

## Deferred / Optional

- External provider live verification: optional, requires explicit user authorization, network, credentials, and cost/privacy acceptance.
- Linux portability work: optional future track; current target is Windows 11.
- Broader static analysis adoption: optional after tooling policy is approved.
