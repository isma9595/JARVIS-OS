import json
from pathlib import Path


class VoskSettingsManager:
    """Read and write local Vosk preferences without touching model files."""

    DEFAULT_SETTINGS_PATH = (
        Path(__file__).resolve().parents[1]
        / "config"
        / "local"
        / "vosk_settings.json"
    )
    DEFAULT_LANGUAGE = "ru"

    def __init__(self, settings_path=None):
        self.settings_path = Path(settings_path or self.DEFAULT_SETTINGS_PATH)

    def load_settings(self):
        if not self.settings_path.is_file():
            return {}

        try:
            with self.settings_path.open("r", encoding="utf-8") as settings_file:
                settings = json.load(settings_file)
        except (OSError, UnicodeError, json.JSONDecodeError):
            return {}

        if not isinstance(settings, dict):
            return {}

        result = {}
        model_path = settings.get("model_path")
        language = settings.get("language")
        if isinstance(model_path, str) and model_path.strip():
            result["model_path"] = model_path.strip()
        if isinstance(language, str) and language.strip():
            result["language"] = language.strip()
        return result

    def save_settings(self, settings):
        current = self.load_settings()
        current.update(settings)
        normalized = {
            "model_path": self._normalize_optional_text(current.get("model_path")),
            "language": (
                self._normalize_optional_text(current.get("language"))
                or self.DEFAULT_LANGUAGE
            ),
        }

        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        with self.settings_path.open("w", encoding="utf-8") as settings_file:
            json.dump(normalized, settings_file, ensure_ascii=False, indent=2)
            settings_file.write("\n")
        return dict(normalized)

    def get_model_path(self):
        return self.load_settings().get("model_path")

    def set_model_path(self, model_path):
        normalized = self._normalize_optional_text(model_path)
        return self.save_settings({"model_path": normalized})

    def clear_model_path(self):
        """Clear only the configured value; never delete a user path or directory."""
        return self.save_settings({"model_path": None})

    def get_language(self):
        return self.load_settings().get("language", self.DEFAULT_LANGUAGE)

    def set_language(self, language):
        normalized = self._normalize_optional_text(language)
        if normalized is None:
            raise ValueError("Vosk model language must not be empty")
        return self.save_settings({"language": normalized})

    @staticmethod
    def _normalize_optional_text(value):
        if value is None:
            return None
        normalized = str(value).strip()
        if len(normalized) >= 2 and normalized[0] == normalized[-1]:
            if normalized[0] in {'"', "'"}:
                normalized = normalized[1:-1].strip()
        return normalized or None
