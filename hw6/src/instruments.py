# src/instruments.py
from __future__ import annotations
from typing import Any, Dict
from abc import ABC, abstractmethod

class Instrument(ABC):
    def __init__(self, symbol: str, **attrs: Any) -> None:
        if not symbol:
            raise ValueError("symbol required")
        self.symbol = symbol
        self.attrs: Dict[str, Any] = dict(attrs)

    @abstractmethod
    def get_metrics(self) -> Dict[str, Any]:
        return {"symbol": self.symbol}

class Stock(Instrument):
    def get_metrics(self) -> Dict[str, Any]:
        return {"type": "Stock", "symbol": self.symbol, **self.attrs}

class Bond(Instrument):
    def get_metrics(self) -> Dict[str, Any]:
        return {"type": "Bond", "symbol": self.symbol, **self.attrs}

class ETF(Instrument):
    def get_metrics(self) -> Dict[str, Any]:
        return {"type": "ETF", "symbol": self.symbol, **self.attrs}

__all__ = ["Instrument", "Stock", "Bond", "ETF"]