from __future__ import annotations

import heapq
from dataclasses import dataclass
from typing import Dict, List, Tuple

from .orders import Order, Side


@dataclass
class BookLevel:
    price: float
    order_ids: List[int]


class OrderBook:
    """
    Very simple limit order book.
    - Bids: max-heap by price, then FIFO by insertion.
    - Asks: min-heap by price, then FIFO by insertion.
    - Maintains mapping from order_id -> Order.
    """

    def __init__(self):
        # Heaps store (price_for_heap, seq, price) -> we look up order_ids by price
        self._bids_heap: List[Tuple[float, int, float]] = []
        self._asks_heap: List[Tuple[float, int, float]] = []
        self._price_to_orders: Dict[float, List[int]] = {}
        self._orders: Dict[int, Order] = {}
        self._seq_counter = 0

    def add_order(self, order: Order) -> None:
        self._orders[order.order_id] = order
        price = order.price
        if price is None:
            raise ValueError("Limit orders must have a price in OrderBook")

        if price not in self._price_to_orders:
            self._price_to_orders[price] = []

            if order.side == Side.BUY:
                heapq.heappush(self._bids_heap, (-price, self._seq_counter, price))
            else:
                heapq.heappush(self._asks_heap, (price, self._seq_counter, price))

            self._seq_counter += 1

        self._price_to_orders[price].append(order.order_id)

    def cancel_order(self, order_id: int) -> None:
        if order_id not in self._orders:
            return
        order = self._orders[order_id]
        price = order.price
        if price in self._price_to_orders:
            lst = self._price_to_orders[price]
            if order_id in lst:
                lst.remove(order_id)
                if not lst:
                    del self._price_to_orders[price]
        del self._orders[order_id]

    def modify_order(self, order_id: int, new_qty: float | None = None,
                     new_price: float | None = None) -> None:
        if order_id not in self._orders:
            return
        order = self._orders[order_id]

        if new_qty is not None:
            order.quantity = new_qty

        if new_price is not None and new_price != order.price:
            old_price = order.price
            if old_price in self._price_to_orders:
                lst = self._price_to_orders[old_price]
                if order_id in lst:
                    lst.remove(order_id)
                    if not lst:
                        del self._price_to_orders[old_price]

            order.price = new_price
            self.add_order(order)

    def _best_bid_price(self) -> float | None:
        while self._bids_heap:
            _, _, price = self._bids_heap[0]
            if price in self._price_to_orders and self._price_to_orders[price]:
                return price
            heapq.heappop(self._bids_heap)
        return None

    def _best_ask_price(self) -> float | None:
        while self._asks_heap:
            _, _, price = self._asks_heap[0]
            if price in self._price_to_orders and self._price_to_orders[price]:
                return price
            heapq.heappop(self._asks_heap)
        return None

    def match_market_order(self, incoming: Order) -> list[tuple[int, float, float]]:
        """
        Match a MARKET order against the opposite side using price-time priority.
        Returns a list of trades: (counterparty_order_id, fill_price, fill_qty).
        """

        trades: list[tuple[int, float, float]] = []

        if incoming.side == Side.BUY:
            while incoming.remaining_quantity > 0:
                best_ask = self._best_ask_price()
                if best_ask is None:
                    break
                order_ids = self._price_to_orders.get(best_ask, [])
                if not order_ids:
                    continue
                counterparty_id = order_ids[0]
                counterparty = self._orders[counterparty_id]

                available = counterparty.remaining_quantity
                if available <= 0:
                    order_ids.pop(0)
                    if not order_ids:
                        del self._price_to_orders[best_ask]
                    continue

                fill_qty = min(incoming.remaining_quantity, available)

                incoming.filled_quantity += fill_qty
                counterparty.filled_quantity += fill_qty

                trades.append((counterparty_id, best_ask, fill_qty))

                if counterparty.remaining_quantity <= 0:
                    order_ids.pop(0)
                    if not order_ids:
                        del self._price_to_orders[best_ask]

                if incoming.remaining_quantity <= 0:
                    break

        else:
            while incoming.remaining_quantity > 0:
                best_bid = self._best_bid_price()
                if best_bid is None:
                    break
                order_ids = self._price_to_orders.get(best_bid, [])
                if not order_ids:
                    continue
                counterparty_id = order_ids[0]
                counterparty = self._orders[counterparty_id]

                available = counterparty.remaining_quantity
                if available <= 0:
                    order_ids.pop(0)
                    if not order_ids:
                        del self._price_to_orders[best_bid]
                    continue

                fill_qty = min(incoming.remaining_quantity, available)

                incoming.filled_quantity += fill_qty
                counterparty.filled_quantity += fill_qty

                trades.append((counterparty_id, best_bid, fill_qty))

                if counterparty.remaining_quantity <= 0:
                    order_ids.pop(0)
                    if not order_ids:
                        del self._price_to_orders[best_bid]

                if incoming.remaining_quantity <= 0:
                    break

        return trades