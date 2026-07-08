from core.event_bus import EventBus


def on_system_started(data):
    print("Получено событие system.started")
    print("Данные:", data)


bus = EventBus()

bus.subscribe("system.started", on_system_started)

bus.publish("system.started", {
    "message": "JARVIS OS запущен",
    "version": "0.2"
})

print("События:", bus.list_events())