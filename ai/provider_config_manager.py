"""Offline-safe AI provider configuration manager."""

from __future__ import annotations

import os

from ai.provider_config import (
    AIProviderConfig,
    AIProviderConfigStatus,
    AIProviderKeyStatus,
    AIProviderRuntimeState,
)


class AIProviderConfigManager:
    """Describe future provider readiness without activating external APIs."""

    def __init__(self, configs: list[AIProviderConfig] | None = None, environ=None):
        self._configs = configs if configs is not None else self.default_configs()
        self._environ = os.environ if environ is None else environ

    @staticmethod
    def default_configs():
        return [
            AIProviderConfig(
                name="dry_run",
                provider_type="dry_run",
                enabled=True,
                default_model="jarvis-dry-run-v0",
                api_key_env_var=None,
                safety_level="offline_deterministic",
                notes="Offline deterministic provider. No API key required.",
            ),
            AIProviderConfig(
                name="groq",
                provider_type="groq",
                enabled=False,
                default_model="llama-3.1-8b-instant",
                api_key_env_var="GROQ_API_KEY",
                notes=(
                    "Groq API key comes from Groq Console. Disabled by default; "
                    "real requests are one-shot only."
                ),
            ),
            AIProviderConfig(
                name="gemini",
                provider_type="gemini",
                enabled=False,
                default_model="gemini-2.5-flash-lite",
                api_key_env_var="GEMINI_API_KEY",
                notes=(
                    "Gemini API key comes from Google AI Studio. Disabled by "
                    "default; real requests are one-shot only."
                ),
            ),
            AIProviderConfig(
                name="openai",
                provider_type="openai",
                enabled=False,
                default_model="openai-default",
                api_key_env_var="OPENAI_API_KEY",
                notes="Set the API key in an environment variable, never in tracked files.",
            ),
        ]

    def list_configs(self):
        return list(self._configs)

    def get_config(self, provider_name: str):
        normalized = str(provider_name or "").strip().lower()
        for config in self._configs:
            if config.name.lower() == normalized:
                return config
        return None

    def status_for(self, provider_name: str):
        config = self.get_config(provider_name)
        if config is None:
            return None
        return self._status_for_config(config)

    def statuses(self):
        return [self._status_for_config(config) for config in self._configs]

    def check_provider_key_text_ru(self, provider_name: str):
        status = self.status_for(provider_name)
        if status is None:
            return (
                f"AI provider '{provider_name}' не найден. "
                "Ключи не читаются, сеть не используется."
            )

        env_var = status.api_key_env_var or "не требуется"
        return (
            f"Проверка ключа {status.name}:\n"
            f"- Переменная окружения: {env_var}\n"
            f"- Статус ключа: {self._key_status_text_ru(status.key_status)}\n"
            f"- Значение ключа не отображается.\n"
            "- Сеть не используется, провайдер не вызывается."
        )

    def format_status_ru(self):
        lines = [
            "Статус AI конфигурации и ключей:",
            "- Активен только dry_run/offline provider.",
            "- Внешние AI-провайдеры пока не активны.",
            "- Сеть не используется.",
            "- Значения API-ключей не отображаются.",
        ]
        for status in self.statuses():
            lines.extend(self._status_lines_ru(status))
        return "\n".join(lines)

    def format_provider_list_ru(self):
        lines = [
            "Конфигурация AI провайдеров:",
            "- Это безопасный offline-слой готовности, не адаптеры внешних API.",
        ]
        for status in self.statuses():
            enabled = "включен" if status.enabled else "выключен"
            env_var = status.api_key_env_var or "не требуется"
            model = status.default_model or "не указан"
            lines.append(
                f"- {status.name}: type={status.provider_type}; {enabled}; "
                f"model={model}; env={env_var}; key={status.key_status.value}; "
                f"runtime={status.runtime_state.value}"
            )
        lines.extend(
            [
                "Локальный config/ai_providers.local.json зарезервирован для будущего и игнорируется git.",
                "Ключи должны храниться в переменных окружения, не в tracked-файлах.",
            ]
        )
        return "\n".join(lines)

    def format_key_safety_help_ru(self):
        return "\n".join(
            [
                "Безопасность AI/API ключей:",
                "- Не вставляйте ключи в код, JSON, Markdown, тесты или команды для коммита.",
                "- Не коммитьте секреты.",
                "- Используйте переменные окружения, например GROQ_API_KEY, GEMINI_API_KEY или OPENAI_API_KEY.",
                "- Локальные файлы config/ai_providers.local.json, config/secrets/ и secrets/ игнорируются git.",
                "- JARVIS показывает только имя переменной и статус PRESENT/MISSING, но не значение.",
                "- На этом этапе сеть не используется и реальные провайдеры не вызываются.",
            ]
        )

    def _status_for_config(self, config: AIProviderConfig):
        key_status = self._key_status(config)
        runtime_state = self._runtime_state(config, key_status)
        return AIProviderConfigStatus(
            name=config.name,
            provider_type=config.provider_type,
            enabled=config.enabled,
            default_model=config.default_model,
            api_key_env_var=config.api_key_env_var,
            key_status=key_status,
            runtime_state=runtime_state,
            safe_message=self._safe_message_ru(config, key_status, runtime_state),
        )

    def _key_status(self, config: AIProviderConfig):
        if config.api_key_env_var is None:
            return AIProviderKeyStatus.NOT_REQUIRED
        if config.api_key_reference_error():
            return AIProviderKeyStatus.INVALID_REFERENCE
        value = self._environ.get(config.api_key_env_var)
        if value is None or not str(value).strip():
            return AIProviderKeyStatus.MISSING
        return AIProviderKeyStatus.PRESENT

    @staticmethod
    def _runtime_state(config: AIProviderConfig, key_status: AIProviderKeyStatus):
        if config.provider_type == "dry_run":
            return AIProviderRuntimeState.DRY_RUN_ONLY
        if key_status == AIProviderKeyStatus.INVALID_REFERENCE:
            return AIProviderRuntimeState.ERROR
        if not config.enabled:
            return AIProviderRuntimeState.DISABLED
        if key_status == AIProviderKeyStatus.MISSING:
            return AIProviderRuntimeState.MISSING_KEY
        return AIProviderRuntimeState.CONFIGURED

    @classmethod
    def _safe_message_ru(
        cls,
        config: AIProviderConfig,
        key_status: AIProviderKeyStatus,
        runtime_state: AIProviderRuntimeState,
    ):
        if key_status == AIProviderKeyStatus.NOT_REQUIRED:
            key_text = "ключ не требуется"
        elif key_status == AIProviderKeyStatus.PRESENT:
            key_text = "ключ найден в переменной окружения, значение не отображается"
        elif key_status == AIProviderKeyStatus.MISSING:
            key_text = "ключ не найден"
        else:
            key_text = "ссылка на ключ небезопасна"

        enabled = "включен" if config.enabled else "выключен"
        return (
            f"{config.name}: {enabled}; {key_text}; "
            f"runtime={runtime_state.value}; сеть не используется"
        )

    @staticmethod
    def _key_status_text_ru(key_status: AIProviderKeyStatus):
        if key_status == AIProviderKeyStatus.NOT_REQUIRED:
            return "NOT_REQUIRED, ключ не требуется"
        if key_status == AIProviderKeyStatus.PRESENT:
            return "PRESENT, ключ найден в переменной окружения, значение не отображается"
        if key_status == AIProviderKeyStatus.MISSING:
            return "MISSING, переменная окружения не задана или пустая"
        return "INVALID_REFERENCE, имя переменной окружения небезопасно"

    @classmethod
    def _status_lines_ru(cls, status: AIProviderConfigStatus):
        env_var = status.api_key_env_var or "не требуется"
        model = status.default_model or "не указан"
        return [
            f"- {status.name}: {status.safe_message}",
            f"  type={status.provider_type}; model={model}; env={env_var}; key={status.key_status.value}",
        ]
