# tests/test_broker.py
import pytest
from backtester.broker import Broker

def test_buy_and_sell_updates_cash_and_pos(broker):
    # initial state
    assert broker.cash == 1000
    assert broker.position == 0

    # Buy 2 @ $10
    broker.market_order("BUY", 2, 10.0)
    assert broker.position == 2
    assert broker.cash == pytest.approx(1000 - 2 * 10.0)

    # Sell 1 @ $20
    broker.market_order("SELL", 1, 20.0)
    assert broker.position == 1
    assert broker.cash == pytest.approx(1000 - 20 + 20.0)


def test_rejects_bad_orders(broker):
    with pytest.raises(ValueError):
        broker.market_order("BUY", 0, 10.0)
    with pytest.raises(ValueError):
        broker.market_order("HOLD", 1, 10.0)
    with pytest.raises(ValueError):
        broker.market_order("BUY", 1, -10.0)


def test_insufficient_cash_raises(broker):
    # buying too much
    with pytest.raises(ValueError):
        broker.market_order("BUY", 2000, 1.0)  # costs more than cash


def test_insufficient_shares_raises(broker):
    # selling when flat
    with pytest.raises(ValueError):
        broker.market_order("SELL", 1, 10.0)


def test_multiple_buys_and_sells_consistent(broker):
    # simple consistency check over several operations
    broker.market_order("BUY", 5, 10.0)
    broker.market_order("BUY", 5, 20.0)
    broker.market_order("SELL", 3, 15.0)

    # position = 7, cash reduced accordingly
    expected_cash = 1000 - (5 * 10 + 5 * 20) + (3 * 15)
    assert broker.cash == pytest.approx(expected_cash)
    assert broker.position == 7

def test_init_rejects_negative_cash():
    with pytest.raises(ValueError, match="Initial cash must be non-negative"):
        Broker(cash=-1)

def test_init_allows_zero_and_positive_cash():
    b0 = Broker(cash=0)
    assert b0.cash == 0 and b0.position == 0

    b = Broker(cash=123.45)
    assert b.cash == pytest.approx(123.45) and b.position == 0