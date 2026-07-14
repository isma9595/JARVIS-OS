"""Model, prompt, and quota guard for explicit Gemini one-shot requests."""

from __future__ import annotations

from dataclasses import dataclass
import os
import re


_LONG_TOKEN_RE = re.compile(r"[A-Za-z0-9_-]{32,}")


@dataclass(frozen=True)
class GeminiRequestGuardConfig:
    default_model: str = "gemini-2.5-flash-lite"
    model_env_var: str = "GEMINI_MODEL"
    max_prompt_chars: int = 1200
    max_output_tokens: int = 128
    min_output_tokens: int = 16
    hard_max_output_tokens: int = 512
    timeout_seconds: int = 30
    show_cost_warning: bool = True


@dataclass(frozen=True)
class GeminiRequestGuardResult:
    allowed: bool
    model: str
    prompt: str
    max_output_tokens: int
    safe_message: str
    warning_text: str | None = None


class GeminiRequestCostGuard:
    """Validate Gemini one-shot request size and model without network access."""

    def __init__(
        self,
        config: GeminiRequestGuardConfig | None = None,
        environ=None,
    ):
        self.config = config or GeminiRequestGuardConfig()
        self.environ = os.environ if environ is None else environ

    def guard_request(
        self,
        prompt: str,
        max_output_tokens: int | str | None = None,
    ) -> GeminiRequestGuardResult:
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

        return GeminiRequestGuardResult(
            allowed=True,
            model=model,
            prompt=prompt.strip(),
            max_output_tokens=token_value,
            safe_message="Gemini one-shot request passed model and quota guard.",
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
            return "Gemini model is empty."
        if len(value) > 100:
            return "Gemini model name is too long."
        if any(char.isspace() for char in value):
            return "Gemini model name must not contain spaces."
        if "/" in value or "\\" in value:
            return "Gemini model name must not contain path separators."
        lowered = value.lower()
        if lowered.startswith(("sk-", "aiza")) or "key" in lowered:
            return "Gemini model name looks like a secret and was rejected."
        if _LONG_TOKEN_RE.search(value):
            return "Gemini model name looks like a token and was rejected."
        return None

    def validate_prompt(self, prompt: str) -> str | None:
        if not isinstance(prompt, str):
            return "Gemini prompt must be a string."
        stripped = prompt.strip()
        if not stripped:
            return "AI prompt is empty."
        if len(stripped) > self.config.max_prompt_chars:
            return (
                "Gemini prompt is too long: "
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
            "Предупреждение: Gemini free tier может иметь limits, quota и rate limits; "
            "реальный запрос может использовать квоту/quota аккаунта. Это только one-shot "
            "запрос; ключ не печатается; ответ не выполняется как команда; память, "
            "профиль, файлы и логи автоматически не отправляются."
        )

    def status_text_ru(self) -> str:
        return "\n".join(
            [
                "Gemini model/quota guard status:",
                f"- model source: {self.model_source()}",
                f"- resolved model: {self.safe_model_display()}",
                f"- default model: {self.config.default_model}",
                f"- max prompt chars: {self.config.max_prompt_chars}",
                f"- maxOutputTokens: {self.config.max_output_tokens}",
                f"- hard maxOutputTokens: {self.config.hard_max_output_tokens}",
                f"- timeout seconds: {self.config.timeout_seconds}",
                "- real request only via explicit one-shot typed command",
                "- key value is never printed",
                "- dry_run remains default",
                "- Gemini free tier/quota may be used",
            ]
        )

    def model_text_ru(self) -> str:
        model = self.resolve_model()
        error = self.validate_model(model)
        lines = [
            "Gemini model:",
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
    ) -> GeminiRequestGuardResult:
        return GeminiRequestGuardResult(
            allowed=False,
            model=str(model or ""),
            prompt=str(prompt or ""),
            max_output_tokens=max_output_tokens,
            safe_message=message,
            warning_text=None,
        )
