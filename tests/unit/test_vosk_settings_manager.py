import json

from voice import VoskSettingsManager


def test_missing_settings_are_empty_and_do_not_create_files(tmp_path):
    settings_path = tmp_path / "config" / "local" / "vosk_settings.json"
    manager = VoskSettingsManager(settings_path)

    assert manager.load_settings() == {}
    assert manager.get_model_path() is None
    assert manager.get_language() == "ru"
    assert settings_path.parent.exists() is False


def test_model_path_and_language_persist_in_temporary_directory(tmp_path):
    settings_path = tmp_path / "config" / "local" / "vosk_settings.json"
    manager = VoskSettingsManager(settings_path)

    manager.set_model_path(r"C:\models\vosk-ru")
    manager.set_language("ru-RU")

    reloaded = VoskSettingsManager(settings_path)
    assert reloaded.get_model_path() == r"C:\models\vosk-ru"
    assert reloaded.get_language() == "ru-RU"
    assert json.loads(settings_path.read_text(encoding="utf-8")) == {
        "model_path": r"C:\models\vosk-ru",
        "language": "ru-RU",
    }


def test_quoted_model_path_is_saved_without_wrapper_quotes(tmp_path):
    settings_path = tmp_path / "config" / "local" / "vosk_settings.json"
    manager = VoskSettingsManager(settings_path)

    manager.set_model_path('"C:\\models\\vosk model small ru"')

    assert manager.get_model_path() == r"C:\models\vosk model small ru"
    assert json.loads(settings_path.read_text(encoding="utf-8"))["model_path"] == (
        r"C:\models\vosk model small ru"
    )


def test_clear_model_path_preserves_language_and_user_directory(tmp_path):
    settings_path = tmp_path / "settings" / "vosk_settings.json"
    model_directory = tmp_path / "user-model"
    model_directory.mkdir()
    manager = VoskSettingsManager(settings_path)
    manager.set_model_path(model_directory)
    manager.set_language("en")

    manager.clear_model_path()

    assert manager.load_settings() == {"language": "en"}
    assert json.loads(settings_path.read_text(encoding="utf-8")) == {
        "model_path": None,
        "language": "en",
    }
    assert model_directory.is_dir()


def test_invalid_json_is_treated_as_empty(tmp_path):
    settings_path = tmp_path / "vosk_settings.json"
    settings_path.write_text("{invalid", encoding="utf-8")

    assert VoskSettingsManager(settings_path).load_settings() == {}
