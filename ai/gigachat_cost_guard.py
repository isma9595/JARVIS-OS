"""Model, prompt, and quota guard for explicit GigaChat one-shot requests."""

from __future__ import annotations

from dataclasses import dataclass
import os
import re


_LONG_TOKEN_RE = re.compile(r"[A-Za-z0-9_-]{32,}")


@dataclass(frozen=True)
class GigaChatRequestGuardConfig:
    default_model: str = "GigaChat"
    model_env_var: str = "GIGACHAT_MODEL"
    max_prompt_chars: int = 1200
    max_output_tokens: int = 128
    hard_max_output_tokens: int = 512
    timeout_seconds: int = 30
    show_quota_warning: bool = True


@dataclass(frozen=True)
class GigaChatRequestGuardResult:
    allowed: bool
    model: str
    prompt: str
    max_output_tokens: int
    safe_message: str
    warning_text: str | None = None


class GigaChatRequestCostGuard:
    """Validate GigaChat one-shot request size and model without network access."""

    MIN_OUTPUT_TOKENS = 16

    def __init__(
        self,
        config: GigaChatRequestGuardConfig | None = None,
        environ=None,
    ):
        self.config = config or GigaChatRequestGuardConfig()
        self.environ = os.environ if environ is None else environ

    def guard_request(
        self,
        prompt: str,
        max_output_tokens: int | str | None = None,
    ) -> GigaChatRequestGuardResult:
        model = self.resolve_model()
        model_error = self.validate_model(model)
        if model_error:
            return self._blocked(model, prompt, self.config.max_output_tokens, model_error)

        prompt_error = self.validate_prompt(prompt)
        if prompt_error:
            return self._blocked(model, prompt, self.config.max_output_tokens, prompt_error)

        token_value, token_error = self.resolve_max_output_tokens(max_output_tokens)
        if token_error:
            return self._blocked(model, prompt, self.config.max_output_tokens, token_error)

        return GigaChatRequestGuardResult(
            allowed=True,
            model=model,
            prompt=prompt.strip(),
            max_output_tokens=token_value,
            safe_message="GigaChat one-shot request passed model and quota guard.",
            warning_text=self.warning_text_ru(),
        )

    def resolve_model(self) -> str:
        if self.config.model_env_var in self.environ:
            return str(self.environ.get(self.config.model_env_var)).strip()
        return self.config.default_model

    def model_source(self) -> str:
        if self.config.model_env_var in self.environ:
            return self.config.model_env_var
        return "default"

    def safe_model_display(self) -> str:
        model = self.resolve_model()
        if self.validate_model(model):
            return "<invalid model value>"
        return model

    def validate_model(self, model: str) -> str | None:
        value = str(model or "").strip()
        if not value:
            return "GigaChat model is empty."
        if len(value) > 120:
            return "GigaChat model name is too long."
        if any(char.isspace() for char in value):
            return "GigaChat model name must not contain spaces."
        if "\\" in value or ".." in value or value.startswith(("/", ".")):
            return "GigaChat model name must not contain path traversal."
        lowered = value.lower()
        if lowered.startswith(("sk-", "gsk_", "xai-", "ya29.")) or "key" in lowered:
            return "GigaChat model name looks like a secret and was rejected."
        if _LONG_TOKEN_RE.search(value):
            return "GigaChat model name looks like a token and was rejected."
        return None

    def validate_prompt(self, prompt: str) -> str | None:
        if not isinstance(prompt, str):
            return "GigaChat prompt must be a string."
        stripped = prompt.strip()
        if not stripped:
            return "AI prompt is empty."
        if len(stripped) > self.config.max_prompt_chars:
            return (
                "GigaChat prompt is too long: "
                f"limit is {self.config.max_prompt_chars} characters."
            )
        return None

    def resolve_max_output_tokens(
        self,
        max_output_tokens: int | str | None = None,
    ) -> tuple[int, str | None]:
        if max_output_tokens is None:
            value = self.config.max_output_tokens
        else:
            try:
                value = int(max_output_tokens)
            except (TypeError, ValueError):
                return self.config.max_output_tokens, "max_output_tokens must be an integer."

        if value < self.MIN_OUTPUT_TOKENS:
            return (
                self.config.max_output_tokens,
                f"max_output_tokens must be at least {self.MIN_OUTPUT_TOKENS}.",
            )
        if value > self.config.hard_max_output_tokens:
            return (
                self.config.max_output_tokens,
                f"max_output_tokens exceeds hard cap {self.config.hard_max_output_tokens}.",
            )
        return value, None

    def warning_text_ru(self) -> str:
        return (
            "Предупреждение: GigaChat free/paid quota may apply; access token is "
            "obtained only by explicit one-shot; this is one-shot only; auth key "
            "and token are not printed; response is not executed as a command; "
            "memory, files, profile, and logs are not sent automatically."
        )

    def status_text_ru(self) -> str:
        return "\n".join(
            [
                "GigaChat model/quota guard status:",
                f"- model source: {self.model_source()}",
                f"- resolved model: {self.safe_model_display()}",
                f"- default model: {self.config.default_model}",
                f"- max prompt chars: {self.config.max_prompt_chars}",
                f"- max_tokens: {self.config.max_output_tokens}",
                f"- hard max_tokens: {self.config.hard_max_output_tokens}",
                f"- timeout seconds: {self.config.timeout_seconds}",
                "- real request only via explicit one-shot typed command",
                "- auth key and token values are never printed",
                "- dry_run remains default",
                "- GigaChat free/paid quota may be used",
            ]
        )

    def model_text_ru(self) -> str:
        model = self.resolve_model()
        error = self.validate_model(model)
        lines = [
            "GigaChat model:",
            f"- source: {self.model_source()}",
            f"- resolved model: {self.safe_model_display()}",
            "- network: not called",
            "- auth key and token values are never printed",
        ]
        if error:
            lines.append(f"- status: invalid ({error})")
        else:
            lines.append("- status: valid for one-shot guard")
        return "\n".join(lines)

    @staticmethod
    def _blocked(
        model: str,
        prompt: str,
        max_output_tokens: int,
        message: str,
    ) -> GigaChatRequestGuardResult:
        return GigaChatRequestGuardResult(
            allowed=False,
            model=str(model or ""),
            prompt=str(prompt or ""),
            max_output_tokens=max_output_tokens,
            safe_message=message,
            warning_text=None,
        )
