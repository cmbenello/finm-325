from __future__ import annotations

import random
import socket
import threading
import time
from typing import Dict, List

from config import (
    SYMBOLS,
    MESSAGE_DELIMITER,
    GATEWAY_PRICE_HOST,
    GATEWAY_PRICE_PORT,
    GATEWAY_NEWS_HOST,
    GATEWAY_NEWS_PORT,
)


def _init_prices(symbols: List[str]) -> Dict[str, float]:
    prices: Dict[str, float] = {}
    for s in symbols:
        prices[s] = random.uniform(50.0, 200.0)
    return prices


def _step_prices(prices: Dict[str, float]) -> None:
    for sym in prices:
        # small random walk step
        delta = random.uniform(-0.5, 0.5)
        new_price = max(1.0, prices[sym] + delta)
        prices[sym] = new_price


def _price_server() -> None:
    prices = _init_prices(SYMBOLS)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((GATEWAY_PRICE_HOST, GATEWAY_PRICE_PORT))
        s.listen()
        print(f"[Gateway/Price] listening on {GATEWAY_PRICE_HOST}:{GATEWAY_PRICE_PORT}")
        while True:
            conn, addr = s.accept()
            print(f"[Gateway/Price] client {addr}")
            try:
                while True:
                    _step_prices(prices)
                    for sym in SYMBOLS:
                        price = prices[sym]
                        ts = time.time()
                        msg = f"{sym},{price:.4f},{ts:.6f}".encode("utf-8") + MESSAGE_DELIMITER
                        conn.sendall(msg)
                    time.sleep(0.1)
            except (ConnectionResetError, BrokenPipeError):
                print(f"[Gateway/Price] client {addr} disconnected")
            finally:
                conn.close()


def _news_server() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((GATEWAY_NEWS_HOST, GATEWAY_NEWS_PORT))
        s.listen()
        print(f"[Gateway/News] listening on {GATEWAY_NEWS_HOST}:{GATEWAY_NEWS_PORT}")
        while True:
            conn, addr = s.accept()
            print(f"[Gateway/News] client {addr}")
            try:
                while True:
                    sentiment = random.randint(0, 100)
                    msg = f"{sentiment}".encode("utf-8") + MESSAGE_DELIMITER
                    conn.sendall(msg)
                    time.sleep(0.5)
            except (ConnectionResetError, BrokenPipeError):
                print(f"[Gateway/News] client {addr} disconnected")
            finally:
                conn.close()


def run_gateway() -> None:
    price_thread = threading.Thread(target=_price_server, daemon=True)
    news_thread = threading.Thread(target=_news_server, daemon=True)

    price_thread.start()
    news_thread.start()

    # Keep the main thread alive so the process does not exit.
    price_thread.join()
    news_thread.join()


if __name__ == "__main__":
    run_gateway()
