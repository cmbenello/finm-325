from __future__ import annotations

import json
import math
import socket
import threading
import time
from collections import deque
from typing import Deque, Dict, Optional

from config import (
    SYMBOLS,
    MESSAGE_DELIMITER,
    GATEWAY_NEWS_HOST,
    GATEWAY_NEWS_PORT,
    ORDER_MANAGER_HOST,
    ORDER_MANAGER_PORT,
)
from shared_memory_utils import SharedPriceBook

# simple shared state for news sentiment
_last_sentiment: int = 50
_sent_lock = threading.Lock()


def _set_sentiment(value: int) -> None:
    global _last_sentiment
    with _sent_lock:
        _last_sentiment = value


def _get_sentiment() -> int:
    with _sent_lock:
        return _last_sentiment


def _connect_news() -> socket.socket:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.connect((GATEWAY_NEWS_HOST, GATEWAY_NEWS_PORT))
    print(f"[Strategy] connected to news at {GATEWAY_NEWS_HOST}:{GATEWAY_NEWS_PORT}")
    return s


def _news_loop() -> None:
    while True:
        try:
            with _connect_news() as sock:
                buf = b""
                while True:
                    chunk = sock.recv(4096)
                    if not chunk:
                        raise ConnectionError("news closed")
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
                            val = int(raw.decode("utf-8"))
                        except ValueError:
                            print(f"[Strategy] bad sentiment: {raw!r}")
                            continue
                        _set_sentiment(val)
        except (ConnectionError, ConnectionRefusedError, OSError) as e:
            print(f"[Strategy] news error: {e}, retrying in 1s")
            time.sleep(1.0)


def _connect_ordermanager() -> socket.socket:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.connect((ORDER_MANAGER_HOST, ORDER_MANAGER_PORT))
    print(f"[Strategy] connected to OrderManager at {ORDER_MANAGER_HOST}:{ORDER_MANAGER_PORT}")
    return s


def _moving_average(buf: Deque[float]) -> Optional[float]:
    if not buf:
        return None
    return sum(buf) / len(buf)


def run_strategy(shm_name: str) -> None:
    primary_symbol = SYMBOLS[0]
    short_window = 5
    long_window = 20
    bullish_th = 60
    bearish_th = 40
    qty = 10

    price_hist: Deque[float] = deque(maxlen=long_window)
    position: str = "FLAT"
    order_id = 1

    # simple latency tracking
    last_price_ts: Optional[float] = None
    latencies = []

    price_book = SharedPriceBook(SYMBOLS, name=shm_name, create=False)
    print(f"[Strategy] attached to shared memory {price_book.name}")

    t = threading.Thread(target=_news_loop, daemon=True)
    t.start()

    sock: Optional[socket.socket] = None

    while True:
        # read latest price
        price = price_book.read(primary_symbol)
        now = time.time()
        if math.isnan(price):
            time.sleep(0.1)
            continue
        last_price_ts = now

        price_hist.append(price)
        if len(price_hist) < long_window:
            time.sleep(0.1)
            continue

        short_ma = _moving_average(deque(list(price_hist)[-short_window:]))
        long_ma = _moving_average(price_hist)
        if short_ma is None or long_ma is None:
            time.sleep(0.1)
            continue

        if short_ma > long_ma:
            price_signal = "BUY"
        elif short_ma < long_ma:
            price_signal = "SELL"
        else:
            price_signal = None

        sentiment = _get_sentiment()
        if sentiment > bullish_th:
            news_signal = "BUY"
        elif sentiment < bearish_th:
            news_signal = "SELL"
        else:
            news_signal = None

        desired: str = "FLAT"
        if price_signal == "BUY" and news_signal == "BUY":
            desired = "LONG"
        elif price_signal == "SELL" and news_signal == "SELL":
            desired = "SHORT"

        # avoid duplicate orders
        side: Optional[str] = None
        if desired == "LONG" and position != "LONG":
            side = "BUY"
            position = "LONG"
        elif desired == "SHORT" and position != "SHORT":
            side = "SELL"
            position = "SHORT"
        elif desired == "FLAT":
            position = "FLAT"

        if side is not None:
            order = {
                "id": order_id,
                "side": side,
                "qty": qty,
                "symbol": primary_symbol,
                "price": price,
            }
            decision_time = time.time()
            if last_price_ts is not None:
                latencies.append(decision_time - last_price_ts)
            payload = json.dumps(order).encode("utf-8") + MESSAGE_DELIMITER

            while True:
                try:
                    if sock is None:
                        sock = _connect_ordermanager()
                    sock.sendall(payload)
                    print(f"[Strategy] sent order {order_id}: {side} {qty} {primary_symbol} @ {price}")
                    order_id += 1
                    if len(latencies) and len(latencies) % 20 == 0:
                        avg_lat = sum(latencies) / len(latencies)
                        print(f"[Metrics] avg decision latency: {avg_lat:.6f}s over {len(latencies)} trades")
                    break
                except (ConnectionError, ConnectionRefusedError, BrokenPipeError, OSError) as e:
                    print(f"[Strategy] order send error: {e}, reconnecting in 1s")
                    if sock is not None:
                        try:
                            sock.close()
                        except OSError:
                            pass
                        sock = None
                    time.sleep(1.0)

        time.sleep(0.1)


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("usage: python strategy.py <shm_name>")
        raise SystemExit(1)
    run_strategy(sys.argv[1])
