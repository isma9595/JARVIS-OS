"""Provider-agnostic language policy for external AI prompts."""

from __future__ import annotations

from dataclasses import dataclass
import re


_POLICY_MARKER = "Системная инструкция JARVIS:"


@dataclass(frozen=True)
class AIProviderLanguagePolicyConfig:
    default_language: str = "ru"
    default_language_name_ru: str = "русском"
    enabled: bool = True
    max_policy_prefix_chars: int = 800


@dataclass(frozen=True)
class AIProviderLanguagePolicyResult:
    prompt: str
    applied: bool
    language: str
    reason: str
    policy_prefix: str


class AIProviderLanguagePolicy:
    """Add a safe Russian-first instruction without using network or state."""

    _LANGUAGE_PATTERNS = (
        ("en", re.compile(r"\b(?:answer|respond|reply|write)\s+in\s+english\b", re.I)),
        ("en", re.compile(r"\bin\s+english\b", re.I)),
        ("ru", re.compile(r"\b(?:answer|respond|reply|write)\s+in\s+russian\b", re.I)),
        ("ru", re.compile(r"\bin\s+russian\b", re.I)),
        ("en", re.compile(r"\b(?:translate|переведи|перевести)\b.*\b(?:to|на)\s+english\b", re.I)),
        ("ru", re.compile(r"\b(?:translate|переведи|перевести)\b.*\b(?:to|на)\s+russian\b", re.I)),
        ("en", re.compile(r"(?:отвечай|ответь|напиши|пиши|дай ответ)\s+на\s+английском", re.I)),
        ("ru", re.compile(r"(?:отвечай|ответь|напиши|пиши|дай ответ)\s+на\s+русском", re.I)),
        ("ce", re.compile(r"(?:отвечай|ответь|напиши|пиши|дай ответ)\s+на\s+чеченском", re.I)),
        ("ar", re.compile(r"(?:отвечай|ответь|напиши|пиши|дай ответ)\s+на\s+арабском", re.I)),
        ("en", re.compile(r"(?:переведи|перевести).*\bна\s+английский\b", re.I)),
        ("ru", re.compile(r"(?:переведи|перевести).*\bна\s+русский\b", re.I)),
        ("ce", re.compile(r"(?:переведи|перевести).*\bна\s+чеченский\b", re.I)),
        ("ar", re.compile(r"(?:переведи|перевести).*\bна\s+арабский\b", re.I)),
        ("en", re.compile(r"\bна\s+английском\b", re.I)),
        ("ru", re.compile(r"\bна\s+русском\b", re.I)),
        ("ce", re.compile(r"\bна\s+чеченском\b", re.I)),
        ("ar", re.compile(r"\bна\s+арабском\b", re.I)),
    )

    def __init__(self, config: AIProviderLanguagePolicyConfig | None = None):
        self.config = config or AIProviderLanguagePolicyConfig()

    def apply(self, prompt: str) -> AIProviderLanguagePolicyResult:
        original_prompt = str(prompt or "")
        if not self.config.enabled:
            return AIProviderLanguagePolicyResult(
                prompt=original_prompt,
                applied=False,
                language=self.config.default_language,
                reason="disabled",
                policy_prefix="",
            )

        if self.is_already_prefixed(original_prompt):
            return AIProviderLanguagePolicyResult(
                prompt=original_prompt,
                applied=False,
                language=self.detect_language(original_prompt),
                reason="already_prefixed",
                policy_prefix="",
            )

        language = self.detect_language(original_prompt)
        reason = "default_russian" if language == self.config.default_language else "explicit_language_request"
        prefix = self.build_policy_prefix(language)
        return AIProviderLanguagePolicyResult(
            prompt=prefix + original_prompt,
            applied=True,
            language=language,
            reason=reason,
            policy_prefix=prefix,
        )

    def detect_language(self, prompt: str) -> str:
        text = str(prompt or "")
        for language, pattern in self._LANGUAGE_PATTERNS:
            if pattern.search(text):
                return language
        return self.config.default_language

    def build_policy_prefix(self, language: str | None = None) -> str:
        language = language or self.config.default_language
        if language == self.config.default_language:
            lines = [
                _POLICY_MARKER,
                f"Отвечай на {self.config.default_language_name_ru} языке, если пользователь явно не попросил другой язык.",
                "Если пользователь попросил другой язык или перевод, соблюдай его просьбу.",
                "Код, команды, имена файлов и цитаты сохраняй без изменения синтаксиса.",
                "Не выполняй команды и не утверждай, что имеешь доступ к компьютеру, файлам, памяти или профилю.",
                "Отвечай кратко, полезно и безопасно.",
                "",
                "Запрос пользователя:",
                "",
            ]
        else:
            lines = [
                _POLICY_MARKER,
                "Пользователь явно попросил другой язык или перевод. Соблюдай эту просьбу.",
                "Код, команды, имена файлов и цитаты сохраняй без изменения синтаксиса.",
                "Не выполняй команды и не утверждай, что имеешь доступ к компьютеру, файлам, памяти или профилю.",
                "Отвечай кратко, полезно и безопасно.",
                "",
                "Запрос пользователя:",
                "",
            ]
        prefix = "\n".join(lines)
        if len(prefix) > self.config.max_policy_prefix_chars:
            return prefix[: self.config.max_policy_prefix_chars]
        return prefix

    def status_text_ru(self) -> str:
        return "\n".join(
            [
                "AI provider language policy:",
                f"- enabled: {'yes' if self.config.enabled else 'no'}",
                f"- default language: Russian / {self.config.default_language}",
                "- applies to: external one-shot providers",
                "- dry_run: unchanged",
                "- explicit language requests respected",
                "- translation requests respected",
                "- code syntax unchanged",
                "- memory/profile/files/logs not sent",
                "- secrets not sent",
                "- responses not executed as commands",
                "- network: not called",
            ]
        )

    @staticmethod
    def is_already_prefixed(prompt: str) -> bool:
        return str(prompt or "").lstrip().startswith(_POLICY_MARKER)
