import json
import re
from pathlib import Path
from uuid import uuid4

from core.time_utils import utc_now_iso_z
from memory.contracts import MemoryEntrySnapshot, MemoryKind, MemoryOperationResult


class LocalMemoryManager:
    DEFAULT_STORAGE_PATH = Path("memory") / "local" / "memory.json"
    STORAGE_VERSION = "0.1"
    MAX_USER_FACT_KEY_LENGTH = 80
    MAX_USER_FACT_VALUE_LENGTH = 300
    MAX_LIST_USER_FACTS = 25
    _CONTROL_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
    _CREDENTIAL_PATTERN = re.compile(
        r"(?is)(sk-[a-z0-9_-]{8,}|api[_ -]?key\s*[:=]?\s*\S+|access[_ -]?token\s*[:=]?\s*\S+|"
        r"token\s*[:=]?\s*\S+|password\s*[:=]?\s*\S+|-----BEGIN [A-Z ]*PRIVATE KEY-----)"
    )

    def __init__(self, storage_path=None, *, create_on_init=False):
        self.storage_path = Path(storage_path) if storage_path else self.DEFAULT_STORAGE_PATH
        self.last_error_code = None
        if create_on_init:
            self.ensure_storage()

    def ensure_storage(self):
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_path.exists():
            self.save_memory({"version": self.STORAGE_VERSION, "items": []})

    def memory_file_exists(self):
        return self.storage_path.exists()

    def load_memory(self):
        if not self.storage_path.exists():
            self.last_error_code = None
            return {"version": self.STORAGE_VERSION, "items": []}
        try:
            with self.storage_path.open("r", encoding="utf-8") as memory_file:
                data = json.load(memory_file)
        except Exception:
            self.last_error_code = "memory_storage_unreadable"
            return {"version": self.STORAGE_VERSION, "items": []}
        if not isinstance(data, dict):
            self.last_error_code = "memory_storage_invalid"
            return {"version": self.STORAGE_VERSION, "items": []}

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

    def get_recent_memories(self, limit=5):
        try:
            normalized_limit = int(limit)
        except (TypeError, ValueError):
            normalized_limit = 5

        if normalized_limit < 1:
            normalized_limit = 1

        return list(reversed(self.list_memories()))[:normalized_limit]

    def has_memories(self):
        return self.count_memories() > 0

    def summarize_memory_count(self):
        return self.count_memories()

    def get_all_memory_text(self):
        return "\n".join(
            str(item.get("content", ""))
            for item in self.list_memories()
            if item.get("content")
        )

    def search_memories(self, query):
        normalized_query = str(query or "").strip().lower()
        if not normalized_query:
            return []

        return [
            item
            for item in self.list_memories()
            if self._matches_query(
                self._searchable_memory_text(item),
                normalized_query,
            )
        ]

    def _save_data(self, data):
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self.storage_path.with_name(self.storage_path.name + ".tmp")
        with temporary_path.open("w", encoding="utf-8") as memory_file:
            json.dump(data, memory_file, ensure_ascii=False, indent=2)
            memory_file.write("\n")
        temporary_path.replace(self.storage_path)

    def _timestamp(self):
        return utc_now_iso_z()

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

    def _searchable_memory_text(self, item):
        tags = item.get("tags", [])
        if not isinstance(tags, list):
            tags = []

        parts = [str(item.get("content", ""))]
        parts.extend(str(tag) for tag in tags)
        return " ".join(parts).lower()

    def remember_user_fact(self, key, value, *, language_code="ru-RU"):
        validation = self._validate_user_fact(key, value)
        if validation is not None:
            return validation
        display_key = self._display_key(key)
        normalized_key = self.normalize_user_fact_key(display_key)
        safe_value = self._display_value(value)
        timestamp = self._timestamp()
        data = self.load_memory()
        items = data["items"]
        existing = self._find_user_fact_item(items, normalized_key)
        if existing is not None:
            previous_value = str(existing.get("value", ""))
            changed = previous_value != safe_value
            if changed:
                existing["display_key"] = display_key
                existing["value"] = safe_value
                existing["updated_at"] = timestamp
                existing["language_code"] = str(language_code or "ru-RU")
                self.save_memory(data)
            return MemoryOperationResult(
                ok=True,
                action="remember",
                memory_id=str(existing.get("id", "")),
                key=display_key,
                value=safe_value,
                changed=changed,
                persisted=True,
                found=True,
                safe_message=(
                    "Память обновлена." if changed else "Это уже было сохранено в памяти."
                ),
                previous_value=previous_value if changed else None,
                entries=(self._snapshot_from_item(existing),),
            )

        memory_item = {
            "id": str(uuid4()),
            "type": MemoryKind.PERSISTENT_USER_FACT.value,
            "normalized_key": normalized_key,
            "display_key": display_key,
            "value": safe_value,
            "source": "explicit_user_command",
            "tags": ["explicit_user_memory"],
            "created_at": timestamp,
            "updated_at": timestamp,
            "language_code": str(language_code or "ru-RU"),
            "metadata": {"storage": "local_memory_manager"},
        }
        items.append(memory_item)
        self.save_memory(data)
        return MemoryOperationResult(
            ok=True,
            action="remember",
            memory_id=memory_item["id"],
            key=display_key,
            value=safe_value,
            changed=True,
            persisted=True,
            found=True,
            safe_message="Запомнил.",
            entries=(self._snapshot_from_item(memory_item),),
        )

    def recall_user_fact(self, key):
        normalized_key = self.normalize_user_fact_key(key)
        if not normalized_key:
            return MemoryOperationResult(
                ok=False,
                action="recall",
                memory_id=None,
                key=self._display_key(key),
                value=None,
                changed=False,
                persisted=False,
                found=False,
                safe_message="Нужно уточнить, что именно найти в памяти.",
                safe_error_code="empty_memory_key",
            )
        item = self._find_user_fact_item(self.load_memory()["items"], normalized_key)
        if item is None:
            return MemoryOperationResult(
                ok=True,
                action="recall",
                memory_id=None,
                key=self._display_key(key),
                value=None,
                changed=False,
                persisted=False,
                found=False,
                safe_message="В памяти нет такого факта.",
            )
        return MemoryOperationResult(
            ok=True,
            action="recall",
            memory_id=str(item.get("id", "")),
            key=str(item.get("display_key", key)),
            value=str(item.get("value", "")),
            changed=False,
            persisted=True,
            found=True,
            safe_message="Найдено в памяти.",
            entries=(self._snapshot_from_item(item),),
        )

    def list_user_facts(self, *, limit=MAX_LIST_USER_FACTS):
        try:
            bounded_limit = max(1, int(limit))
        except (TypeError, ValueError):
            bounded_limit = self.MAX_LIST_USER_FACTS
        bounded_limit = min(bounded_limit, self.MAX_LIST_USER_FACTS)
        facts = [
            item
            for item in self.load_memory()["items"]
            if item.get("type") == MemoryKind.PERSISTENT_USER_FACT.value
        ]
        facts = sorted(
            facts,
            key=lambda item: (
                str(item.get("normalized_key", "")),
                str(item.get("created_at", "")),
            ),
        )[:bounded_limit]
        entries = tuple(self._snapshot_from_item(item) for item in facts)
        return MemoryOperationResult(
            ok=True,
            action="list",
            memory_id=None,
            key=None,
            value=None,
            changed=False,
            persisted=bool(entries),
            found=bool(entries),
            safe_message="Список памяти." if entries else "В памяти пока нет сохранённых фактов.",
            entries=entries,
        )

    def forget_user_fact(self, key):
        normalized_key = self.normalize_user_fact_key(key)
        if not normalized_key:
            return MemoryOperationResult(
                ok=False,
                action="forget",
                memory_id=None,
                key=self._display_key(key),
                value=None,
                changed=False,
                persisted=False,
                found=False,
                safe_message="Нужно уточнить, какую запись удалить из памяти.",
                safe_error_code="empty_memory_key",
            )
        data = self.load_memory()
        items = data["items"]
        item = self._find_user_fact_item(items, normalized_key)
        if item is None:
            return MemoryOperationResult(
                ok=True,
                action="forget",
                memory_id=None,
                key=self._display_key(key),
                value=None,
                changed=False,
                persisted=False,
                found=False,
                safe_message="Такой записи в памяти не было.",
            )
        data["items"] = [
            candidate
            for candidate in items
            if not (
                candidate.get("type") == MemoryKind.PERSISTENT_USER_FACT.value
                and candidate.get("normalized_key") == normalized_key
            )
        ]
        self.save_memory(data)
        return MemoryOperationResult(
            ok=True,
            action="forget",
            memory_id=str(item.get("id", "")),
            key=str(item.get("display_key", key)),
            value=None,
            changed=True,
            persisted=True,
            found=True,
            safe_message="Удалил запись из памяти.",
            previous_value=str(item.get("value", "")),
        )

    def forget_all_user_facts(self):
        data = self.load_memory()
        before = len(data["items"])
        data["items"] = [
            item
            for item in data["items"]
            if item.get("type") != MemoryKind.PERSISTENT_USER_FACT.value
        ]
        removed = before - len(data["items"])
        if removed:
            self.save_memory(data)
        return MemoryOperationResult(
            ok=True,
            action="forget_all",
            memory_id=None,
            key=None,
            value=None,
            changed=removed > 0,
            persisted=removed > 0,
            found=removed > 0,
            safe_message=f"Удалено записей памяти: {removed}.",
        )

    @classmethod
    def normalize_user_fact_key(cls, key) -> str:
        text = str(key or "").strip()
        text = text.replace("ё", "е").replace("Ё", "е")
        text = " ".join(text.lower().split())
        prefixes = (
            "мой ",
            "моя ",
            "мое ",
            "моё ",
            "моем ",
            "моём ",
            "моего ",
            "мою ",
            "my ",
        )
        changed = True
        while changed:
            changed = False
            for prefix in prefixes:
                if text.startswith(prefix):
                    text = text[len(prefix) :].strip()
                    changed = True
        aliases = {
            "favorite color": "любимый цвет",
            "favourite color": "любимый цвет",
            "favorite colour": "любимый цвет",
            "favourite colour": "любимый цвет",
            "любимом цвете": "любимый цвет",
            "любимого цвета": "любимый цвет",
            "любимый цвет": "любимый цвет",
            "test word": "тестовое слово",
            "тестовом слове": "тестовое слово",
            "тестового слова": "тестовое слово",
            "city": "город",
        }
        return aliases.get(text, text)

    def _validate_user_fact(self, key, value):
        display_key = self._display_key(key)
        display_value = self._display_value(value)
        if not display_key:
            return self._validation_error("empty_memory_key", "Ключ памяти не должен быть пустым.")
        if not display_value:
            return self._validation_error("empty_memory_value", "Значение памяти не должно быть пустым.")
        if len(display_key) > self.MAX_USER_FACT_KEY_LENGTH:
            return self._validation_error("memory_key_too_long", "Ключ памяти слишком длинный.")
        if len(display_value) > self.MAX_USER_FACT_VALUE_LENGTH:
            return self._validation_error("memory_value_too_long", "Значение памяти слишком длинное.")
        if self._CONTROL_PATTERN.search(display_key) or self._CONTROL_PATTERN.search(display_value):
            return self._validation_error("memory_control_characters", "Память не сохраняет управляющие символы.")
        if "\n" in str(value or "") or "\r" in str(value or ""):
            return self._validation_error("memory_multiline_value", "Память не сохраняет многострочные значения.")
        if self._CREDENTIAL_PATTERN.search(display_value):
            return self._validation_error(
                "credential_like_memory_rejected",
                "Похоже на секрет или пароль. Такие данные нельзя хранить в разговорной памяти.",
            )
        if not self.normalize_user_fact_key(display_key):
            return self._validation_error("empty_memory_key", "Ключ памяти не должен быть пустым.")
        return None

    @staticmethod
    def _display_key(key) -> str:
        return " ".join(str(key or "").strip().split())

    @staticmethod
    def _display_value(value) -> str:
        return " ".join(str(value or "").strip().split())

    @staticmethod
    def _validation_error(code: str, message: str) -> MemoryOperationResult:
        return MemoryOperationResult(
            ok=False,
            action="validate",
            memory_id=None,
            key=None,
            value=None,
            changed=False,
            persisted=False,
            found=False,
            safe_message=message,
            safe_error_code=code,
        )

    @staticmethod
    def _find_user_fact_item(items, normalized_key):
        for item in items:
            if (
                isinstance(item, dict)
                and item.get("type") == MemoryKind.PERSISTENT_USER_FACT.value
                and item.get("normalized_key") == normalized_key
            ):
                return item
        return None

    @staticmethod
    def _snapshot_from_item(item):
        return MemoryEntrySnapshot(
            memory_id=str(item.get("id", "")),
            normalized_key=str(item.get("normalized_key", "")),
            display_key=str(item.get("display_key", item.get("normalized_key", ""))),
            value=str(item.get("value", "")),
            kind=MemoryKind.PERSISTENT_USER_FACT.value,
            created_at=str(item.get("created_at", "")),
            updated_at=str(item.get("updated_at", "")),
            persisted=True,
            language_code=str(item.get("language_code", "ru-RU")),
            metadata={"source": "explicit_user_memory"},
        )
