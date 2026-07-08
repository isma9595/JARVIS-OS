from core.event_bus import EventBus
from core.exceptions import KernelError
from core.logger import Logger
from core.module_manager import ModuleManager


class JARVISKernel:
    ALLOWED_SERVICES = {"logger", "event_bus", "module_manager"}

    def __init__(self, version="0.2", user_profile=None):
        self.version = version
        self.user_profile = user_profile or {}
        self.logger = Logger()
        self.event_bus = EventBus()
        self.module_manager = ModuleManager()
        self.services = {
            "logger": self.logger,
            "event_bus": self.event_bus,
            "module_manager": self.module_manager,
        }
        self.state = "created"
        self.running = False

    def get_service(self, name):
        if name not in self.ALLOWED_SERVICES:
            raise KernelError(f"Неизвестный сервис ядра: {name}")

        return self.services[name]

    def start(self):
        if self.state == "running":
            raise KernelError("Ядро уже запущено")

        self.event_bus.publish("kernel.starting", {"version": self.version})

        self.logger.info(f"JARVIS OS v{self.version}")
        self.logger.info("Инициализация ядра...")
        self.logger.info("Logger: OK")
        self.logger.info("EventBus: OK")
        self.logger.info("ModuleManager: OK")

        self.state = "running"
        self.running = True
        self.event_bus.publish("kernel.started", {"version": self.version})
        self.event_bus.publish("system.started", {"version": self.version})

        self.logger.info("Система успешно запущена.")
        self.logger.info(f"Добро пожаловать, {self.get_user_display_name()}.")

    def get_user_display_name(self):
        return self.user_profile.get("preferred_name") or "Пользователь"

    def shutdown(self):
        if self.state == "stopped":
            self.logger.warning("Ядро уже остановлено.")
            return

        self.event_bus.publish("kernel.stopping", {"version": self.version})

        try:
            self.module_manager.stop_all()
        except Exception as exc:
            self.logger.error(f"Ошибка остановки модулей: {exc}")

        self.event_bus.publish("system.shutdown", {"version": self.version})
        self.state = "stopped"
        self.running = False
        self.event_bus.publish("kernel.stopped", {"version": self.version})
        self.logger.info("Система остановлена.")
