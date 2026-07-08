from core.base_module import BaseModule
from core.module_manager import ModuleManager


manager = ModuleManager()

memory_module = BaseModule(
    module_id="memory.core.v1",
    name="Memory Module",
    version="0.1",
    description="Модуль памяти JARVIS OS",
    permissions=["memory.read", "memory.write"],
    dependencies=[]
)

manager.register(memory_module)
manager.initialize_all()
manager.start_all()

print(manager.list_modules())