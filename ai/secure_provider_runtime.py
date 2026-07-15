"""Secure credential bridge for explicit provider runtime use."""

from __future__ import annotations

from dataclasses import dataclass, fields
from enum import Enum
import os

from security import ApiKeyManager


class ProviderCredentialSource(Enum):
    SECURE_STORE = "secure_store"
    ENVIRONMENT = "env"
    MISSING = "missing"
    UNSUPPORTED = "unsupported"
    UNAVAILABLE = "unavailable"
    LOCAL_NO_KEY = "local/no_key"


@dataclass(frozen=True)
class ProviderRuntimeCredentialStatus:
    provider: str
    supported: bool
    configured: bool
    source: str
    secure_store_available: bool
    secure_store_has_key: bool
    env_var_name: str | None
    env_has_key: bool
    can_attempt_real_request: bool
    key_preview: str
    secrets_included: bool
    network_used: bool
    error: str | None
    notes_ru: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {field.name: getattr(self, field.name) for field in fields(self)}


@dataclass(frozen=True)
class ProviderRuntimeCredential:
    provider: str
    source: str
    value: str | None
    env_var_name: str | None
    safe_to_use: bool
    secrets_included_in_repr: bool = False

    def __repr__(self) -> str:
        return (
            "ProviderRuntimeCredential("
            f"provider={self.provider!r}, source={self.source!r}, value=<redacted>, "
            f"env_var_name={self.env_var_name!r}, safe_to_use={self.safe_to_use!r}, "
            "secrets_included_in_repr=False)"
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "source": self.source,
            "value": None,
            "env_var_name": self.env_var_name,
            "safe_to_use": self.safe_to_use,
            "secrets_included_in_repr": False,
        }


class SecureProviderRuntime:
    """Resolve provider credentials without weakening explicit request gates."""

    NO_KEY_PROVIDERS = ("dry_run", "ollama")

    def __init__(self, api_key_manager: ApiKeyManager | None = None, environ=None):
        self.api_key_manager = api_key_manager or ApiKeyManager(environ=environ)
        self.environ = environ if environ is not None else os.environ

    def supported_providers(self) -> tuple[str, ...]:
        return tuple(ApiKeyManager.PROVIDERS.keys()) + self.NO_KEY_PROVIDERS

    def credential_status(self, provider: str) -> ProviderRuntimeCredentialStatus:
        normalized = self._normalize(provider)
        if normalized in self.NO_KEY_PROVIDERS:
            return ProviderRuntimeCredentialStatus(
                provider=normalized,
                supported=True,
                configured=True,
                source=ProviderCredentialSource.LOCAL_NO_KEY.value,
                secure_store_available=self._secure_store_available(),
                secure_store_has_key=False,
                env_var_name=None,
                env_has_key=False,
                can_attempt_real_request=True,
                key_preview="not_required",
                secrets_included=False,
                network_used=False,
                error=None,
                notes_ru=(
                    "Provider does not require an API key.",
                    "Status does not call providers or network.",
                    "Real/local requests remain explicit-only.",
                ),
            )

        metadata = ApiKeyManager.PROVIDERS.get(normalized)
        if metadata is None:
            return ProviderRuntimeCredentialStatus(
                provider=normalized or "unknown",
                supported=False,
                configured=False,
                source=ProviderCredentialSource.UNSUPPORTED.value,
                secure_store_available=self._secure_store_available(),
                secure_store_has_key=False,
                env_var_name=None,
                env_has_key=False,
                can_attempt_real_request=False,
                key_preview="none",
                secrets_included=False,
                network_used=False,
                error="Unsupported provider.",
                notes_ru=("Unsupported provider; no credential lookup performed.",),
            )

        secure_available = self._secure_store_available()
        secure_has_key = False
        error = None
        try:
            secure_has_key = self.api_key_manager.secure_key_store.has_secret(
                metadata.provider,
                metadata.secret_name,
            )
        except Exception as exc:
            error = self._safe_error(exc)

        env_has_key = bool(str(self.environ.get(metadata.env_var, "")).strip())
        if secure_has_key:
            source = ProviderCredentialSource.SECURE_STORE.value
        elif env_has_key:
            source = ProviderCredentialSource.ENVIRONMENT.value
        elif error and not secure_available:
            source = ProviderCredentialSource.UNAVAILABLE.value
        else:
            source = ProviderCredentialSource.MISSING.value

        return ProviderRuntimeCredentialStatus(
            provider=metadata.provider,
            supported=True,
            configured=source in {
                ProviderCredentialSource.SECURE_STORE.value,
                ProviderCredentialSource.ENVIRONMENT.value,
            },
            source=source,
            secure_store_available=secure_available,
            secure_store_has_key=secure_has_key,
            env_var_name=metadata.env_var,
            env_has_key=env_has_key,
            can_attempt_real_request=source
            in {
                ProviderCredentialSource.SECURE_STORE.value,
                ProviderCredentialSource.ENVIRONMENT.value,
            },
            key_preview="present" if source in {"secure_store", "env"} else "none",
            secrets_included=False,
            network_used=False,
            error=error,
            notes_ru=(
                "Secure store is preferred over environment variables.",
                "Status does not decrypt or print secrets.",
                "No provider call or network is used.",
                "Real requests remain explicit-only.",
            ),
        )

    def all_credential_statuses(self) -> tuple[ProviderRuntimeCredentialStatus, ...]:
        return tuple(self.credential_status(provider) for provider in self.supported_providers())

    def status_text_ru(self) -> str:
        lines = [
            "Secure provider runtime status:",
            "- secure provider runtime: yes",
            "- secure store preferred: yes",
            "- env fallback: yes",
            "- no secrets",
            "- no network",
            "- no provider call",
            "- real requests still explicit-only",
            "- AI responses not executed as commands",
            "- supported providers: " + ", ".join(self.supported_providers()),
        ]
        for status in self.all_credential_statuses():
            lines.append(self._status_line(status))
        return "\n".join(lines)

    def provider_status_text_ru(self, provider: str) -> str:
        status = self.credential_status(provider)
        return "\n".join(
            [
                "Secure provider runtime provider status:",
                "- secure provider runtime: yes",
                f"- provider: {status.provider}",
                f"- supported: {'yes' if status.supported else 'no'}",
                f"- provider configured: {'yes' if status.configured else 'no'}",
                f"- source: {status.source}",
                f"- secure store available: {'yes' if status.secure_store_available else 'no'}",
                f"- secure store has key: {'yes' if status.secure_store_has_key else 'no'}",
                "- secure store preferred: yes",
                f"- env var: {status.env_var_name or 'none'}",
                f"- env fallback: {'yes' if status.env_var_name else 'no'}",
                f"- env has key: {'yes' if status.env_has_key else 'no'}",
                f"- can attempt real request: {'yes' if status.can_attempt_real_request else 'no'}",
                "- no secrets",
                "- no network",
                "- no provider call",
                "- real requests still explicit-only",
                "- AI responses not executed as commands",
            ]
        )

    def resolve_credential(self, provider: str) -> ProviderRuntimeCredential:
        normalized = self._normalize(provider)
        if normalized in self.NO_KEY_PROVIDERS:
            return ProviderRuntimeCredential(
                provider=normalized,
                source=ProviderCredentialSource.LOCAL_NO_KEY.value,
                value=None,
                env_var_name=None,
                safe_to_use=True,
            )
        metadata = ApiKeyManager.PROVIDERS.get(normalized)
        if metadata is None:
            return ProviderRuntimeCredential(
                provider=normalized or "unknown",
                source=ProviderCredentialSource.UNSUPPORTED.value,
                value=None,
                env_var_name=None,
                safe_to_use=False,
            )
        try:
            if self.api_key_manager.secure_key_store.has_secret(
                metadata.provider,
                metadata.secret_name,
            ):
                value = self.api_key_manager.secure_key_store.get_secret(
                    metadata.provider,
                    metadata.secret_name,
                )
                if value and str(value).strip():
                    return ProviderRuntimeCredential(
                        provider=metadata.provider,
                        source=ProviderCredentialSource.SECURE_STORE.value,
                        value=str(value).strip(),
                        env_var_name=metadata.env_var,
                        safe_to_use=True,
                    )
        except Exception:
            pass
        env_value = self.environ.get(metadata.env_var)
        if env_value and str(env_value).strip():
            return ProviderRuntimeCredential(
                provider=metadata.provider,
                source=ProviderCredentialSource.ENVIRONMENT.value,
                value=str(env_value).strip(),
                env_var_name=metadata.env_var,
                safe_to_use=True,
            )
        return ProviderRuntimeCredential(
            provider=metadata.provider,
            source=ProviderCredentialSource.MISSING.value,
            value=None,
            env_var_name=metadata.env_var,
            safe_to_use=False,
        )

    def runtime_ready_for(self, provider: str) -> bool:
        return self.credential_status(provider).can_attempt_real_request

    def runtime_summary_text_ru(self) -> str:
        ready = [
            status.provider
            for status in self.all_credential_statuses()
            if status.can_attempt_real_request
        ]
        return "\n".join(
            [
                "Secure provider runtime summary:",
                "- secure provider runtime: yes",
                "- secure store preferred: yes",
                "- env fallback: yes",
                "- no secrets",
                "- no network",
                "- no provider call",
                "- explicit-only real requests",
                "- ready providers: " + (", ".join(ready) if ready else "none"),
            ]
        )

    def _secure_store_available(self) -> bool:
        try:
            return bool(self.api_key_manager.secure_key_store.status().available)
        except Exception:
            return False

    @staticmethod
    def _status_line(status: ProviderRuntimeCredentialStatus) -> str:
        return (
            f"- provider: {status.provider} | configured: "
            f"{'yes' if status.configured else 'no'} | source: {status.source} | "
            f"secure_store_available: {'yes' if status.secure_store_available else 'no'} | "
            f"secure_store_has_key: {'yes' if status.secure_store_has_key else 'no'} | "
            f"env_var: {status.env_var_name or 'none'} | "
            f"env_has_key: {'yes' if status.env_has_key else 'no'}"
        )

    @staticmethod
    def _normalize(provider: str) -> str:
        return str(provider or "").strip().lower()

    @staticmethod
    def _safe_error(exc: Exception) -> str:
        text = str(exc) or exc.__class__.__name__
        lowered = text.lower()
        if "sk-" in lowered or "key=" in lowered or "token=" in lowered:
            return "[REDACTED]"
        return text[:160]
