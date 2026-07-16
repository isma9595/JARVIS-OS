"""Application-level language defaults and future locale extension point."""

from __future__ import annotations

from dataclasses import dataclass


DEFAULT_RUNTIME_LOCALE = "ru-RU"
DEFAULT_LANGUAGE = "ru"
DEFAULT_VOSK_LANGUAGE = "ru"


@dataclass(frozen=True)
class ApplicationLanguageSettings:
    """Stable language settings consumed by app-facing boundaries."""

    runtime_locale: str = DEFAULT_RUNTIME_LOCALE
    command_language: str = DEFAULT_LANGUAGE
    speech_recognition_language: str = DEFAULT_VOSK_LANGUAGE
    ui_language: str = DEFAULT_LANGUAGE
    assistant_response_language: str = DEFAULT_LANGUAGE


class ApplicationLanguageManager:
    """Resolve JARVIS language defaults without implementing full i18n."""

    def __init__(self, settings: ApplicationLanguageSettings | None = None):
        self.settings = settings or ApplicationLanguageSettings()

    @classmethod
    def from_profile(cls, user_profile=None):
        profile_language = ""
        if isinstance(user_profile, dict):
            profile_language = str(user_profile.get("language") or "").strip()
        if profile_language and profile_language not in {"ru", "ru-RU"}:
            return cls(
                ApplicationLanguageSettings(
                    runtime_locale=profile_language,
                    command_language=profile_language,
                    speech_recognition_language=DEFAULT_VOSK_LANGUAGE,
                    ui_language=profile_language,
                    assistant_response_language=profile_language,
                )
            )
        return cls()

    def current_settings(self) -> ApplicationLanguageSettings:
        return self.settings

    def runtime_locale(self) -> str:
        return self.settings.runtime_locale

    def speech_recognition_language(self) -> str:
        return self.settings.speech_recognition_language

    def status_dict(self) -> dict[str, str]:
        settings = self.current_settings()
        return {
            "runtime_locale": settings.runtime_locale,
            "command_language": settings.command_language,
            "speech_recognition_language": settings.speech_recognition_language,
            "ui_language": settings.ui_language,
            "assistant_response_language": settings.assistant_response_language,
        }
