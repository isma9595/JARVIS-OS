# Conversational Loop

TASK-076 adds the first safe conversational loop foundation for JARVIS. It lets
JARVIS classify ordinary Russian-first user text without turning that text into
automatic execution.

## Why This Layer Exists

The command system is good for exact commands and status checks. The
conversational loop is for ordinary text such as `привет`, `напиши письмо мэру`,
or `найди фильм на вечер и запусти`. It returns a safe response or plan instead
of immediately calling providers, browsers, files, audio, or OS automation.

## Relationship To CommandRegistry

Known commands are detected through `CommandRegistry` metadata. A direct command
such as `статус ai` is classified as `KNOWN_COMMAND` and shown as a command
preview. The registry also exposes the `conversation` category:

- `conversation.status`
- `conversation.capabilities`
- `conversation.preview`

Free-form dialog aliases are marked sensitive, require privacy checking in
metadata, and are not voice auto-allowed.

## Relationship To AppService

`JarvisAppService` owns the app-facing conversational methods:

- `conversational_status()`
- `conversational_status_text_ru()`
- `conversational_preview(text)`
- `conversational_preview_text_ru(text)`
- `conversational_handle(text, allow_network=False, allow_command_execution=False)`
- `conversational_handle_text_ru(text, allow_network=False, allow_command_execution=False)`
- `conversational_capabilities_text_ru()`

The AppService status cards include `Conversational loop: foundation ready/safe`.

## Relationship To AI Providers

TASK-076 does not call AI providers. AI-style questions are classified as
`AI_QUESTION` and routed to `AI_DRY_RUN_SAFE`. Real provider runtime integration
must remain an explicit future step with provider gates, privacy checks, and
clear user permission.

## Relationship To Future Browser/Search

Research-style text is classified as `RESEARCH_TASK` and routed to
`RESEARCH_PLAN`. Complex tasks that mix search and actions are routed to
`AGENT_PLAN`. TASK-076 does not open a browser, run search, or launch media.

## Relationship To Future Voice One-Shot

Only read-only conversational status and capabilities commands are voice
auto-allowlisted. Free-form dialog commands such as `диалог: <text>`,
`чат: <text>`, `jarvis: <text>`, `джарвис: <text>`, and `поговори: <text>` are
not voice auto-allowlisted. Existing voice confirmation flows remain in charge
for recognized modifying commands.

## Intent Types

- `KNOWN_COMMAND`
- `SMALL_TALK`
- `AI_QUESTION`
- `DRAFTING_TASK`
- `SIMPLE_ACTION`
- `RESEARCH_TASK`
- `COMPLEX_AGENT_TASK`
- `RISKY_ACTION`
- `UNKNOWN`

## Routes

- `COMMAND_PREVIEW`
- `COMMAND_EXECUTION_SAFE_READ_ONLY`
- `LOCAL_SMALL_TALK`
- `AI_DRY_RUN_SAFE`
- `DRAFT_PLAN`
- `SIMPLE_ACTION_PLAN`
- `RESEARCH_PLAN`
- `AGENT_PLAN`
- `RISKY_BLOCKED_OR_CONFIRMATION_REQUIRED`
- `CLARIFY`

## Safety Guarantees

- No hidden network.
- No provider calls by default.
- No command execution by default.
- No browser launch.
- No file or OS operation.
- No prompt/response storage.
- No decrypted secret access.
- No microphone or TTS start.
- AI responses are not executed as commands.
- Risky/destructive requests are blocked or marked confirmation-required.

## Commands

- `статус conversational loop`
- `статус conversation loop`
- `статус диалога jarvis`
- `статус разговорного режима`
- `conversational loop status`
- `conversational loop capabilities`
- `возможности conversational loop`
- `возможности диалога jarvis`
- `возможности разговорного режима`
- `диалог: <text>`
- `чат: <text>`
- `jarvis: <text>`
- `джарвис: <text>`
- `поговори: <text>`

## Examples

`привет` -> small talk:

`Привет, Исмаил. Я на связи. Могу принять команду, помочь с текстом или разобрать задачу.`

`напиши письмо мэру` -> drafting plan. No document is created.

`открой папку документы` -> simple action plan. No folder is opened.

`найди фильм на вечер и запусти` -> complex agent plan. Search, AI comparison,
and launch are future steps and require explicit permission/confirmation.

`покажи закон о защите прав потребителей` -> research plan. Browser/search is
future work and requires explicit network permission.

`удали все файлы` -> risky action. The loop blocks execution and marks the
request confirmation-required/risky-blocked.

## Future

- Real provider runtime integration through explicit provider gates.
- Secure-store provider keys surfaced only through safe provider settings.
- One-shot voice-to-answer with strict allowlist/confirmation boundaries.
- Browser/search agent with explicit network permission.
- File/OS automation through a safe action layer with rollback and confirmation.
