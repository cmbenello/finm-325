from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional

import pandas as pd

from .orders import Order, ExecutionReport, OrderStatus
from .order_book import OrderBook
from .orders import OrderType


@dataclass
class MatchingEngine:
    """
    Matching engine simulator.

    For this project, we keep it simple:
      - For LIMIT orders: randomly choose between:
          * resting on the book (no fill)
          * partial fill
          * full fill
      - For MARKET orders: use the OrderBook's match logic and then
        optionally trim fills to simulate partial execution.
    """

    order_book: OrderBook

    def process_order(self, order: Order, mid_price: Optional[float] = None) -> ExecutionReport:
        scenario = random.random()

        if order.order_type == OrderType.MARKET:
            trades = self.order_book.match_market_order(order)
            total_filled = sum(q for _, _, q in trades)
            avg_price = (
                sum(price * qty for _, price, qty in trades) / total_filled
                if total_filled > 0
                else (mid_price if mid_price is not None else order.price)
            )

            if total_filled == 0:
                status = OrderStatus.CANCELLED
                note = "No liquidity; cancelled"
            elif total_filled < order.quantity:
                status = OrderStatus.PARTIALLY_FILLED
                note = "Partially filled via book"
            else:
                status = OrderStatus.FILLED
                note = "Fully filled via book"

            return ExecutionReport(
                order_id=order.order_id,
                status=status,
                filled_quantity=total_filled,
                remaining_quantity=order.quantity - total_filled,
                avg_price=avg_price,
                timestamp=order.timestamp,
                note=note,
            )

        if scenario < 0.3:
            self.order_book.add_order(order)
            status = OrderStatus.NEW
            filled_qty = 0.0
            avg_price = None
            note = "Rested on book"

        elif scenario < 0.8:
            fill_fraction = random.uniform(0.1, 0.9)
            filled_qty = order.quantity * fill_fraction
            avg_price = order.price if order.price is not None else mid_price
            status = OrderStatus.PARTIALLY_FILLED
            note = "Random partial fill"

        else:
            filled_qty = order.quantity
            avg_price = order.price if order.price is not None else mid_price
            status = OrderStatus.FILLED
            note = "Random full fill"

        remaining = order.quantity - filled_qty

        return ExecutionReport(
            order_id=order.order_id,
            status=status,
            filled_quantity=filled_qty,
            remaining_quantity=remaining,
            avg_price=avg_price,
            timestamp=order.timestamp,
            note=note,
        )