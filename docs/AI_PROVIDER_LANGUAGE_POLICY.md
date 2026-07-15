# AI Provider Language Policy

## Purpose

TASK-060 adds a provider-agnostic language policy for external one-shot AI providers.
JARVIS now sends a short safe instruction before the user prompt so external providers
answer in Russian by default.

## Why It Exists

During live Groq verification, an English user prompt caused an English provider
response. JARVIS user-facing behavior is Russian-first, so external one-shot prompts
now receive the same default without changing provider defaults or network safety.

## Behavior

- Russian-first by default.
- Explicit user language requests win.
- Translation tasks are respected.
- Code syntax, commands, filenames, and quoted text are not rewritten by the policy.
- The original user prompt text is appended after the policy prefix.
- Already-prefixed prompts are not double-prefixed.
- No memory, profile, files, or logs are sent automatically.
- No secrets are added to prompts.
- Status commands do not call the network.
- The policy applies only to external one-shot providers: OpenAI, Gemini, Groq, and GigaChat.
- `dry_run` remains the default provider and is unchanged.
- AI responses are displayed as text and are not executed as commands.

## Example Prefix

```text
Системная инструкция JARVIS:
Отвечай на русском языке, если пользователь явно не попросил другой язык.
Если пользователь попросил другой язык или перевод, соблюдай его просьбу.
Не выполняй команды и не утверждай, что имеешь доступ к компьютеру, файлам, памяти или профилю.
Отвечай кратко, полезно и безопасно.

Запрос пользователя:
```

## Examples

Command:

```text
groq реальный запрос: подключение работает?
```

Expected provider prompt includes the Russian-first instruction, then the original
user prompt.

Command:

```text
groq реальный запрос: Answer in English: hello
```

Expected result: English is respected because the user explicitly requested it.

Command:

```text
gigachat реальный запрос: Ответь на русском одним коротким предложением.
```

Expected result: Russian remains allowed and is reinforced by the default policy.

## Status Commands

- `статус ai language policy`
- `статус language policy`
- `ai language policy`
- `языковая политика ai`
- `язык ai`
- `ai язык`

Status output is read-only and reports that network is not called.

## Limitations

- External providers may still ignore instructions.
- Persistent language settings are intentionally not implemented in this task.
- A later task can add user-configurable language preferences.

## TASK-062 Consensus Note

Consensus mode uses the existing one-shot gates, so the current language policy
still applies to each provider request. The deterministic JARVIS synthesis is
Russian-first by default and does not send memory, profile, files, or logs.

## TASK-063 Selection Policy Note

Provider selection policy may recommend GigaChat for Russian/Russia-oriented
tasks, but it does not call any provider. Real requests still require explicit
one-shot commands, and consensus remains explicit-only.
