import json
from datetime import datetime
from pathlib import Path


class UserProfileManager:
    DEFAULT_PROFILE_PATH = Path("users") / "profiles" / "default_user.json"

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
        return self._get_value(profile, "assistant_name", "JARVIS")

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
