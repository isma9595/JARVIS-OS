# One-Shot Vosk Recognition Bridge

TASK-034 adds a safe bridge layer for a future explicit one-shot microphone capture to local Vosk recognition flow.

The bridge is implemented in `voice/one_shot_vosk_recognition_bridge.py` as `OneShotVoskRecognitionBridge`. It coordinates readiness checks, injected audio input, injected recognizer backends, and a structured Russian-first result.

## What It Does

- Checks local Vosk readiness through the existing Vosk recognition gate.
- Requires explicit one-shot intent before any capture-like step.
- Accepts injected capture providers for tests.
- Accepts injected recognizers for tests.
- Returns `allowed`, `completed`, `blocked`, `simulated`, `recognized_text`, `reasons`, `warnings`, and `safety_notes`.
- Provides a concise Russian formatter for command output.

## What It Does Not Do

- Does not start the real microphone automatically.
- Does not enable continuous listening.
- Does not create background listeners.
- Does not load a real Vosk model by default.
- Does not download or install Vosk packages or models.
- Does not send audio to the cloud.
- Does not store audio files by default.
- Does not execute recognized text as a command.

## Safety Model

The default bridge has no real capture provider and no real recognizer. If Vosk gate readiness blocks, the bridge returns a blocked result before capture is called. If the gate allows but capture or recognizer dependencies are missing, the bridge still returns a blocked result instead of crashing.

The only completed recognition path in TASK-034 is through injected test doubles.

## Why TASK-034 Does Not Enable Real Recognition

TASK-034 is a preparation step. It defines the coordinator and command surface that later work can connect to real one-shot microphone capture and local Vosk recognition after separate approval.

Real microphone-to-Vosk command execution is intentionally left for a later task, likely TASK-035.

## Commands

Manual command aliases added through `CommandProcessor`:

- `голосовой мост`
- `мост vosk`
- `тест голосового моста`
- `проверка голосового моста`
- `проверить мост распознавания`
- `мост распознавания`
- `one shot vosk`
- `one-shot vosk`

Expected result: a Russian-first bridge check that says the microphone was not started automatically, continuous listening was not used, audio was not sent to the cloud, and recognized text is not executed as a command.
