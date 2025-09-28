from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List

@dataclass(frozen=True)
class MarketDataPoint:
    timestamp: datetime
    symbol: str
    price: float


class Stategy(ABC):
    @abstractmethod
    def generate_signals(self, tick: MarketDatapoint) -> List:
        pass