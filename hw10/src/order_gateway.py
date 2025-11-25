from __future__ import annotations

import csv
from pathlib import Path
from typing import Optional

from .orders import Order, ExecutionReport


class OrderGateway:
    """
    Gateway that logs all order lifecycle events to a CSV file.
    """

    def __init__(self, log_path: Path):
        self.log_path = log_path
        self._initialized = False

    def _ensure_header(self):
        if self._initialized:
            return
        write_header = not self.log_path.exists()
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        if write_header:
            with self.log_path.open("w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "timestamp",
                        "event_type",
                        "order_id",
                        "side",
                        "quantity",
                        "price",
                        "status",
                        "filled_quantity",
                        "remaining_quantity",
                        "avg_price",
                        "note",
                    ]
                )
        self._initialized = True

    def log(
        self,
        event_type: str,
        order: Order,
        exec_report: Optional[ExecutionReport] = None,
    ) -> None:
        self._ensure_header()
        with self.log_path.open("a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    (exec_report.timestamp if exec_report else order.timestamp).isoformat(),
                    event_type,
                    order.order_id,
                    order.side.name,
                    order.quantity,
                    order.price,
                    (exec_report.status.name if exec_report else order.status.name),
                    (exec_report.filled_quantity if exec_report else order.filled_quantity),
                    (exec_report.remaining_quantity if exec_report else order.remaining_quantity),
                    (exec_report.avg_price if exec_report else None),
                    (exec_report.note if exec_report else ""),
                ]
            )