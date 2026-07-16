# TASK-087 Startup Profiling & Lazy Initialization

## Startup Phases

`JarvisAppService` now records monotonic startup phases for command registry,
command processor composition, lazy optional component registration, language
manager setup, app safety boundaries, and document workflow construction.
Snapshots are immutable DTOs and are not persisted or sent anywhere.

## Eager Components

The command registry, intent resolver, language manager, policy boundary,
execution coordinator, execution journal, audio lifecycle metadata controller,
and document workflow wiring remain eager. These are lightweight safety and
text-command boundaries required for immediate safe operation.

## Lazy Components

Optional provider and voice resources are registered as lazy components:
secure provider runtime, provider router/request gates, provider consensus and
fallback helpers, live verification, API key manager, and one-shot voice
recognition. Registration does not call factories.

## Lifecycle

Lazy state starts as `deferred`, moves to `initializing` during first explicit
access, then to `ready` after the factory completes. Failed factories move to
`failed`; partial instances are not published. Failure snapshots expose only a
safe error code.

## First Use

Provider diagnostics or explicit provider paths initialize provider-related
components once and reuse them. One-shot voice requests initialize the voice
recognition component once and reuse it for later one-shot requests where the
component supports reuse.

## Failure And Thread Safety

Lazy initialization is guarded by a lock so concurrent first access cannot
create duplicates. Factory exceptions are converted to safe typed failures
without raw exception text.

## Diagnostics

`JarvisAppService.get_startup_profile()` and `startup_profile_text_ru()` expose
startup completion, total measured duration, ordered phases, eager components,
and lazy component states. Inspecting diagnostics does not initialize deferred
components.

## Telemetry And Timing

No external telemetry, network reporting, persistent performance database, or
machine-specific hard timing target is added.

## Manual Smoke

Run:

```powershell
python -m pytest tests/unit/test_startup_profiler.py -v
python -m pytest tests/unit/test_lazy_initialization.py -v
python -m pytest tests/integration/test_task_087_startup_lazy_initialization.py -v
powershell -ExecutionPolicy Bypass -File scripts/assistant_smoke.ps1
```

## Known Limitations

The profile measures in-process composition only. It does not include GUI event
loop startup, operating-system scheduling, or provider/model request latency.
