from language.language_manager import (
    ApplicationLanguageManager,
    DEFAULT_RUNTIME_LOCALE,
    DEFAULT_VOSK_LANGUAGE,
)


def test_application_language_defaults_are_russian_first():
    manager = ApplicationLanguageManager()
    settings = manager.current_settings()

    assert DEFAULT_RUNTIME_LOCALE == "ru-RU"
    assert DEFAULT_VOSK_LANGUAGE == "ru"
    assert settings.runtime_locale == "ru-RU"
    assert settings.command_language == "ru"
    assert settings.speech_recognition_language == "ru"
    assert settings.ui_language == "ru"
    assert settings.assistant_response_language == "ru"


def test_application_language_reuses_russian_profile_default_as_ru_ru_locale():
    manager = ApplicationLanguageManager.from_profile({"language": "ru"})

    assert manager.runtime_locale() == "ru-RU"
    assert manager.speech_recognition_language() == "ru"


def test_application_language_keeps_future_non_russian_extension_point():
    manager = ApplicationLanguageManager.from_profile({"language": "en-US"})
    settings = manager.current_settings()

    assert settings.runtime_locale == "en-US"
    assert settings.command_language == "en"
    assert settings.ui_language == "en"
    assert settings.assistant_response_language == "en"
    assert settings.speech_recognition_language == "en-US"
