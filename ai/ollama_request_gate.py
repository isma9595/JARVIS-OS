"""Explicit request gate for local Ollama one-shot calls."""

from __future__ import annotations

from dataclasses import dataclass
import re

from ai.context_privacy_policy import AIContextPrivacyPolicy, AIContextTarget
from ai.ollama_runtime import OllamaRuntime
from ai.provider_contracts import (
    AIProviderCapability,
    AIProviderSafetyLevel,
    AIRequest,
    AIResponse,
)
from ai.provider_language_policy import AIProviderLanguagePolicy
from ai.providers.ollama_provider import OllamaProvider


@dataclass(frozen=True)
class OllamaRequestResult:
    ok: bool
    model: str
    answer: str
    safe_error: str | None
    network_scope: str = "localhost-only"


class OllamaRequestGate:
    MAX_PROMPT_CHARS = 4000
    _MODEL_RE = re.compile(r"^[A-Za-z0-9:._/-]{1,120}$")
    _KEY_LOOKING_RE = re.compile(r"(?i)(sk-|gsk_|api[_-]?key|token|bearer)")

    def __init__(
        self,
        runtime: OllamaRuntime | None = None,
        provider_factory=None,
        language_policy: AIProviderLanguagePolicy | None = None,
        context_privacy_policy: AIContextPrivacyPolicy | None = None,
    ):
        self.runtime = runtime or OllamaRuntime()
        self.provider_factory = provider_factory or OllamaProvider
        self.language_policy = language_policy or AIProviderLanguagePolicy()
        self.context_privacy_policy = context_privacy_policy or AIContextPrivacyPolicy()

    def status_text(self) -> str:
        status = self.runtime.status(check_models=False)
        return "\n".join(
            [
                "Ollama local provider status:",
                "- provider: ollama",
                "- local only: yes",
                f"- base URL: {status.base_url}",
                "- env var: OLLAMA_MODEL",
                f"- model: {self.runtime.config.model}",
                "- key: not required",
                "- cloud: not used",
                "- dry_run remains default",
                "- explicit one-shot only",
                "- network: not called",
                "- memory/profile/files/logs not sent",
                "- responses not executed as commands",
            ]
        )

    def guard_text(self) -> str:
        return "\n".join(
            [
                "Ollama request guard:",
                f"- max prompt chars: {self.MAX_PROMPT_CHARS}",
                "- model override: validated locally before any network call",
                "- allowed model chars: letters, digits, colon, dot, hyphen, underscore, slash",
                "- no API key is required",
                "- network scope: localhost-only",
                "- no automatic install or model pull",
            ]
        )

    def model_text(self) -> str:
        return "\n".join(
            [
                "Ollama model configuration:",
                f"- configured model: {self.runtime.config.model}",
                f"- default model: {OllamaRuntime.DEFAULT_MODEL}",
                "- override: set OLLAMA_MODEL outside JARVIS",
                "- network: not called",
                "- availability: run explicit model-list command",
                "- no model is pulled or downloaded automatically",
            ]
        )

    def runtime_status_text(self) -> str:
        status = self.runtime.status(check_models=True)
        lines = [
            "Ollama local runtime check:",
            "- provider: ollama",
            "- network: localhost-only /api/tags",
            f"- base URL: {status.base_url}",
            f"- model: {status.model}",
            f"- server reachable: {status.server_reachable}",
            f"- model installed: {status.model_installed}",
            f"- status: {status.safe_message}",
        ]
        if status.installed_models:
            lines.append("- installed models:")
            lines.extend(f"  - {name}" for name in status.installed_models)
        else:
            lines.append("- installed models: none reported")
        lines.extend(self._safety_footer_lines(request_completed=False))
        return "\n".join(lines)

    def list_models_text(self) -> str:
        ok, models, error = self.runtime.list_models()
        lines = [
            "Ollama local model list:",
            "- provider: ollama",
            "- network: localhost-only /api/tags",
            f"- base URL: {self.runtime.status(check_models=False).base_url}",
        ]
        if not ok:
            lines.append(f"- status: {error or 'Ollama localhost server is unavailable.'}")
        elif models:
            lines.append("- installed models:")
            lines.extend(f"  - {model}" for model in models)
        else:
            lines.append("- installed models: none reported")
        lines.extend(
            [
                "- no model was pulled or downloaded",
                "- no cloud endpoint was called",
                "- no secrets are used",
            ]
        )
        return "\n".join(lines)

    def one_shot(self, prompt: str, model_override: str | None = None) -> OllamaRequestResult:
        validation_error = self._validate_prompt(prompt)
        if validation_error:
            return OllamaRequestResult(False, self.runtime.config.model, "", validation_error)
        privacy_decision = self.context_privacy_policy.decide(
            prompt,
            AIContextTarget.LOCAL_OLLAMA,
        )
        if not privacy_decision.allowed:
            return OllamaRequestResult(
                False,
                self.runtime.config.model,
                "",
                self.context_privacy_policy.format_refusal(
                    prompt,
                    AIContextTarget.LOCAL_OLLAMA,
                ),
            )
        model = model_override or self.runtime.config.model
        model_error = self.validate_model(model)
        if model_error:
            return OllamaRequestResult(False, self.runtime.config.model, "", model_error)

        status = self.runtime.status(check_models=True)
        if not status.server_reachable:
            return OllamaRequestResult(
                False,
                model,
                "",
                status.safe_message or "Ollama localhost server is unavailable.",
            )
        if model not in status.installed_models:
            return OllamaRequestResult(
                False,
                model,
                "",
                (
                    f"Ollama model '{model}' is not installed locally. "
                    "Install or pull it manually outside JARVIS, then retry."
                ),
            )

        language_result = self.language_policy.apply(prompt)
        provider = self.provider_factory(
            runtime=self.runtime,
            enabled=True,
            model=model,
        )
        response = provider.generate(
            AIRequest(
                prompt=language_result.prompt,
                task_type=AIProviderCapability.CHAT.value,
                language=language_result.language,
            )
        )
        if response.is_error:
            return OllamaRequestResult(
                False,
                model,
                "",
                response.error_message or response.text or "Ollama request failed safely.",
            )
        return OllamaRequestResult(True, model, response.text, None)

    def generate_one_shot(
        self,
        request: AIRequest,
        capability: AIProviderCapability = AIProviderCapability.CHAT,
        model_override: str | None = None,
    ) -> AIResponse:
        validation_error = request.validation_error()
        if validation_error:
            return self._error_response(capability, validation_error)
        result = self.one_shot(request.prompt, model_override=model_override)
        if not result.ok:
            return self._error_response(
                capability,
                result.safe_error or "Ollama request failed safely.",
                model=result.model,
            )
        return AIResponse(
            text=result.answer,
            provider_name="ollama",
            model_name=result.model,
            capability=capability.value,
            safety_level=AIProviderSafetyLevel.LOCAL_ONLY.value,
        )

    def validate_model(self, model: str) -> str | None:
        text = str(model or "").strip()
        if not text:
            return "Ollama model name is empty."
        if len(text) > 120:
            return "Ollama model name is too long."
        if " " in text or "\\" in text:
            return "Ollama model name contains unsafe characters."
        if ".." in text.split("/"):
            return "Ollama model name must not contain path traversal."
        if self._KEY_LOOKING_RE.search(text):
            return "Ollama model name looks like a secret or token."
        if not self._MODEL_RE.fullmatch(text):
            return "Ollama model name contains unsupported characters."
        return None

    def _validate_prompt(self, prompt: str) -> str | None:
        if not isinstance(prompt, str) or not prompt.strip():
            return "Ollama prompt is empty."
        if len(prompt.strip()) > self.MAX_PROMPT_CHARS:
            return f"Ollama prompt is too long; max {self.MAX_PROMPT_CHARS} chars."
        return None

    def _error_response(
        self,
        capability: AIProviderCapability,
        message: str,
        model: str | None = None,
    ) -> AIResponse:
        return AIResponse(
            text=message,
            provider_name="ollama_request_gate",
            model_name=model or self.runtime.config.model,
            capability=capability.value,
            safety_level=AIProviderSafetyLevel.LOCAL_ONLY.value,
            is_error=True,
            error_message=message,
        )

    @staticmethod
    def _safety_footer_lines(request_completed: bool = True) -> list[str]:
        return [
            "- request completed" if request_completed else "- real chat request was not sent",
            "- dry_run remains default",
            "- network scope: localhost-only",
            "- cloud: not used",
            "- key/token: not required",
            "- memory/profile/files/logs not sent",
            "- response was not executed as a command",
        ]
