import json
import re
from datetime import datetime
from pathlib import Path


class UserProfileManager:
    DEFAULT_PROFILE_PATH = Path("users") / "profiles" / "default_user.json"
    DEFAULT_ASSISTANT_NAME = "JARVIS"
    MAX_ASSISTANT_NAME_LENGTH = 40
    ASSISTANT_NAME_PATTERN = re.compile(r"^[A-Za-zА-Яа-яЁё0-9 _-]+$")

    def __init__(self, profile_path=None):
        self.profile_path = Path(profile_path) if profile_path else self.DEFAULT_PROFILE_PATH

    def profile_exists(self):
        return self.profile_path.exists()

    def create_profile(
        self,
        user_name,
        preferred_name,
        assistant_name,
        language="ru",
        age=None,
        main_use_cases=None,
        communication_style="естественный, понятный, не робот",
    ):
        now = datetime.now().isoformat(timespec="seconds")
        profile = {
            "user_name": user_name,
            "preferred_name": preferred_name,
            "assistant_name": assistant_name,
            "language": language or "ru",
            "age": age,
            "main_use_cases": main_use_cases or [],
            "communication_style": communication_style,
            "created_at": now,
            "updated_at": now,
        }
        self.save_profile(profile)
        return profile

    def load_profile(self):
        with self.profile_path.open("r", encoding="utf-8") as profile_file:
            return json.load(profile_file)

    def save_profile(self, profile):
        profile_to_save = dict(profile)
        profile_to_save["updated_at"] = datetime.now().isoformat(timespec="seconds")

        if not profile_to_save.get("created_at"):
            profile_to_save["created_at"] = profile_to_save["updated_at"]

        self.profile_path.parent.mkdir(parents=True, exist_ok=True)
        with self.profile_path.open("w", encoding="utf-8") as profile_file:
            json.dump(profile_to_save, profile_file, ensure_ascii=False, indent=2)

        return profile_to_save

    def get_user_name(self, profile=None):
        return self._get_value(profile, "user_name", "Пользователь")

    def get_assistant_name(self, profile=None):
        return self._get_value(profile, "assistant_name", self.DEFAULT_ASSISTANT_NAME)

    def set_assistant_name(self, name):
        assistant_name = self.validate_assistant_name(name)
        profile = self.load_profile() if self.profile_exists() else {}
        profile["assistant_name"] = assistant_name
        return self.save_profile(profile)

    def reset_assistant_name(self):
        profile = self.load_profile() if self.profile_exists() else {}
        profile["assistant_name"] = self.DEFAULT_ASSISTANT_NAME
        return self.save_profile(profile)

    @classmethod
    def validate_assistant_name(cls, name):
        if not isinstance(name, str):
            raise ValueError("Assistant name must be a string.")

        assistant_name = name.strip()
        if not assistant_name:
            raise ValueError("Assistant name must not be empty.")
        if len(assistant_name) > cls.MAX_ASSISTANT_NAME_LENGTH:
            raise ValueError("Assistant name is too long.")
        if any(character in assistant_name for character in ("\r", "\n")):
            raise ValueError("Assistant name must be single-line.")
        if any(ord(character) < 32 or ord(character) == 127 for character in assistant_name):
            raise ValueError("Assistant name must not contain control characters.")
        if not cls.ASSISTANT_NAME_PATTERN.fullmatch(assistant_name):
            raise ValueError("Assistant name contains unsupported characters.")

        return assistant_name

    def get_language(self, profile=None):
        return self._get_value(profile, "language", "ru")

    def get_communication_style(self, profile=None):
        return self._get_value(
            profile,
            "communication_style",
            "естественный, понятный, не робот",
        )

    def _get_value(self, profile, key, default):
        source = profile if profile is not None else self.load_profile()
        return source.get(key) or default
