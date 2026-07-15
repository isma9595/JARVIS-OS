# Secure Key Storage

## Why This Exists

TASK-071 adds a secure API key storage foundation for the future JARVIS desktop
app. The goal is to support a later AI Provider Settings UI where users can add,
remove, and inspect key presence without putting secrets in command history,
logs, or git.

Environment variables are still useful for CLI/server workflows, but they are
not enough for a desktop product mode. A Windows desktop app needs a local,
user-scoped storage foundation that can survive restarts without saving API keys
as plain text.

## Design

- `security/secure_key_store.py` provides `SecureKeyStore`.
- `security/api_key_manager.py` provides `ApiKeyManager`.
- On Windows, the persistent backend uses Windows DPAPI through standard-library
  `ctypes`.
- Encrypted payloads are stored under:
  `%APPDATA%\JARVIS-OS\secure_keys.json`
- If Windows DPAPI is unavailable, persistent storage is unavailable. JARVIS
  does not fall back to plain-text persistent storage.
- Tests use `MemorySecureKeyBackend`; they do not require real DPAPI.

## Supported Providers

- `openai` -> `OPENAI_API_KEY`
- `gemini` -> `GEMINI_API_KEY`
- `groq` -> `GROQ_API_KEY`
- `gigachat` -> `GIGACHAT_AUTH_KEY`

## Commands

Status:

- `статус secure keys`
- `статус key storage`
- `статус хранилища ключей`
- `статус api keys`
- `статус api ключей`
- `статус безопасного хранилища ключей`

List:

- `список api ключей`
- `список secure keys`
- `какие ключи сохранены`
- `статус ключей ai`

Import from environment:

- `импортировать openai ключ из env`
- `импортировать gemini ключ из env`
- `импортировать groq ключ из env`
- `импортировать gigachat ключ из env`
- `сохранить openai ключ из env`
- `сохранить gemini ключ из env`
- `сохранить groq ключ из env`
- `сохранить gigachat ключ из env`

Delete:

- `удалить openai ключ`
- `удалить gemini ключ`
- `удалить groq ключ`
- `удалить gigachat ключ`
- `удалить openai ключ из хранилища`
- `удалить gemini ключ из хранилища`
- `удалить groq ключ из хранилища`
- `удалить gigachat ключ из хранилища`

Help:

- `безопасность api ключей`
- `помощь api keys`
- `помощь secure keys`

## Safety Boundaries

- Commands do not accept raw API key text.
- Import is only from existing environment variables.
- Output shows provider names, env var names, and `PRESENT`/`MISSING`.
- Masked hints use at most the last four characters.
- Decrypted values are not printed.
- No provider validation is performed.
- No network is called.
- Stored keys are not automatically used by OpenAI, Gemini, Groq, or GigaChat
  request gates yet.
- No AI Provider Settings UI is built in this task.

## Future Work

- AI Provider Settings UI.
- Secure key input field in the desktop app.
- Enable/disable providers and models.
- Provider health checks.
- Safe integration between real provider request gates and secure storage.

## AppService Contracts

TASK-073 contracts may report that secure key storage is ready, but they do not
read, decrypt, serialize, or print stored key values. Future AI Provider
Settings UI should use secure storage through an approved boundary.
