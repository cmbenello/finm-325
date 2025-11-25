from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

import pandas as pd


class Side(Enum):
    BUY = auto()
    SELL = auto()


class OrderType(Enum):
    LIMIT = auto()
    MARKET = auto()


class OrderStatus(Enum):
    NEW = auto()
    PARTIALLY_FILLED = auto()
    FILLED = auto()
    CANCELLED = auto()
    REJECTED = auto()


@dataclass
class Order:
    order_id: int
    side: Side
    quantity: float
    price: Optional[float]  # None for market orders
    timestamp: pd.Timestamp
    order_type: OrderType = OrderType.LIMIT
    status: OrderStatus = OrderStatus.NEW

    filled_quantity: float = 0.0

    @property
    def remaining_quantity(self) -> float:
        return max(self.quantity - self.filled_quantity, 0.0)


@dataclass
class ExecutionReport:
    order_id: int
    status: OrderStatus
    filled_quantity: float
    remaining_quantity: float
    avg_price: Optional[float]
    timestamp: pd.Timestamp
    note: str = ""

    extra: dict = field(default_factory=dict)