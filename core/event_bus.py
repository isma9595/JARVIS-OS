"""
JARVIS OS Event Bus

EventBus — внутренняя система событий.
Позволяет модулям JARVIS OS общаться друг с другом без прямой зависимости.
"""


class EventBus:
    def __init__(self):
        self.subscribers = {}

    def subscribe(self, event_name, callback):
        if event_name not in self.subscribers:
            self.subscribers[event_name] = []

        self.subscribers[event_name].append(callback)

    def publish(self, event_name, data=None):
        if event_name not in self.subscribers:
            return

        for callback in self.subscribers[event_name]:
            callback(data)

    def list_events(self):
        return list(self.subscribers.keys())