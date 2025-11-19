from datetime import datetime
import json

class Logger:
    _instance = None

    def __new__(cls, path="events.json"):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.path = path
            cls._instance.events = []
        return cls._instance

    def log(self, event_type, data):
        entry = {
            "time": datetime.utcnow().isoformat(),
            "type": event_type,
            "data": data,
        }
        self.events.append(entry)
        print(f"[LOG] {event_type} → {data}")

    def save(self):
        with open(self.path, "w") as f:
            json.dump(self.events, f, indent=2)