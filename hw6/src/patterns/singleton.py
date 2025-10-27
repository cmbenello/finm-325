import json
from pathlib import Path

class Config:
    _instance = None  

    def __new__(cls, path: str | Path = "config.json"):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, path: str | Path = "config.json"):
        if not hasattr(self, "_initialized"):
            self._path = Path(path)
            self.reload()
            self._initialized = True  # prevent re-initialization

    def reload(self):
        self._cfg = json.loads(self._path.read_text())

    def get(self, key, default=None):
        return self._cfg.get(key, default)

    def __getitem__(self, key):
        return self._cfg[key]