"""
JARVIS OS Base Module

Профессиональный базовый класс всех модулей системы.
Каждый модуль JARVIS OS должен наследоваться от BaseModule.
"""


from datetime import datetime


class BaseModule:
    """
    Базовый модуль JARVIS OS.

    Отвечает за:
    - паспорт модуля;
    - статус;
    - жизненный цикл;
    - зависимости;
    - разрешения;
    - получение информации о модуле.
    """

    VALID_STATUSES = {
        "created",
        "initialized",
        "running",
        "stopped",
        "unloaded",
    }

    ALLOWED_TRANSITIONS = {
        "created": {"initialized", "unloaded"},
        "initialized": {"running", "unloaded"},
        "running": {"stopped"},
        "stopped": {"running", "unloaded"},
        "unloaded": set(),
    }

    def __init__(
        self,
        module_id,
        name,
        version="0.1",
        description="",
        author="JARVIS Team",
        required_core_version="0.2",
        permissions=None,
        dependencies=None,
        supported_languages=None
    ):
        self._validate_text("module_id", module_id)
        self._validate_text("name", name)

        self.module_id = module_id
        self.name = name
        self.version = version
        self.description = description
        self.author = author
        self.required_core_version = required_core_version

        self.permissions = permissions or []
        self.dependencies = dependencies or []
        self.supported_languages = supported_languages or ["ru"]

        self.status = "created"
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at

    def initialize(self):
        self._set_status("initialized")

    def start(self):
        self._set_status("running")

    def stop(self):
        self._set_status("stopped")

    def unload(self):
        self._set_status("unloaded")

    def restart(self):
        self.stop()
        self.start()

    def _set_status(self, next_status):
        if next_status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid module status: {next_status}")

        if next_status not in self.ALLOWED_TRANSITIONS[self.status]:
            raise ValueError(
                f"Invalid status transition for {self.module_id}: "
                f"{self.status} -> {next_status}"
            )

        self.status = next_status
        self._touch()

    @staticmethod
    def _validate_text(field_name, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} must be a non-empty string")

    def _touch(self):
        self.updated_at = datetime.now().isoformat()

    def get_status(self):
        return self.status

    def get_passport(self):
        return {
            "module_id": self.module_id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "required_core_version": self.required_core_version,
            "permissions": self.permissions,
            "dependencies": self.dependencies,
            "supported_languages": self.supported_languages,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    def get_info(self):
        return self.get_passport()
