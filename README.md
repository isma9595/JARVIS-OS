# JARVIS OS

JARVIS OS is a Windows-first personal assistant application. It is not a
replacement operating system. The current repository contains a Python runtime,
a Tkinter Desktop Shell prototype, an AppService boundary for UI clients,
deterministic command handling, local memory, local voice/Vosk integration
boundaries, local TTS support, provider adapters behind explicit gates, a
planner, and a safe local TXT document-review workflow.

## Current Status

The main architecture audit cycle from TASK-090 through TASK-102 is closed for
the current development baseline. Critical remediation items identified for the
cycle have been addressed. Remaining audit items are tracked as non-blocking
future work: targeted decomposition, documentation maintenance, optional test
coverage tooling, repository line-ending maintenance, and Desktop Shell UX
polish.

The published baseline is TASK-128 at
`612426d3e3aaed593c29ef16862a1ef6f1cf44f4`. It includes the chat-first
Desktop projection while retaining the TASK-127 provider boundary, TASK-124
Desktop worker, and TASK-123 conversation persistence boundaries. TASK-129 is a
documentation-only project rebaseline: it changes no runtime behavior and makes
the full-personal-agent direction normative. `JarvisAppService` remains the
current application-facing boundary, and major responsibilities have been
extracted, but `app/app_service.py` and `core/command_processor.py` are still
large orchestration modules.

## Implemented Capabilities

- CLI entry point through `run.py`.
- Tkinter Desktop Shell prototype through `run_desktop.py`.
- App-facing service boundary in `app/app_service.py`.
- Versioned DTO contracts in `app/app_contracts.py`.
- Cognitive conversation contracts and orchestration in `cognition/`, including
  owned session lifecycle, bounded ordered context, deterministic intent,
  conservative reference resolution, and stateless clarification.
- `ConversationSessionRepository` and
  `LocalConversationSessionRepository` persistence boundaries for
  bounded/redacted session records. Standard Desktop composition is
  repository-backed and automatically resumes the latest ACTIVE session;
  direct `JarvisAppService()` construction remains in-memory.
- The conversation repository retains per-record partial-load diagnostics for
  direct repository-backed use. TASK-125 supported composition adds a stricter
  pre-owner migration/health gate: a corrupt or unsupported authoritative store
  blocks that startup attempt rather than being used as migration input.
  Persisted turns contain bounded/redacted summaries rather than raw user text
  or secrets.
- Supported Desktop and CLI composition resolve one immutable canonical local
  data root: `%LOCALAPPDATA%\JARVIS-OS\data\v1` on Windows, with
  `~/.jarvis-os/data/v1` fallback and exact-root `JARVIS_USER_DATA_DIR`
  override. Fixed stores live below `conversation/`, `memory/`, `profiles/`,
  `ideas/`, and `voice/`; default paths do not depend on startup CWD.
- Known deterministic legacy stores are validated and copied without overwrite
  or source deletion before ordinary owners are constructed. Private path-free
  receipts make later startup canonical-only; ambiguous, conflicting, unsafe,
  corrupt, or unsupported state fails closed.
- AppService exposes a stateless read-only persistence-health snapshot and safe
  status card containing only stable store codes, schema/layout metadata, and
  bounded counts. Paths, contents, identifiers, exception text, and secrets are
  excluded. Windows DPAPI storage remains security-owned and is not relocated.
- One AppService-owned Desktop cognitive turn facade shared by typed input and
  one-shot voice, with natural response text separated from technical
  diagnostics and optional execution metadata.
- One immutable path-free `AppDesktopChatStatus` projection for session,
  response, explicit retry, and persistence state. Desktop presents this DTO
  but does not inspect cognition, providers, repositories, or health internals.
- Deterministic stateless `MemoryPolicy` foundation for eligibility, approval,
  retention, deduplication, supersession, sensitivity, and deletion decisions.
  The policy owns no storage and is not yet connected to AppService, Desktop,
  or existing memory commands.
- Command registry metadata in `core/command_registry.py`.
- Deterministic command resolution in `core/command_resolution_service.py`.
- Legacy command execution facade in `core/command_processor.py`.
- Unified policy decisions in `core/policy_boundary.py`.
- Execution coordination, idempotency, cancellation, and in-memory operation
  journal in `core/execution_coordinator.py` and `core/execution_journal.py`.
- Desktop execution history viewer backed by the existing Execution Journal and
  projected through AppService-safe DTOs, with local Desktop text search and
  status filtering over the bounded loaded history.
- Desktop Activity Status panel backed by AppService-safe application activity
  DTOs projected from existing execution lifecycle snapshots.
- Deterministic multi-step planner in `planner/`.
- Reusable workflow runner and local TXT document-review workflow in
  `workflows/`.
- Read-only workflow run state and ordered step history projection for current
  in-memory workflow runs.
- Desktop Workflow History panel that reads recent workflow runs and selected
  run details through AppService-safe DTOs only.
- Explicit safe workflow resume for eligible failed/interrupted in-memory
  workflow runs through AppService, with centralized eligibility checks,
  definition compatibility validation, duplicate-request protection, and a
  distinct linked resumed attempt.
- Explicit safe workflow cancellation for eligible active in-memory workflow
  runs through AppService, with centralized eligibility checks, cooperative
  cancellation signalling, duplicate-request protection, and preserved
  completed-step history.
- One lazy serialized non-daemon Desktop worker for typed, one-shot voice, and
  workflow-resume GUI entry points. Desktop remains an AppService-only client;
  the worker owns scheduling and shutdown, not execution, workflow, cognition,
  or persistence. Cancellation is cooperative and never claims rollback or
  force-stop of a started opaque AppService call.
- Main-thread completion polling keeps Tk and `DesktopShellState` updates out of
  the worker thread. Close waits for safe worker stop, performs no Tk update
  after destroy, and leaves the ACTIVE conversation resumable. During shutdown
  worker termination does not depend on Tk consuming completion; pending
  completion remains retrievable exactly once, and the post-mainloop fallback
  discards it without applying a user result.
- Workflow lifecycle hardening that enforces non-cancellable active steps in
  the central workflow cancellation policy and closes the TASK-105 through
  TASK-109 workflow subsystem milestone.
- Windows local filesystem adapter boundary in `platform_adapters/`.
- Local memory and bounded conversation context in `memory/`.
- Russian-first language preference with English support in `language/`.
- One-shot local microphone/Vosk recognition boundaries in `voice/`.
- Local speech synthesis boundary, including Windows local TTS support, in
  `voice/`.
- AI provider contracts, gates, selection, fallback, and secure runtime status
  boundaries in `ai/`.
- Secure key storage foundation in `security/`.

Planned or future capabilities are not complete unless they are listed above
and supported by source and tests. Provider settings UI, installer mode, mobile
clients, admin/support surfaces, broad portability, wake-word listening, and
continuous autonomous automation remain future work.

TASK-127 makes standard Desktop conversation Groq-backed through the existing
privacy, cost/model, credential, and language gates. Only bounded safe session
context is packaged; memory, profile, files, logs, screen content, audio, and
raw secrets are not sent automatically. A missing key, blocked context, guard
refusal, or provider failure returns the existing deterministic compatibility
answer. Direct `JarvisAppService()` construction remains in-memory and
compatibility-based unless a composer/gate is explicitly injected.

Groq response text is bounded, redacted, and treated only as untrusted
presentation output. It is never automatically submitted for command or
workflow execution. Known commands, confirmation, cancellation, and execution
continue through their existing AppService routes. Legacy `run.py` remains on
its separate `CommandProcessor` compatibility path; TASK-127 changes the
supported Desktop conversation composition, not the later CLI router
consolidation.

TASK-128 makes the Desktop primary flow visibly chat-first: `Сообщение` and
`Отправить` lead to a prominent assistant response, a compact AppService-owned
chat status, and an explicit `Повторить запрос` action when the projected result
is eligible. Retry uses the same cognitive session, AppService facade, and
single bounded Desktop worker. It is never automatic, does not create a queue,
and is unavailable for command/control, clarification, privacy-blocked, or
failed turns. Persistence is shown only as path-free state/code; no record,
path, secret, traceback, or raw provider error is exposed.
Gate-level privacy refusals use the configured semantic privacy decision and do
not become misleading provider-unavailable retries. Unknown externally supplied
session ids are not echoed into the path-free status projection, and clearing
the response refreshes the visible status to idle/no-retry.

TASK-129 defines JARVIS as a goal-driven, tool-using, verifiable, resumable,
model-independent personal AI agent. Models remain replaceable engines beneath
JARVIS-owned permissions, context, execution, provenance, persistence, memory,
and verification. This direction is a roadmap, not implemented Agent Runtime.
New user capabilities must not be built primarily by expanding literal phrase
tables in `CommandProcessor`, legacy passthrough tables, or deterministic
planner grammar. Existing behavior stays as a tested compatibility layer until
an eval-backed migration task replaces it. TASK-130 — Golden Agent Evals v1 is
the next implementation task.

TASK-130 adds the first Golden Agent Eval suite without changing production
runtime behavior. Thirty versioned offline goals exercise the public AppService
boundary with deterministic fakes across conversation, provider isolation,
privacy, command selection, preview, clarification, confirmation, cancellation,
sessions, bounded context, and deliberately unsupported future agent goals.
The report separates behavioral-contract pass rate from actual task-success
rate and records unsafe actions, unnecessary confirmation, human intervention,
recovery, duplicate effects, steps, and model/tool calls. Token/cost, context
precision, and verifier accuracy remain explicitly unavailable until a future
runtime exposes trustworthy signals; they are not reported as artificial zeros.
The baseline adapter derives outcomes from AppService DTOs rather than expected
fixture labels, counts actual registered-command invocations, and installs
fail-closed network/provider/microphone/filesystem boundaries for every case.
Callback failures count as failed goals in the total-case task-success rate.

## Architecture

Current dependency direction:

```text
Desktop Shell -> JarvisAppService -> DTOs / services / policy / planner /
workflow / cognition / memory / voice / provider-runtime boundaries ->
CommandProcessor legacy execution where needed
```

Key architecture documents:

- `docs/ARCHITECTURE.md`
- `docs/ROADMAP.md`
- `docs/AGENTIC_ROADMAP_V1.md`
- `docs/architecture/COGNITIVE_ARCHITECTURE.md`
- `docs/JARVIS_APP_SERVICE.md`
- `docs/APPSERVICE_CONTRACTS.md`
- `docs/AUDIT_STATUS.md`
- `docs/audits/JARVIS_FULL_SYSTEM_AUDIT_2026-07-16.md`
- `docs/audits/JARVIS_REMEDIATION_ROADMAP_2026-07-16.md`

## Requirements

The supported automated test baseline is Windows Server 2025 with CPython
3.14.6. `requirements-ci.txt` exactly pins pytest and its complete transitive
dependency set, while `pytest.ini` keeps repository test discovery consistent
locally and in CI.

Core verification requires:

- `python`
- `pytest`
- PowerShell
- Tkinter support for the Desktop Shell

Optional local voice features require user-provided local audio/Vosk setup.
Their `numpy`, `sounddevice`, and `vosk` packages are intentionally not part of
the mandatory CI manifest.
Optional provider calls require explicit user authorization, configured
credentials, and acceptance of network/cost/privacy implications.

## Setup

From PowerShell:

```powershell
cd C:\JARVIS-OS
python --version
python -m pip install --requirement requirements-ci.txt
python -m pytest -q
```

The same install and test commands are used by `.github/workflows/ci.yml` on
the fixed `windows-2025` / Python 3.14.6 baseline. CI uses read-only repository
permissions, immutable action revisions, and no credentials or provider calls.
Dependency updates remain explicit reviewed changes; JARVIS runtime never
installs packages automatically.

## Basic Configuration

Supported Desktop and CLI launches keep ordinary runtime state below one
versioned user-local root. On Windows the default is
`%LOCALAPPDATA%\JARVIS-OS\data\v1`; without `LOCALAPPDATA` it is
`~/.jarvis-os/data/v1`. `JARVIS_USER_DATA_DIR` is an exact root override.
Conversation sessions, memory, profile, ideas, and Vosk settings use fixed
subpaths below that root. Explicit per-store paths retain priority and opt out
of default migration for that store. Secure-key metadata remains at its
security-owned Windows DPAPI location.

These files are local state, not public contracts. The default user-facing
language is Russian (`ru-RU`), with English (`en-US`) supported through the
language preference boundary.

## Launch

CLI:

```powershell
python run.py
```

Desktop Shell:

```powershell
python run_desktop.py
```

The Desktop Shell uses `JarvisAppService`. It does not call `CommandProcessor`,
providers, filesystem adapters, or memory storage directly.

## Verification

Full pytest suite:

```powershell
python -m pytest -q
```

Strict deprecation-warning run:

```powershell
python -W error::DeprecationWarning -m pytest -q
```

Health check:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\health_check.ps1
```

Assistant smoke test:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\assistant_smoke.ps1
```

Source compilation:

```powershell
python -m compileall ai app automation brain config core database dialogue ideas integrations interface language memory planner platform_adapters plugins scheduler security services tools users vision voice workflows
```

Whitespace check:

```powershell
git diff --check
```

## Repository Structure

- `.ai/tasks/` - task records and verification notes.
- `ai/` - provider contracts, adapters, gates, selection, fallback, runtime.
- `app/` - AppService, contracts, Desktop Shell, resolver, startup profiling.
- `core/` - kernel, command registry, command processing, policy, execution.
- `docs/` - architecture, safety, provider, voice, audit, and workflow docs.
- `language/` - application language preference.
- `memory/` - local memory and conversation context.
- `planner/` - deterministic multi-step planner and executor.
- `platform_adapters/` - local platform boundary implementations.
- `scripts/` - health check and assistant smoke wrappers.
- `security/` - secure key storage and API-key manager.
- `tests/` - unit, integration, smoke, and characterization tests.
- `voice/` - microphone, Vosk, voice normalization, and TTS boundaries.
- `workflows/` - workflow runner and local document-review workflow.

## Safety Principles

- Preview must not execute commands or mutate state.
- Risky and destructive operations must pass through explicit confirmation.
- Provider responses must not be executed as commands.
- Execution history is read-only in the Desktop Shell; it supports viewing,
  refresh, local filtering/search, selection, and safe copy, not replay,
  editing, deletion, or export.
- Activity status is read-only in the Desktop Shell; it shows current
  application-level activity, idle/busy state, user-attention state, and bounded
  recent outcomes through AppService DTOs only.
- Workflow run history is read-only and projected from existing workflow
  runtime state with safe DTOs.
- Workflow resume is explicit, policy-gated, and AppService-mediated. It starts
  at the first safe unfinished step, does not rerun completed steps by default,
  preserves the source run history, and creates a distinct linked resumed
  attempt.
- Workflow cancellation is explicit, policy-gated, AppService-mediated, and
  cooperative. It does not roll back completed work or force-kill running
  work, and rejects non-cancellable active steps centrally; once accepted, later
  workflow steps are not started.
- Desktop workflow history supports viewing, manual refresh, selection, ordered
  step inspection, safe copy, explicit resume for eligible runs, and explicit
  cancellation for eligible active runs only.
- Network/provider calls are explicit-only.
- Raw microphone audio remains local; recognized text enters the same
  AppService route as typed input.
- Secrets must not be printed or exposed through DTOs, status text, logs, or
  operation metadata.
- Desktop UI code must use AppService rather than bypassing application
  boundaries.

## Current Limitations

- `JarvisAppService` and `CommandProcessor` remain comparatively large.
- Agent Runtime, Tool Registry, durable AgentRun state, Planner v2, verification,
  and autonomous tool loops are roadmap items, not current runtime features.
- Golden Agent Evals measure the current baseline but do not themselves add
  tools, execution capability, provider access, or autonomous behavior. Current
  task success is intentionally below full-agent acceptance.
- Literal `CommandProcessor`, legacy passthrough, and deterministic planner
  phrase-grammar growth are frozen; existing compatibility behavior remains.
- Default Desktop persistence provides automatic latest-ACTIVE resume only;
  chat history browsing, manual session selection, retention, and migration of
  the former unversioned path are not implemented.
- Standard Desktop conversation may use the gated Groq primary provider and
  falls back deterministically; direct `JarvisAppService()` construction
  remains compatibility-based and in-memory.
- `MemoryPolicy` is implemented and exported but is not used by AppService,
  Desktop, or existing memory command routes.
- Desktop GUI entry points now share one bounded interaction worker; deeper
  domain cancellation remains owned by execution and workflow services.
- Supported Desktop and CLI composition use the TASK-125 canonical user-data
  root; explicitly unsupported legacy paths remain outside that migration.
- Automated verification currently supports one Windows Server 2025 / Python
  3.14.6 baseline; broader platform and interpreter matrices are not claimed.
- Formal coverage tooling/policy is not tracked.
- Some line-ending normalization is deferred to repository maintenance.
- Desktop Shell action clarity and broader copy/export controls remain future
  UX work.
- Workflow retry, replay, deletion, editing, export, persistence redesign,
  restart-persistent recovery, and advanced workflow analytics remain future
  work.
- Real hardware and external provider checks require explicit manual
  authorization and environment setup.
- Linux/macOS portability is a future goal, not a current verified support
  claim.

## Development Notes

Keep changes small, task-scoped, and testable. Do not change runtime behavior,
public contracts, dependencies, or configuration in documentation-only tasks.
Run the relevant checks before committing. Commit and push only after the user
has explicitly approved that step for the task.
