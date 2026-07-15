import json
from pathlib import Path
from uuid import uuid4

from core.time_utils import utc_now_iso_z


class IdeaManager:
    DEFAULT_STORAGE_PATH = Path("ideas") / "ideas.json"

    def __init__(self, storage_path=None):
        self.storage_path = Path(storage_path) if storage_path else self.DEFAULT_STORAGE_PATH
        self.ensure_storage()

    def ensure_storage(self):
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_path.exists():
            self._save_data({"ideas": []})

    def load_ideas(self):
        self.ensure_storage()
        with self.storage_path.open("r", encoding="utf-8") as ideas_file:
            data = json.load(ideas_file)

        ideas = data.get("ideas", [])
        if not isinstance(ideas, list):
            return []

        return ideas

    def save_ideas(self, ideas):
        self._save_data({"ideas": list(ideas)})

    def add_idea(self, title, description="", source="user_command", priority="normal"):
        normalized_title = str(title or "").strip()
        if not normalized_title:
            raise ValueError("Idea title must not be empty.")

        timestamp = self._timestamp()
        idea = {
            "id": str(uuid4()),
            "title": normalized_title,
            "description": str(description or ""),
            "source": source,
            "status": "new",
            "priority": priority,
            "created_at": timestamp,
            "updated_at": timestamp,
        }

        ideas = self.load_ideas()
        ideas.append(idea)
        self.save_ideas(ideas)
        return idea

    def list_ideas(self):
        return self.load_ideas()

    def count_ideas(self):
        return len(self.list_ideas())

    def _save_data(self, data):
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with self.storage_path.open("w", encoding="utf-8") as ideas_file:
            json.dump(data, ideas_file, ensure_ascii=False, indent=2)
            ideas_file.write("\n")

    def _timestamp(self):
        return utc_now_iso_z()
