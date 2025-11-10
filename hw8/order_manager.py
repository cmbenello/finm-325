from __future__ import annotations

import json
import socket
import time
from typing import Any, Dict

from config import ORDER_MANAGER_HOST, ORDER_MANAGER_PORT, MESSAGE_DELIMITER


_order_count = 0
_order_start_ts = time.time()


def log_order(order: Dict[str, Any]) -> None:
    oid = order.get("id", "?")
    side = order.get("side", "?")
    qty = order.get("qty", "?")
    symbol = order.get("symbol", "?")
    price = order.get("price", "?")
    global _order_count, _order_start_ts
    _order_count += 1
    print(f"Received Order {oid}: {side} {qty} {symbol} @ {price}")
    elapsed = time.time() - _order_start_ts
    if elapsed > 0 and _order_count % 20 == 0:
        rate = _order_count / elapsed
        print(f"[Metrics] orders received: {_order_count}, rate: {rate:.2f} orders/sec")


def handle_client(conn: socket.socket, addr) -> None:
    print(f"[OrderManager] connection from {addr}")
    buf = b""
    try:
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            buf += chunk
            while True:
                try:
                    idx = buf.index(MESSAGE_DELIMITER)
                except ValueError:
                    break
                raw = buf[:idx]
                buf = buf[idx + len(MESSAGE_DELIMITER):]
                if not raw:
                    continue
                try:
                    msg = raw.decode("utf-8")
                    order = json.loads(msg)
                except json.JSONDecodeError:
                    print(f"[OrderManager] bad payload: {raw!r}")
                    continue
                log_order(order)
    finally:
        conn.close()
        print(f"[OrderManager] closed {addr}")


def run_ordermanager() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((ORDER_MANAGER_HOST, ORDER_MANAGER_PORT))
        s.listen()
        print(f"[OrderManager] listening on {ORDER_MANAGER_HOST}:{ORDER_MANAGER_PORT}")
        while True:
            conn, addr = s.accept()
            handle_client(conn, addr)


if __name__ == "__main__":
    run_ordermanager()
