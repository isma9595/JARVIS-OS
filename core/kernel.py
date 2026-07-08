from core.event_bus import EventBus
from core.logger import Logger
from core.module_manager import ModuleManager


class JARVISKernel:
    def __init__(self, version="0.2"):
        self.version = version
        self.logger = Logger()
        self.event_bus = EventBus()
        self.module_manager = ModuleManager()
        self.running = False

    def start(self):
        self.logger.info(f"JARVIS OS v{self.version}")
        self.logger.info("Инициализация ядра...")
        self.logger.info("Logger: OK")
        self.logger.info("EventBus: OK")
        self.logger.info("ModuleManager: OK")

        self.running = True
        self.event_bus.publish("system.started", {"version": self.version})

        self.logger.info("Система успешно запущена.")
        self.logger.info("Добро пожаловать, Исмаил.")

    def shutdown(self):
        if not self.running:
            self.logger.warning("Система уже остановлена.")
            return

        self.event_bus.publish("system.shutdown", {"version": self.version})
        self.running = False
        self.logger.info("Система остановлена.")
