"""Safe AI provider configuration primitives.

This module only describes provider readiness. It does not call providers,
validate keys against a network service, or expose secret values.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re


class AIProviderRuntimeState(str, Enum):
    DISABLED = "DISABLED"
    CONFIGURED = "CONFIGURED"
    MISSING_KEY = "MISSING_KEY"
    DRY_RUN_ONLY = "DRY_RUN_ONLY"
    ERROR = "ERROR"


class AIProviderKeyStatus(str, Enum):
    NOT_REQUIRED = "NOT_REQUIRED"
    MISSING = "MISSING"
    PRESENT = "PRESENT"
    INVALID_REFERENCE = "INVALID_REFERENCE"


_ENV_VAR_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_LONG_TOKEN_RE = re.compile(r"[A-Za-z0-9_-]{32,}")


@dataclass(frozen=True)
class AIProviderConfig:
    name: str
    provider_type: str
    enabled: bool = False
    default_model: str | None = None
    api_key_env_var: str | None = None
    safety_level: str = "external_api"
    notes: str | None = None

    def __post_init__(self):
        if not str(self.name or "").strip():
            raise ValueError("AI provider config name is required.")
        if not str(self.provider_type or "").strip():
            raise ValueError("AI provider config provider_type is required.")
        if self.api_key_env_var is not None and self.api_key_reference_error():
            raise ValueError("api_key_env_var must be an environment variable name.")

    def api_key_reference_error(self) -> str | None:
        """Return a safe validation error for env-var references only."""

        if self.api_key_env_var is None:
            return None

        value = str(self.api_key_env_var)
        stripped = value.strip()
        if not stripped:
            return "empty"
        if value != stripped:
            return "contains_whitespace"
        if " " in value:
            return "contains_space"
        if value.lower().startswith("sk-"):
            return "looks_like_secret"
        if len(value) > 80:
            return "too_long"
        if _LONG_TOKEN_RE.search(value):
            return "looks_like_token"
        if not _ENV_VAR_RE.fullmatch(value):
            return "invalid_env_var_name"
        return None


@dataclass(frozen=True)
class AIProviderConfigStatus:
    name: str
    provider_type: str
    enabled: bool
    default_model: str | None
    api_key_env_var: str | None
    key_status: AIProviderKeyStatus
    runtime_state: AIProviderRuntimeState
    safe_message: str
