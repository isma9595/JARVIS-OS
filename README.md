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

The implementation remains transitional. `JarvisAppService` is the current
application-facing boundary, and major responsibilities have been extracted,
but `app/app_service.py` and `core/command_processor.py` are still large
orchestration modules.

## Implemented Capabilities

- CLI entry point through `run.py`.
- Tkinter Desktop Shell prototype through `run_desktop.py`.
- App-facing service boundary in `app/app_service.py`.
- Versioned DTO contracts in `app/app_contracts.py`.
- Command registry metadata in `core/command_registry.py`.
- Deterministic command resolution in `core/command_resolution_service.py`.
- Legacy command execution facade in `core/command_processor.py`.
- Unified policy decisions in `core/policy_boundary.py`.
- Execution coordination, idempotency, cancellation, and in-memory operation
  journal in `core/execution_coordinator.py` and `core/execution_journal.py`.
- Desktop execution history viewer backed by the existing Execution Journal and
  projected through AppService-safe DTOs, with local Desktop text search and
  status filtering over the bounded loaded history.
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

## Architecture

Current dependency direction:

```text
Desktop Shell -> JarvisAppService -> DTOs / services / policy / planner /
workflow / memory / voice / provider-runtime boundaries -> CommandProcessor
legacy execution where needed
```

Key architecture documents:

- `docs/ARCHITECTURE.md`
- `docs/JARVIS_APP_SERVICE.md`
- `docs/APPSERVICE_CONTRACTS.md`
- `docs/AUDIT_STATUS.md`
- `docs/audits/JARVIS_FULL_SYSTEM_AUDIT_2026-07-16.md`
- `docs/audits/JARVIS_REMEDIATION_ROADMAP_2026-07-16.md`

## Requirements

The repository is currently developed and verified on Windows with PowerShell
and Python. Recent task records and verification runs use Python 3.14-series
interpreters. No dependency manifest is currently tracked at the repository
root, so dependency installation is manual and environment-specific.

Core verification requires:

- `python`
- `pytest`
- PowerShell
- Tkinter support for the Desktop Shell

Optional local voice features require user-provided local audio/Vosk setup.
Optional provider calls require explicit user authorization, configured
credentials, and acceptance of network/cost/privacy implications.

## Setup

From PowerShell:

```powershell
cd C:\JARVIS-OS
python --version
python -m pytest --version
```

There is no tracked `requirements.txt`, `pyproject.toml`, or lock file in the
current repository baseline. Do not add or upgrade dependencies without an
approved task.

## Basic Configuration

Local runtime state is kept in repository-local or user-local files depending
on the subsystem:

- user profile: `users/profiles/default_user.json`
- local memory: `memory/local/memory.json`
- Vosk settings: `config/local/vosk_settings.json`
- secure key metadata: Windows DPAPI-backed user-local storage when available

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
- Workflow run history is read-only and projected from existing workflow
  runtime state with safe DTOs.
- Workflow resume is explicit, policy-gated, and AppService-mediated. It starts
  at the first safe unfinished step, does not rerun completed steps by default,
  preserves the source run history, and creates a distinct linked resumed
  attempt.
- Desktop workflow history supports viewing, manual refresh, selection, ordered
  step inspection, safe copy, and explicit resume for eligible runs only.
- Network/provider calls are explicit-only.
- Raw microphone audio remains local; recognized text enters the same
  AppService route as typed input.
- Secrets must not be printed or exposed through DTOs, status text, logs, or
  operation metadata.
- Desktop UI code must use AppService rather than bypassing application
  boundaries.

## Current Limitations

- `JarvisAppService` and `CommandProcessor` remain comparatively large.
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
