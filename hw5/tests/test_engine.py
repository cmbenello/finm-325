# tests/test_engine.py
from unittest.mock import MagicMock
from backtester.engine import Backtester
import pytest
import pandas as pd

def test_engine_uses_tminus1_signal(prices, broker, strategy, monkeypatch):
    # Force exactly one buy at t=10 by controlling signals
    fake_strategy = MagicMock()
    fake_strategy.signals.return_value = prices*0
    fake_strategy.signals.return_value.iloc[9] = 1  # triggers buy at t=10
    bt = Backtester(fake_strategy, broker)
    eq = bt.run(prices)
    assert broker.position == 1
    assert broker.cash == 1000 - float(prices.iloc[10])


def test_engine_empty_prices_returns_cash(broker):
    bt = Backtester(strategy=MagicMock(), broker=broker)
    equity = bt.run(pd.Series([], dtype=float))
    assert equity == pytest.approx(broker.cash)
    assert broker.position == 0

def test_engine_does_nothing_on_prev_zero(prices, broker):
    fake_strategy = MagicMock()
    fake_strategy.signals.return_value = pd.Series(0, index=prices.index)
    bt = Backtester(fake_strategy, broker)
    start_cash = broker.cash
    equity = bt.run(prices)
    assert broker.position == 0
    assert broker.cash == start_cash
    # equity equals cash because position=0
    assert equity == pytest.approx(start_cash)

def test_engine_buys_once_no_double_buy(prices, broker):
    # prev=1 at t=6 and again at t=7 → should buy only once (position gate)
    sig = pd.Series(0, index=prices.index)
    sig.iloc[5] = 1
    sig.iloc[6] = 1
    fake_strategy = MagicMock()
    fake_strategy.signals.return_value = sig

    bt = Backtester(fake_strategy, broker)
    bt.run(prices)

    # Only one BUY executed at t=6 (prev=1 from index 5)
    assert broker.position == 1
    assert broker.cash == pytest.approx(1000 - float(prices.iloc[6]))

def test_engine_sells_on_prev_minus_one(prices, broker):
    # Start long, then issue prev=-1 at t=10 to SELL there
    broker.market_order("BUY", 1, float(prices.iloc[0]))  # position=1
    sig = pd.Series(0, index=prices.index)
    sig.iloc[9] = -1  # triggers SELL at t=10
    fake_strategy = MagicMock()
    fake_strategy.signals.return_value = sig

    bt = Backtester(fake_strategy, broker)
    bt.run(prices)

    assert broker.position == 0
    # Cash should be initial_cash - buy_price + sell_price
    expected_cash = 1000 - float(prices.iloc[0]) + float(prices.iloc[10])
    assert broker.cash == pytest.approx(expected_cash)

def test_engine_buy_then_sell_later(prices, broker):
    # Buy at t=6 (prev=1 at 5), Sell at t=21 (prev=-1 at 20)
    sig = pd.Series(0, index=prices.index)
    sig.iloc[5] = 1
    sig.iloc[20] = -1
    fake_strategy = MagicMock()
    fake_strategy.signals.return_value = sig

    bt = Backtester(fake_strategy, broker)
    equity = bt.run(prices)

    # End flat; equity equals realized PnL
    assert broker.position == 0
    expected_cash = 1000 - float(prices.iloc[6]) + float(prices.iloc[21])
    assert broker.cash == pytest.approx(expected_cash)
    assert equity == pytest.approx(expected_cash)

def test_engine_calls_strategy_once_with_prices(prices, broker):
    fake_strategy = MagicMock()
    fake_strategy.signals.return_value = pd.Series(0, index=prices.index)
    bt = Backtester(fake_strategy, broker)
    bt.run(prices)
    fake_strategy.signals.assert_called_once()
    # Ensure it was called with a Series equal to 'prices'
    called_prices = fake_strategy.signals.call_args[0][0]
    assert isinstance(called_prices, pd.Series)
    assert len(called_prices) == len(prices)
    assert called_prices.index.equals(prices.index)
    assert pytest.approx(called_prices.iloc[-1]) == float(prices.iloc[-1])