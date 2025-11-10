from __future__ import annotations

import socket
import time

from config import GATEWAY_PRICE_HOST, GATEWAY_PRICE_PORT, MESSAGE_DELIMITER, SYMBOLS
from shared_memory_utils import SharedPriceBook

_tick_count = 0
_tick_start_ts = time.time()


def _connect() -> socket.socket:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.connect((GATEWAY_PRICE_HOST, GATEWAY_PRICE_PORT))
    print(f"[OrderBook] connected to price feed at {GATEWAY_PRICE_HOST}:{GATEWAY_PRICE_PORT}")
    return s


def _process_stream(sock: socket.socket, book: SharedPriceBook) -> None:
    buf = b""
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            raise ConnectionError("gateway closed connection")
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
                text = raw.decode("utf-8")
                parts = text.split(",")
                sym = parts[0]
                price = float(parts[1])
            except Exception:
                print(f"[OrderBook] bad tick: {raw!r}")
                continue
            if sym not in book.symbol_to_idx:
                # symbol not tracked, ignore
                continue

            global _tick_count, _tick_start_ts
            _tick_count += 1
            book.update(sym, price)

            elapsed = time.time() - _tick_start_ts
            if elapsed > 0 and _tick_count % 100 == 0:
                rate = _tick_count / elapsed
                print(f"[Metrics] orderbook tick throughput: {_tick_count} ticks, {rate:.2f} ticks/sec")


def run_orderbook(shm_name: str) -> None:
    book = SharedPriceBook(SYMBOLS, name=shm_name, create=False)
    print(f"[OrderBook] attached to shared memory {book.name}")
    while True:
        try:
            with _connect() as sock:
                _process_stream(sock, book)
        except (ConnectionError, ConnectionRefusedError, OSError) as e:
            print(f"[OrderBook] connection error: {e}, retrying in 1s")
            time.sleep(1.0)


if __name__ == "__main__":
    # For manual testing, hard-code a shm name here if needed.
    # Example:
    #   python orderbook.py prices
    import sys

    if len(sys.argv) != 2:
        print("usage: python orderbook.py <shm_name>")
        raise SystemExit(1)
    run_orderbook(sys.argv[1])