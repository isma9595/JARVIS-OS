# TASK-037: First Real One-Shot Vosk Recognition

TASK-037 adds the first safe local real Vosk recognition path.

It is available only through explicit one-shot commands. JARVIS captures one
short microphone sample, recognizes it locally through Vosk when the package
and model are ready, prints the recognized text, and stops.

## Safety Model

- Microphone capture starts only after an explicit one-shot recognition command.
- Capture is bounded and runs once.
- Continuous listening is not connected.
- No background listener is started.
- Audio is not sent to the cloud.
- Audio files are not saved by default.
- Vosk and the model are not downloaded or installed automatically.
- The recognized text is displayed only; it is not executed as a JARVIS command.

## Explicit Commands

- `распознай голос один раз`
- `распознай одну голосовую команду`
- `реальное распознавание vosk`
- `запусти распознавание vosk один раз`
- `запусти голосовое распознавание один раз`
- `проверить голос через vosk`
- `тест реального vosk`
- `тест реального распознавания`

## Success

On success JARVIS reports that recognition completed, shows:

`Распознанный текст: <текст>`

Then it states that the command was not executed automatically and repeats the
safety notes.

## Block Or Failure

JARVIS blocks safely when Vosk is unavailable, the model path is missing, the
model folder does not look ready, the microphone cannot capture audio, or Vosk
recognition fails.

Blocked responses include reasons, one next step when available, and safety
notes. If speech is empty or unrecognized, the recognition attempt completes
without command execution.

In the AppService TASK-078 path, TASK-079 may conservatively normalize a known
Russian status command candidate before the existing text execution contract.
For example, `статус система` can become `статус системы`. The original
recognized text remains available, risky misspellings are not repaired, and
normalization itself performs no execution, provider calls, credential reads,
or network access.

## Difference From Bridge And Dry Run

The bridge commands remain dry/safe coordinator checks and do not start the real
microphone:

- `голосовой мост`
- `мост vosk`
- `тест голосового моста`
- `проверить мост распознавания`

The dry-run path continues to use test data only. TASK-037 is separate because
it is the first path allowed to touch the microphone, and only after an explicit
one-shot recognition command.

## Why Text Is Not Executed Yet

Recognition and command execution are separate safety stages. TASK-037 proves
bounded local recognition first. Future work must add confirmation, routing,
and policy checks before recognized text can affect the system.

## Future TASK-038 Direction

TASK-038 can connect recognized voice text to a safe command pipeline with
confirmation and policy gates. It should keep continuous listening separate
unless explicitly approved in a later task.
