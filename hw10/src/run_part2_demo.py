from pathlib import Path

import pandas as pd

from .market_data_gateway import MarketDataGateway
from .orders import Order, Side, OrderType
from .order_book import OrderBook
from .order_manager import OrderManager, OrderStatus
from .order_gateway import OrderGateway
from .matching_engine import MatchingEngine


def main():
    md_gateway = MarketDataGateway()
    order_book = OrderBook()
    om = OrderManager()
    mg = MatchingEngine(order_book=order_book)

    log_path = Path("data") / "orders_log.csv"
    gateway = OrderGateway(log_path)

    order_id = 1

    for ts, row in md_gateway:
        price = float(row["Close"])

        if order_id <= 5:
            order = Order(
                order_id=order_id,
                side=Side.BUY,
                quantity=10,
                price=price,
                timestamp=ts,
                order_type=OrderType.LIMIT,
            )

            ok, reason = om.validate_order(order)
            if not ok:
                order.status = OrderStatus.REJECTED
                er = ExecutionReport(
                    order_id=order.order_id,
                    status=order.status,
                    filled_quantity=0.0,
                    remaining_quantity=order.quantity,
                    avg_price=None,
                    timestamp=ts,
                    note=reason,
                )
                gateway.log("REJECT", order, er)
                order_id += 1
                continue

            om.record_accepted_order(order)
            er = mg.process_order(order, mid_price=price)
            if er.filled_quantity > 0 and er.avg_price is not None:
                om.apply_execution(order, er.filled_quantity, er.avg_price)

            gateway.log("NEW", order, er)
            order_id += 1

    print(f"Final cash: {om.cash:.2f}, final position: {om.position}")


if __name__ == "__main__":
    main()