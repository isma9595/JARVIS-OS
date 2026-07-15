"""Safe API key manager built on SecureKeyStore."""

from __future__ import annotations

from dataclasses import dataclass
import os

from security.secure_key_store import SecureKeyStore


@dataclass(frozen=True)
class ProviderKeyMetadata:
    provider: str
    env_var: str
    secret_name: str = "api_key"


class ApiKeyManager:
    PROVIDERS: dict[str, ProviderKeyMetadata] = {
        "openai": ProviderKeyMetadata("openai", "OPENAI_API_KEY"),
        "gemini": ProviderKeyMetadata("gemini", "GEMINI_API_KEY"),
        "groq": ProviderKeyMetadata("groq", "GROQ_API_KEY"),
        "gigachat": ProviderKeyMetadata("gigachat", "GIGACHAT_AUTH_KEY"),
    }

    def __init__(self, secure_key_store: SecureKeyStore | None = None, environ=None):
        self.secure_key_store = secure_key_store or SecureKeyStore()
        self.environ = environ if environ is not None else os.environ

    def status_text_ru(self) -> str:
        status = self.secure_key_store.status()
        return "\n".join(
            [
                "Secure key storage status:",
                "- secure key storage foundation: yes",
                f"- backend: {status.backend_name}",
                f"- encrypted at rest: {'yes' if status.encrypted_at_rest else 'no'}",
                f"- persistent: {'yes' if status.persistent else 'no'}",
                f"- storage path: {status.storage_path or 'none'}",
                f"- safe to store: {'yes' if status.safe_to_store else 'no'}",
                "- providers supported: openai, gemini, groq, gigachat",
                "- provider real requests still use current existing behavior until future integration",
                "- no keys printed",
                "- no network",
                "- no response execution",
                f"- detail: {status.detail_ru}",
            ]
        )

    def list_text_ru(self) -> str:
        lines = [
            "Secure API keys:",
            "- no key values printed",
            "- no network",
        ]
        stored_by_provider = {record.provider: record for record in self.secure_key_store.list_records()}
        for provider, metadata in self.PROVIDERS.items():
            record = stored_by_provider.get(provider)
            stored_state = "PRESENT" if record and record.present else "MISSING"
            env_state = "PRESENT" if self.environ.get(metadata.env_var) else "MISSING"
            hint = record.masked_hint if record and record.masked_hint else "none"
            lines.append(
                f"- provider: {provider} | env: {metadata.env_var} | stored: {stored_state} | env: {env_state} | hint: {hint}"
            )
        return "\n".join(lines)

    def provider_status_text_ru(self, provider: str) -> str:
        metadata = self._metadata(provider)
        if metadata is None:
            return self._unsupported_provider_text(provider)
        stored = self.secure_key_store.has_secret(metadata.provider, metadata.secret_name)
        env_present = bool(self.environ.get(metadata.env_var))
        return "\n".join(
            [
                "API key provider status:",
                f"- provider: {metadata.provider}",
                f"- env var: {metadata.env_var}",
                f"- stored: {'PRESENT' if stored else 'MISSING'}",
                f"- env: {'PRESENT' if env_present else 'MISSING'}",
                "- no key value printed",
                "- no network",
            ]
        )

    def import_from_env(self, provider: str) -> str:
        metadata = self._metadata(provider)
        if metadata is None:
            return self._unsupported_provider_text(provider)
        value = self.environ.get(metadata.env_var)
        if not value:
            return "\n".join(
                [
                    "API key import from env:",
                    "- stored: no",
                    f"- provider: {metadata.provider}",
                    f"- env var: {metadata.env_var}",
                    "- env: MISSING",
                    "- reason: environment variable is missing",
                    "- no key value printed",
                    "- no network",
                ]
            )
        try:
            self.secure_key_store.set_secret(metadata.provider, value, metadata.secret_name)
        except Exception as exc:
            return "\n".join(
                [
                    "API key import from env:",
                    "- stored: no",
                    f"- provider: {metadata.provider}",
                    f"- env var: {metadata.env_var}",
                    "- env: PRESENT",
                    f"- reason: {self._safe_error(exc)}",
                    "- no key value printed",
                    "- no network",
                ]
            )
        return "\n".join(
            [
                "API key import from env:",
                "- stored: yes",
                f"- provider: {metadata.provider}",
                f"- env var: {metadata.env_var}",
                "- env: PRESENT",
                "- no provider validation",
                "- no key value printed",
                "- no network",
            ]
        )

    def delete_provider_key(self, provider: str) -> str:
        metadata = self._metadata(provider)
        if metadata is None:
            return self._unsupported_provider_text(provider)
        deleted = self.secure_key_store.delete_secret(metadata.provider, metadata.secret_name)
        return "\n".join(
            [
                "API key delete:",
                f"- deleted: {'yes' if deleted else 'no'}",
                f"- provider: {metadata.provider}",
                "- no key value printed",
                "- no network",
            ]
        )

    def safe_help_text_ru(self) -> str:
        return "\n".join(
            [
                "API key safety:",
                "- do not paste real API keys into chat, command text, logs, or git",
                "- commands do not accept raw key text",
                "- import keys from environment variables for now",
                "- future desktop UI will use a secure input field",
                "- stored keys are not printed",
                "- no provider validation or network request in this task",
                "- secure store is not used automatically by providers yet",
            ]
        )

    def _metadata(self, provider: str) -> ProviderKeyMetadata | None:
        return self.PROVIDERS.get(str(provider or "").strip().lower())

    def _unsupported_provider_text(self, provider: str) -> str:
        safe_provider = str(provider or "").strip().lower()[:40] or "unknown"
        return "\n".join(
            [
                "API key provider status:",
                "- supported: no",
                f"- provider: {safe_provider}",
                "- supported providers: openai, gemini, groq, gigachat",
                "- no key value printed",
                "- no network",
            ]
        )

    @staticmethod
    def _safe_error(exc: Exception) -> str:
        text = str(exc) or exc.__class__.__name__
        for marker in ("sk-", "key=", "token="):
            if marker in text.lower():
                return "[REDACTED]"
        return text[:160]
