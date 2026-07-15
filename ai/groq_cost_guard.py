"""Model, prompt, and quota guard for explicit Groq one-shot requests."""

from __future__ import annotations

from dataclasses import dataclass
import os
import re


_LONG_TOKEN_RE = re.compile(r"[A-Za-z0-9_-]{32,}")


@dataclass(frozen=True)
class GroqRequestGuardConfig:
    default_model: str = "llama-3.1-8b-instant"
    model_env_var: str = "GROQ_MODEL"
    max_prompt_chars: int = 1200
    max_output_tokens: int = 128
    min_output_tokens: int = 16
    hard_max_output_tokens: int = 512
    timeout_seconds: int = 30
    show_quota_warning: bool = True


@dataclass(frozen=True)
class GroqRequestGuardResult:
    allowed: bool
    model: str
    prompt: str
    max_output_tokens: int
    safe_message: str
    warning_text: str | None = None


class GroqRequestCostGuard:
    """Validate Groq one-shot request size and model without network access."""

    def __init__(
        self,
        config: GroqRequestGuardConfig | None = None,
        environ=None,
    ):
        self.config = config or GroqRequestGuardConfig()
        self.environ = os.environ if environ is None else environ

    def guard_request(
        self,
        prompt: str,
        max_output_tokens: int | str | None = None,
        model_override: str | None = None,
    ) -> GroqRequestGuardResult:
        model = str(model_override).strip() if model_override is not None else self.resolve_model()
        model_error = self.validate_model(model)
        if model_error:
            return self._blocked(model, prompt, self.config.max_output_tokens, model_error)

        prompt_error = self.validate_prompt(prompt)
        if prompt_error:
            return self._blocked(model, prompt, self.config.max_output_tokens, prompt_error)

        token_value, token_error = self.resolve_max_output_tokens(max_output_tokens)
        if token_error:
            return self._blocked(model, prompt, self.config.max_output_tokens, token_error)

        return GroqRequestGuardResult(
            allowed=True,
            model=model,
            prompt=prompt.strip(),
            max_output_tokens=token_value,
            safe_message="Groq one-shot request passed model and quota guard.",
            warning_text=self.warning_text_ru(),
        )

    def resolve_model(self) -> str:
        if self.config.model_env_var in self.environ:
            env_value = self.environ.get(self.config.model_env_var)
            return str(env_value).strip()
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
            return "Groq model is empty."
        if len(value) > 120:
            return "Groq model name is too long."
        if any(char.isspace() for char in value):
            return "Groq model name must not contain spaces."
        if "\\" in value or ".." in value or value.startswith(("/", ".")):
            return "Groq model name must not contain path traversal."
        lowered = value.lower()
        if lowered.startswith(("sk-", "gsk_", "xai-")) or "key" in lowered:
            return "Groq model name looks like a secret and was rejected."
        if _LONG_TOKEN_RE.search(value):
            return "Groq model name looks like a token and was rejected."
        return None

    def validate_prompt(self, prompt: str) -> str | None:
        if not isinstance(prompt, str):
            return "Groq prompt must be a string."
        stripped = prompt.strip()
        if not stripped:
            return "AI prompt is empty."
        if len(stripped) > self.config.max_prompt_chars:
            return (
                "Groq prompt is too long: "
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

        if value < self.config.min_output_tokens:
            return (
                self.config.max_output_tokens,
                f"max_output_tokens must be at least {self.config.min_output_tokens}.",
            )
        if value > self.config.hard_max_output_tokens:
            return (
                self.config.max_output_tokens,
                f"max_output_tokens exceeds hard cap {self.config.hard_max_output_tokens}.",
            )
        return value, None

    def warning_text_ru(self) -> str:
        return (
            "Предупреждение: Groq free/developer limits, quota и rate limits "
            "могут отличаться по модели и аккаунту; реальный запрос может "
            "использовать квоту или rate limit. Это только one-shot запрос; "
            "ключ не печатается; ответ не выполняется как команда; память, "
            "профиль, файлы и логи автоматически не отправляются."
        )

    def status_text_ru(self) -> str:
        return "\n".join(
            [
                "Groq model/quota guard status:",
                f"- model source: {self.model_source()}",
                f"- resolved model: {self.safe_model_display()}",
                f"- default model: {self.config.default_model}",
                f"- max prompt chars: {self.config.max_prompt_chars}",
                f"- max_tokens: {self.config.max_output_tokens}",
                f"- hard max_tokens: {self.config.hard_max_output_tokens}",
                f"- timeout seconds: {self.config.timeout_seconds}",
                "- real request only via explicit one-shot typed command",
                "- key value is never printed",
                "- dry_run remains default",
                "- Groq free/developer quota and rate limits may be used",
            ]
        )

    def model_text_ru(self) -> str:
        model = self.resolve_model()
        error = self.validate_model(model)
        lines = [
            "Groq model:",
            f"- source: {self.model_source()}",
            f"- resolved model: {self.safe_model_display()}",
            "- network: not called",
            "- key value is never printed",
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
    ) -> GroqRequestGuardResult:
        return GroqRequestGuardResult(
            allowed=False,
            model=str(model or ""),
            prompt=str(prompt or ""),
            max_output_tokens=max_output_tokens,
            safe_message=message,
            warning_text=None,
        )
