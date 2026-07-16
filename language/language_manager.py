"""Application-level language defaults and user preference boundary."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from users.user_profile import UserProfileManager


DEFAULT_RUNTIME_LOCALE = "ru-RU"
DEFAULT_LANGUAGE = "ru"
DEFAULT_VOSK_LANGUAGE = "ru"
DEFAULT_LANGUAGE_CODE = DEFAULT_RUNTIME_LOCALE


class SupportedLanguage(str, Enum):
    RU_RU = "ru-RU"
    EN_US = "en-US"


_LANGUAGE_NAMES = {
    SupportedLanguage.RU_RU.value: "Russian",
    SupportedLanguage.EN_US.value: "English",
}

_LANGUAGE_NAMES_RU = {
    SupportedLanguage.RU_RU.value: "русский",
    SupportedLanguage.EN_US.value: "английский",
}

_ALIASES = {
    "русский": SupportedLanguage.RU_RU,
    "русский язык": SupportedLanguage.RU_RU,
    "ru": SupportedLanguage.RU_RU,
    "ru-ru": SupportedLanguage.RU_RU,
    "russian": SupportedLanguage.RU_RU,
    "английский": SupportedLanguage.EN_US,
    "английский язык": SupportedLanguage.EN_US,
    "english": SupportedLanguage.EN_US,
    "en": SupportedLanguage.EN_US,
    "en-us": SupportedLanguage.EN_US,
}


@dataclass(frozen=True)
class LanguagePreferenceSnapshot:
    language_code: str
    display_name: str
    is_default: bool
    source: str
    persisted: bool
    safe_message: str

    def to_dict(self) -> dict[str, object]:
        return {
            "language_code": self.language_code,
            "display_name": self.display_name,
            "is_default": self.is_default,
            "source": self.source,
            "persisted": self.persisted,
            "safe_message": self.safe_message,
        }


@dataclass(frozen=True)
class LanguagePreferenceChange:
    language_code: str
    language_name: str
    previous_language_code: str
    changed: bool
    persisted: bool
    default_language: str
    safe_message: str

    def to_dict(self) -> dict[str, object]:
        return {
            "language_code": self.language_code,
            "language_name": self.language_name,
            "previous_language_code": self.previous_language_code,
            "changed": self.changed,
            "persisted": self.persisted,
            "default_language": self.default_language,
            "safe_message": self.safe_message,
        }


@dataclass(frozen=True)
class ApplicationLanguageSettings:
    """Stable language settings consumed by app-facing boundaries."""

    runtime_locale: str = DEFAULT_RUNTIME_LOCALE
    command_language: str = DEFAULT_LANGUAGE
    speech_recognition_language: str = DEFAULT_VOSK_LANGUAGE
    ui_language: str = DEFAULT_LANGUAGE
    assistant_response_language: str = DEFAULT_LANGUAGE


class ApplicationLanguageManager:
    """Resolve and persist the single JARVIS language preference."""

    def __init__(
        self,
        settings: ApplicationLanguageSettings | None = None,
        profile_manager: UserProfileManager | None = None,
    ):
        self.profile_manager = profile_manager
        self.settings = settings or self._settings_for_language(DEFAULT_LANGUAGE_CODE)
        self._snapshot = self._load_preference() if settings is None else self._snapshot_for(
            self.settings.runtime_locale,
            source="explicit",
            persisted=False,
            safe_message=self._message("status", self.settings.runtime_locale),
        )

    @classmethod
    def from_profile(cls, user_profile=None):
        profile_language = ""
        if isinstance(user_profile, dict):
            profile_language = str(user_profile.get("language") or "").strip()
        language = cls.normalize_language(profile_language) or SupportedLanguage.RU_RU
        return cls(cls._settings_for_language(language.value))

    @classmethod
    def from_profile_manager(cls, profile_manager: UserProfileManager):
        return cls(profile_manager=profile_manager)

    @staticmethod
    def normalize_language(value) -> SupportedLanguage | None:
        normalized = " ".join(str(value or "").strip().lower().split())
        if not normalized:
            return None
        for language in SupportedLanguage:
            if normalized == language.value.lower():
                return language
        return _ALIASES.get(normalized)

    def get_preference(self) -> LanguagePreferenceSnapshot:
        return self._snapshot

    def set_preference(self, language_code) -> LanguagePreferenceChange:
        language = self.normalize_language(language_code)
        previous = self._snapshot.language_code
        active_language = self._snapshot.language_code
        if language is None:
            return LanguagePreferenceChange(
                language_code=active_language,
                language_name=_LANGUAGE_NAMES[active_language],
                previous_language_code=previous,
                changed=False,
                persisted=self._snapshot.persisted,
                default_language=DEFAULT_LANGUAGE_CODE,
                safe_message=self._message("unsupported", active_language),
            )

        target = language.value
        changed = target != previous
        if self.profile_manager is None:
            self.settings = self._settings_for_language(target)
            self._snapshot = self._snapshot_for(
                target,
                source="runtime",
                persisted=False,
                safe_message=self._message("set", target, changed=changed),
            )
            return self._change(target, previous, changed, persisted=False)

        try:
            self.profile_manager.set_language_preference(target)
        except Exception:
            return LanguagePreferenceChange(
                language_code=previous,
                language_name=_LANGUAGE_NAMES[previous],
                previous_language_code=previous,
                changed=False,
                persisted=False,
                default_language=DEFAULT_LANGUAGE_CODE,
                safe_message=self._message("persistence_error", previous),
            )

        self.settings = self._settings_for_language(target)
        self._snapshot = self._snapshot_for(
            target,
            source="profile",
            persisted=True,
            safe_message=self._message("set", target, changed=changed),
        )
        return self._change(target, previous, changed, persisted=True)

    def reset_to_default(self) -> LanguagePreferenceChange:
        return self.set_preference(DEFAULT_LANGUAGE_CODE)

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

    def provider_language(self) -> str:
        return "en" if self._snapshot.language_code == SupportedLanguage.EN_US.value else "ru"

    @classmethod
    def _settings_for_language(cls, language_code: str) -> ApplicationLanguageSettings:
        language = cls.normalize_language(language_code) or SupportedLanguage.RU_RU
        if language == SupportedLanguage.EN_US:
            return ApplicationLanguageSettings(
                runtime_locale=SupportedLanguage.EN_US.value,
                command_language="en",
                speech_recognition_language="en-US",
                ui_language="en",
                assistant_response_language="en",
            )
        return ApplicationLanguageSettings()

    def _load_preference(self) -> LanguagePreferenceSnapshot:
        if self.profile_manager is None:
            self.settings = self._settings_for_language(DEFAULT_LANGUAGE_CODE)
            return self._snapshot_for(
                DEFAULT_LANGUAGE_CODE,
                source="default",
                persisted=False,
                safe_message=self._message("fallback", DEFAULT_LANGUAGE_CODE),
            )
        if not self.profile_manager.profile_exists():
            self.settings = self._settings_for_language(DEFAULT_LANGUAGE_CODE)
            return self._snapshot_for(
                DEFAULT_LANGUAGE_CODE,
                source="default",
                persisted=False,
                safe_message=self._message("status", DEFAULT_LANGUAGE_CODE),
            )
        try:
            raw_language = self.profile_manager.get_language_preference()
        except Exception:
            self.settings = self._settings_for_language(DEFAULT_LANGUAGE_CODE)
            return self._snapshot_for(
                DEFAULT_LANGUAGE_CODE,
                source="safe_fallback",
                persisted=False,
                safe_message=self._message("persistence_error", DEFAULT_LANGUAGE_CODE),
            )
        language = self.normalize_language(raw_language) or SupportedLanguage.RU_RU
        source = "profile" if raw_language else "default"
        persisted = bool(raw_language and language.value == raw_language)
        self.settings = self._settings_for_language(language.value)
        return self._snapshot_for(
            language.value,
            source=source,
            persisted=persisted,
            safe_message=self._message("status", language.value),
        )

    @staticmethod
    def _snapshot_for(
        language_code: str,
        *,
        source: str,
        persisted: bool,
        safe_message: str,
    ) -> LanguagePreferenceSnapshot:
        language = ApplicationLanguageManager.normalize_language(language_code) or SupportedLanguage.RU_RU
        code = language.value
        return LanguagePreferenceSnapshot(
            language_code=code,
            display_name=_LANGUAGE_NAMES[code],
            is_default=code == DEFAULT_LANGUAGE_CODE,
            source=source,
            persisted=persisted,
            safe_message=safe_message,
        )

    @staticmethod
    def _message(kind: str, language_code: str, *, changed: bool = True) -> str:
        active = ApplicationLanguageManager.normalize_language(language_code) or SupportedLanguage.RU_RU
        code = active.value
        if code == SupportedLanguage.EN_US.value:
            if kind == "unsupported":
                return "Unsupported language. The language preference was not changed."
            if kind == "persistence_error":
                return "Language preference storage is unavailable. Safe default is used."
            if kind == "fallback":
                return "Language preference is unavailable. Russian is used by default."
            if kind == "set":
                return "Language preference is already English." if not changed else "Language preference changed to English."
            return "Current language: English (en-US)."
        if kind == "unsupported":
            return "Неподдерживаемый язык. Настройка языка не изменена."
        if kind == "persistence_error":
            return "Хранилище настройки языка недоступно. Используется безопасное значение."
        if kind == "fallback":
            return "Настройка языка недоступна. По умолчанию используется русский."
        if kind == "set":
            return "Язык уже русский." if not changed else "Язык переключен на русский."
        return "Текущий язык: русский (ru-RU)."

    def _change(
        self,
        target: str,
        previous: str,
        changed: bool,
        *,
        persisted: bool,
    ) -> LanguagePreferenceChange:
        return LanguagePreferenceChange(
            language_code=target,
            language_name=_LANGUAGE_NAMES[target],
            previous_language_code=previous,
            changed=changed,
            persisted=persisted,
            default_language=DEFAULT_LANGUAGE_CODE,
            safe_message=self._message("set", target, changed=changed),
        )
