# src/patterns/factory.py
import csv
from typing import Dict, Type
from src.instruments import Instrument, Stock, Bond, ETF

class InstrumentFactory:
    _map: Dict[str, Type[Instrument]] = {
        "stock": Stock, "bond": Bond, "etf": ETF
    }

    @classmethod
    def create_instrument(cls, data: dict) -> Instrument:
        t = (data.get("type") or "").lower()
        if t not in cls._map:
            raise KeyError(f"Unknown instrument type: {data.get('type')!r}")
        sym = data["symbol"]
        klass = cls._map[t]
        attrs = {k: v for k, v in data.items() if k not in {"type", "symbol"}}
        return klass(sym, **attrs)

def load_instruments_csv(path: str):
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield InstrumentFactory.create_instrument(row)