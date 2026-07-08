"""
JARVIS OS Module Manager

Управляет регистрацией, запуском, остановкой и списком модулей.
"""


from core.base_module import BaseModule


class ModuleManager:
    def __init__(self):
        self.modules = {}

    def register(self, module):
        if not isinstance(module, BaseModule):
            raise TypeError("module must be an instance of BaseModule")

        module_id = module.module_id

        if module_id in self.modules:
            raise ValueError(f"Модуль уже зарегистрирован: {module_id}")

        self.modules[module_id] = module

    def initialize_all(self):
        for module in self.modules.values():
            module.initialize()

    def start_all(self):
        for module in self.modules.values():
            module.start()

    def stop_all(self):
        for module in self.modules.values():
            module.stop()

    def unload_all(self):
        for module in self.modules.values():
            module.unload()

    def get_module(self, module_id):
        if module_id not in self.modules:
            raise KeyError(f"Unknown module: {module_id}")

        return self.modules[module_id]

    def list_modules(self):
        return [module.get_info() for module in self.modules.values()]
