import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4


class LocalMemoryManager:
    DEFAULT_STORAGE_PATH = Path("memory") / "local" / "memory.json"
    STORAGE_VERSION = "0.1"

    def __init__(self, storage_path=None):
        self.storage_path = Path(storage_path) if storage_path else self.DEFAULT_STORAGE_PATH
        self.ensure_storage()

    def ensure_storage(self):
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_path.exists():
            self.save_memory({"version": self.STORAGE_VERSION, "items": []})

    def memory_file_exists(self):
        return self.storage_path.exists()

    def load_memory(self):
        self.ensure_storage()
        with self.storage_path.open("r", encoding="utf-8") as memory_file:
            data = json.load(memory_file)

        items = data.get("items", [])
        if not isinstance(items, list):
            items = []

        return {
            "version": data.get("version") or self.STORAGE_VERSION,
            "items": items,
        }

    def save_memory(self, data):
        items = data.get("items", []) if isinstance(data, dict) else []
        if not isinstance(items, list):
            items = []

        self._save_data(
            {
                "version": self.STORAGE_VERSION,
                "items": items,
            }
        )

    def add_memory(self, content, memory_type="note", source="user_command", tags=None):
        normalized_content = str(content or "").strip()
        if not normalized_content:
            raise ValueError("Memory content must not be empty.")

        timestamp = self._timestamp()
        memory_item = {
            "id": str(uuid4()),
            "type": str(memory_type or "note"),
            "content": normalized_content,
            "source": str(source or "user_command"),
            "tags": list(tags or []),
            "created_at": timestamp,
            "updated_at": timestamp,
        }

        data = self.load_memory()
        data["items"].append(memory_item)
        self.save_memory(data)
        return memory_item

    def list_memories(self):
        return self.load_memory()["items"]

    def count_memories(self):
        return len(self.list_memories())

    def search_memories(self, query):
        normalized_query = str(query or "").strip().lower()
        if not normalized_query:
            return []

        return [
            item
            for item in self.list_memories()
            if self._matches_query(str(item.get("content", "")).lower(), normalized_query)
        ]

    def _save_data(self, data):
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with self.storage_path.open("w", encoding="utf-8") as memory_file:
            json.dump(data, memory_file, ensure_ascii=False, indent=2)
            memory_file.write("\n")

    def _timestamp(self):
        return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    def _matches_query(self, content, query):
        if query in content:
            return True

        content_words = content.split()
        query_words = query.split()
        return any(
            self._words_share_prefix(content_word, query_word)
            for query_word in query_words
            for content_word in content_words
        )

    def _words_share_prefix(self, left, right):
        if len(left) < 5 or len(right) < 5:
            return False

        prefix_length = min(6, len(left), len(right))
        return left[:prefix_length] == right[:prefix_length]
