# TASK-126 - Reproducible Environment and CI

## Status

Implementation and acceptance are complete in the unstaged worktree. Commit
and push are not part of this implementation phase.

## Objective

Define one reviewable test-environment contract and run that same contract in
GitHub Actions so dependency drift or an accidentally different CI suite cannot
silently replace the supported local baseline.

## Verified Baseline

- Published dependency: TASK-125 - Unified User Data and Persistence Health.
- Baseline commit: `12d88cf133c260c3bf49aff9ea3a5323d9f43d9f`.
- Baseline tree: `5562cd95820c8b8fe076e33ea5a2f1acc0d2a377`.
- Branch and `origin/main` both pointed to the baseline commit.
- The worktree and staging area were clean.
- Baseline Python: CPython `3.14.6` on Windows.
- Baseline pytest: `9.1.1`.
- Published TASK-125 acceptance:
  `2677 passed, 4 skipped in 18.42s`.
- No dependency manifest, repository pytest configuration, or CI workflow
  existed before this task.

## Approved File Scope

1. `.github/workflows/ci.yml`
2. `requirements-ci.txt`
3. `pytest.ini`
4. `tests/unit/test_reproducible_environment.py`
5. `.ai/tasks/TASK-126.md`
6. `.ai/CHECKPOINT.md`
7. `README.md`
8. `docs/ARCHITECTURE.md`
9. `docs/ROADMAP.md`

No runtime module is changed by TASK-126.

## Reproducible Environment Contract

The supported automated test baseline is deliberately narrow:

- GitHub-hosted Windows Server 2025 (`windows-2025`);
- CPython `3.14.6`;
- pip `26.1.2` in CI;
- exact pytest and pytest-transitive versions from `requirements-ci.txt`;
- repository `pytest.ini` discovery rooted at `tests`;
- the same `python -m pytest -q` command locally and in CI.

This is the verified test environment, not a claim that every optional JARVIS
feature has become mandatory or portable to every platform.

## Dependency Manifest

`requirements-ci.txt` exactly pins the complete pytest dependency set used by
the supported baseline. It contains no ranges, URLs, editable installs, local
paths, provider SDKs, or runtime voice packages.

`numpy`, `sounddevice`, and `vosk` remain optional, explicitly user-installed
dependencies for local voice features. They are not required to collect or run
the deterministic test suite and are not installed by CI.

Dependency updates remain explicit reviewed changes. JARVIS runtime code does
not install or download packages.

## Pytest Configuration

The repository configuration fixes:

- minimum pytest version `9.1.1`;
- `tests` as the only default discovery root;
- `test_*.py` as the test filename pattern;
- `-ra` for bounded skipped/failed outcome reporting.

It does not enable network, hardware, provider, microphone, TTS, strict warning,
or coverage behavior.

## CI Workflow

The workflow runs for pushes to `main` and pull requests. It has one bounded
Windows job and no matrix or retry queue. It:

1. checks out the repository without persisting credentials;
2. installs the exact supported Python and pip versions;
3. caches only pip downloads using the manifest hash;
4. installs `requirements-ci.txt`;
5. runs `python -m pytest -q` once.

The workflow has `contents: read` permission only and a 15-minute job timeout.
It does not consume secrets, publish artifacts, deploy, release, mutate the
repository, or invoke real providers or hardware.

Official action versions are pinned to immutable release commit SHAs:

- `actions/checkout` v7.0.0:
  `9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0`;
- `actions/setup-python` v7.0.0:
  `5fda3b95a4ea91299a34e894583c3862153e4b97`.

## Preserved Architecture Boundaries

- `JarvisAppService` and all runtime composition remain unchanged.
- Cognition, persistence, Desktop worker, execution, workflow, provider, voice,
  microphone, and TTS ownership remain unchanged.
- The CI workflow verifies code; it is not a runtime scheduler or automation
  owner.
- Provider/network behavior remains explicit-only.
- Optional voice dependencies remain manual and local.
- Compatibility-based Desktop response remains the default.
- `MemoryPolicy` remains not runtime-integrated.

## Test-First Evidence

The contract test was created before the manifest, pytest configuration, and
workflow. The controlled RED was:

`python -m pytest -q tests/unit/test_reproducible_environment.py`

Result: `6 failed in 0.32s`. Every failure was caused by one of the three
approved configuration files being absent.

After adding those files, the same command passed:

`6 passed in 0.07s`.

## Acceptance Criteria

- The approved test dependency graph is exactly pinned.
- Optional runtime dependencies are not silently promoted to CI requirements.
- Local and CI discovery use the same repository pytest configuration.
- CI uses one explicit Windows and Python baseline.
- Third-party Actions are pinned to immutable commit SHAs.
- CI permissions are read-only and execution is bounded.
- A clean temporary environment can install the manifest and run the required
  suite.
- The full repository suite passes once after implementation and documentation.
- Only the nine approved files differ from the published baseline.
- Staging remains empty; commit and push are not performed.

## Validation

- Preflight: passed.
- Controlled focused RED: `6 failed in 0.32s`.
- Focused contract GREEN: `6 passed in 0.07s`.
- Clean-environment installation: passed; CPython `3.14.6`, pip `26.1.2`, and
  all six exact manifest entries installed successfully; `pip check` reported
  no broken requirements.
- Clean-environment focused contract: `6 passed in 0.07s`.
- Clean-environment related regression: `123 passed in 1.15s`.
- Single clean-environment full repository acceptance:
  `2683 passed, 4 skipped in 40.35s`.
- Final Git audit: passed; only the nine approved files changed,
  `git diff --check` exited `0`, and staging remained empty.

## Out Of Scope

- runtime package installation or automatic model downloads;
- `pyproject.toml`, application packaging, wheels, installers, or releases;
- optional voice dependency installation in CI;
- real microphone, TTS, provider, network, or GUI checks;
- Linux/macOS support claims or a platform matrix;
- coverage tooling or coverage thresholds;
- deployment, publishing, artifacts, signing, or secrets;
- Dependabot or automatic dependency updates;
- changes to runtime code, command routing, persistence, cognition, execution,
  workflows, providers, or voice behavior;
- TASK-127 or later work.

## Next Stage

TASK-127 - Real AI Conversation Vertical Slice. TASK-127 is not started by this
task. Staging, commit, and push require separate user verification and explicit
approval.
