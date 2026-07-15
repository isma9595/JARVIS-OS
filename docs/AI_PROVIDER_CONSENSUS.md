# AI Provider Consensus

TASK-062 adds an explicit-only multi-provider comparison mode for JARVIS.

## Purpose

Consensus mode lets the user ask several external AI providers the same prompt, compare the safe text answers, and receive a deterministic JARVIS synthesis.

Supported real consensus providers:

- Groq
- GigaChat
- OpenAI
- Gemini

`dry_run` is not part of real consensus. It remains the default provider for `спроси ai: <текст>`.

## Explicit Only

Consensus is never automatic. JARVIS attempts providers only after an explicit command:

- `статус ai consensus`
- `консенсус ai: сравни два варианта...`
- `спроси все ai: дай короткий ответ...`
- `сравни ответы ai: ...`
- `ai consensus: ...`
- `ai compare: ...`

Status commands do not call network.

## Safety

- Existing one-shot gates are used for every provider call.
- Missing provider keys are listed as skipped; no network call is made for them.
- Provider failures are isolated and do not stop the whole consensus.
- At least one successful provider response is required for a synthesized answer.
- If no keys are present, JARVIS returns: `Consensus request was not sent. No external provider keys are present.`
- If all attempted providers fail, JARVIS returns a safe failure summary and no synthesized answer.
- Multiple provider quotas or rate limits may be used after an explicit consensus command.
- Memory, profile, files, and logs are not sent automatically.
- Prompts and responses are not stored to disk.
- API keys, auth keys, and tokens are never printed or saved.
- Provider responses are never executed as commands.

## Synthesis

The first version uses deterministic local synthesis, not another external judge model.

When one provider succeeds, JARVIS says only one provider succeeded and presents that answer as the best available answer.

When multiple providers succeed, JARVIS summarizes:

- common points
- differences and provider-specific accents
- conflicts or uncertainties
- a concise final recommended answer

The synthesis does not add facts beyond the provider answers and does not expose chain-of-thought.

## Expected Behavior

No keys:

- no provider is attempted
- no network is called
- safe refusal is returned

One key:

- only that provider is attempted
- other providers are skipped as missing
- the single answer is presented as the best available answer

Multiple keys:

- providers are attempted in order: Groq, GigaChat, OpenAI, Gemini
- successful answers are compared
- failed providers are summarized safely

## Limitations

- Quality depends on provider responses.
- Providers may disagree.
- No hidden chain-of-thought is shown.
- A later task may add a stronger synthesis model or a local Ollama judge.

## TASK-063 Selection Policy Note

Selection policy can recommend an explicit consensus command when the prompt
asks to compare multiple AI answers. It does not call consensus automatically,
does not call providers, and does not change the explicit-only safety gate.
## TASK-064 Ollama Update

Ollama is available separately as a local-only provider. TASK-064 does not add Ollama to the default consensus provider order. Consensus remains explicit-only, and a later task may define local plus external consensus mixing.
