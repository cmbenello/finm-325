from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import pandas as pd

from .orders import Order, Side, OrderStatus


@dataclass
class OrderManagerConfig:
    initial_capital: float = 100_000.0
    max_long_position: float = 1_000.0     # max net long quantity
    max_short_position: float = -1_000.0   # min net short
    max_orders_per_minute: int = 60


@dataclass
class OrderManager:
    config: OrderManagerConfig = field(default_factory=OrderManagerConfig)

    cash: float = field(init=False)
    position: float = field(init=False)
    _order_timestamps: List[pd.Timestamp] = field(default_factory=list, init=False)

    def __post_init__(self):
        self.cash = self.config.initial_capital
        self.position = 0.0

    def _update_orders_per_minute(self, now: pd.Timestamp) -> None:
        cutoff = now - pd.Timedelta(minutes=1)
        self._order_timestamps = [t for t in self._order_timestamps if t >= cutoff]

    def _orders_per_minute(self, now: pd.Timestamp) -> int:
        self._update_orders_per_minute(now)
        return len(self._order_timestamps)

    def _would_break_position_limits(self, order: Order) -> bool:
        delta = order.quantity if order.side == Side.BUY else -order.quantity
        new_position = self.position + delta
        if new_position > self.config.max_long_position:
            return True
        if new_position < self.config.max_short_position:
            return True
        return False

    def _has_sufficient_capital(self, order: Order) -> bool:
        if order.side == Side.SELL:
            return True  # allow shorting within position limit
        if order.price is None:
            return False  # conservative: require a price for capital check
        cost = order.price * order.quantity
        return self.cash >= cost

    def validate_order(self, order: Order) -> tuple[bool, str]:
        now = order.timestamp

        if self._orders_per_minute(now) >= self.config.max_orders_per_minute:
            return False, "Orders per minute limit exceeded"

        if self._would_break_position_limits(order):
            return False, "Position limits exceeded"

        if not self._has_sufficient_capital(order):
            return False, "Insufficient capital"

        return True, "OK"

    def record_accepted_order(self, order: Order) -> None:
        self._order_timestamps.append(order.timestamp)

    def apply_execution(self, order: Order, fill_qty: float, avg_price: float) -> None:
        if fill_qty == 0:
            return

        if order.side == Side.BUY:
            self.position += fill_qty
            self.cash -= avg_price * fill_qty
        else:
            self.position -= fill_qty
            self.cash += avg_price * fill_qty

        order.filled_quantity += fill_qty
        if order.remaining_quantity <= 0:
            order.status = OrderStatus.FILLED
        else:
            order.status = OrderStatus.PARTIALLY_FILLED