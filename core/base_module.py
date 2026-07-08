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
        self.status = "initialized"
        self._touch()

    def start(self):
        self.status = "running"
        self._touch()

    def stop(self):
        self.status = "stopped"
        self._touch()

    def unload(self):
        self.status = "unloaded"
        self._touch()

    def restart(self):
        self.stop()
        self.start()

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