
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import json
import socket
import threading
import time
from collections import deque

import pytest

import gateway
import order_manager
from config import (
    GATEWAY_NEWS_HOST,
    GATEWAY_NEWS_PORT,
    GATEWAY_PRICE_HOST,
    GATEWAY_PRICE_PORT,
    MESSAGE_DELIMITER,
)
from shared_memory_utils import SharedPriceBook
from strategy import _moving_average


# -----------------------
# Shared memory tests
# -----------------------


def test_shared_pricebook_update_propagates() -> None:
    symbols = ["AAPL", "MSFT"]
    name = "test_prices"

    creator = SharedPriceBook(symbols, name=name, create=True)
    try:
        creator.update("AAPL", 123.45)

        reader = SharedPriceBook(symbols, name=name, create=False)
        try:
            assert reader.read("AAPL") == pytest.approx(123.45)
            all_prices = reader.read_all()
            assert all_prices["AAPL"] == pytest.approx(123.45)
        finally:
            reader.close()
    finally:
        creator.close()
        creator.unlink()


# -----------------------
# Serialization tests
# -----------------------


def test_order_message_serialization_roundtrip() -> None:
    order = {
        "id": 1,
        "side": "BUY",
        "qty": 10,
        "symbol": "AAPL",
        "price": 173.2,
    }
    payload = json.dumps(order).encode("utf-8") + MESSAGE_DELIMITER

    # simulate the framing logic used by OrderManager
    raw = payload.split(MESSAGE_DELIMITER)[0]
    decoded = json.loads(raw.decode("utf-8"))

    assert decoded == order


# -----------------------
# Gateway connection tests
# -----------------------


def _start_price_server() -> threading.Thread:
    t = threading.Thread(target=gateway._price_server, daemon=True)
    t.start()
    time.sleep(0.2)
    return t


def _start_news_server() -> threading.Thread:
    t = threading.Thread(target=gateway._news_server, daemon=True)
    t.start()
    time.sleep(0.2)
    return t


def test_gateway_price_connection_established() -> None:
    _start_price_server()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((GATEWAY_PRICE_HOST, GATEWAY_PRICE_PORT))


def test_gateway_news_connection_established() -> None:
    _start_news_server()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((GATEWAY_NEWS_HOST, GATEWAY_NEWS_PORT))


# -----------------------
# Strategy helper tests
# -----------------------


def test_moving_average_basic() -> None:
    buf = deque([1.0, 2.0, 3.0, 4.0])
    assert _moving_average(buf) == pytest.approx(2.5)

    empty = deque([])
    assert _moving_average(empty) is None


def test_strategy_signal_logic_buy_sell_neutral() -> None:
    # This mirrors the documented logic in run_strategy:
    # - price signal: BUY if short > long, SELL if short < long
    # - news signal: BUY if sentiment > 60, SELL if sentiment < 40
    # - trade only when both agree.
    def decide(short_ma, long_ma, sentiment, bullish_th=60, bearish_th=40):
        if short_ma > long_ma:
            price_sig = "BUY"
        elif short_ma < long_ma:
            price_sig = "SELL"
            # else None
        else:
            price_sig = None

        if sentiment > bullish_th:
            news_sig = "BUY"
        elif sentiment < bearish_th:
            news_sig = "SELL"
        else:
            news_sig = None

        if price_sig == "BUY" and news_sig == "BUY":
            return "BUY"
        if price_sig == "SELL" and news_sig == "SELL":
            return "SELL"
        return "NEUTRAL"

    # Both bullish
    assert decide(105, 100, 80) == "BUY"
    # Both bearish
    assert decide(95, 100, 20) == "SELL"
    # Disagree: price BUY, news neutral
    assert decide(105, 100, 50) == "NEUTRAL"
    # Disagree: price neutral, news BUY
    assert decide(100, 100, 90) == "NEUTRAL"
    # Disagree: price SELL, news BUY
    assert decide(95, 100, 90) == "NEUTRAL"


# -----------------------
# OrderManager tests
# -----------------------


def test_ordermanager_receives_correct_number_of_orders() -> None:
    # Use a socketpair to avoid binding ports.
    s_server, s_client = socket.socketpair()
    orders = []

    original_log_order = order_manager.log_order

    def fake_log(order):
        orders.append(order)

    order_manager.log_order = fake_log  # type: ignore[assignment]

    try:
        th = threading.Thread(
            target=order_manager.handle_client,
            args=(s_server, ("local", 0)),
            daemon=True,
        )
        th.start()

        for i in range(3):
            order = {
                "id": i + 1,
                "side": "BUY",
                "qty": 10,
                "symbol": "AAPL",
                "price": 100.0 + i,
            }
            payload = json.dumps(order).encode("utf-8") + MESSAGE_DELIMITER
            s_client.sendall(payload)

        s_client.shutdown(socket.SHUT_WR)
        th.join(timeout=1.0)

    finally:
        order_manager.log_order = original_log_order  # type: ignore[assignment]
        s_client.close()
        s_server.close()

    assert len(orders) == 3
    assert orders[0]["id"] == 1
    assert orders[-1]["id"] == 3
