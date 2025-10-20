# tests/test_strategy.py
import numpy as np
import pandas as pd
import pytest
from pandas.testing import assert_series_equal
from backtester.strategy import VolatilityBreakoutStrategy

def test_signals_length(strategy, prices):
    sig = strategy.signals(prices)
    assert len(sig) == len(prices)

def test_window_len():
    with pytest.raises(ValueError):
        VolatilityBreakoutStrategy(window=0)

def test_k():
    with pytest.raises(ValueError):
        VolatilityBreakoutStrategy(k=-1)

def test_empty_signals(strategy):
    sig = strategy.signals([])
    expected = pd.Series(dtype=float, name="signal")
    assert_series_equal(sig, expected)

def test_constant_prices_all_zero():
    s = pd.Series([100.0] * 30)
    strat = VolatilityBreakoutStrategy(window=5, k=1.0)
    sig = strat.signals(s)
    # No breakouts on a flat series
    assert (sig == 0).all()
    assert sig.name == "signal"
    assert sig.dtype == int

def test_warmup_region_zero():
    n = 40
    s = pd.Series(np.linspace(100, 120, n)) 
    W = 10
    strat = VolatilityBreakoutStrategy(window=W, k=0.0)  # threshold 0 -> buy when return > 0
    sig = strat.signals(s)
    # Rolling std needs W non-NaN returns, so signals before index W are zeros
    assert (sig.iloc[:W] == 0).all()
    # After warmup, since returns > 0, all should be 1
    assert (sig.iloc[W:] == 1).all()

def test_single_strong_breakout_exactly_once():
    # Build returns: W-1 zeros, then a huge spike 1.0 (100%) at t=W
    # Prices: start at 100, flat for W days, then jump to 200, then flat
    W = 8
    prices = [100.0] * (W + 1)  # indices 0..W, pct_change at W will be 1.0
    prices[W] = 200.0
    prices += [200.0] * 10
    s = pd.Series(prices)

    strat = VolatilityBreakoutStrategy(window=W, k=2.0)
    sig = strat.signals(s)

    # Expect exactly one '1' on the jump day; zeros elsewhere
    ones_idx = np.flatnonzero(sig.values)
    assert ones_idx.tolist() == [W]

def test_log_vs_pct_direction_agree_when_k_zero():
    # With k=0 and enough window, the signal is r_t > 0.
    # Direction (up move) matches for pct vs log returns.
    s = pd.Series([100, 101, 102, 101, 103, 104, 104, 105, 104, 106], dtype=float)
    W = 3  # ensure rolling std becomes defined after some steps
    strat_pct = VolatilityBreakoutStrategy(window=W, k=0.0, use_log_returns=False)
    strat_log = VolatilityBreakoutStrategy(window=W, k=0.0, use_log_returns=True)

    sig_pct = strat_pct.signals(s)
    sig_log = strat_log.signals(s)

    # They can differ during warmup (std NaN), but once std is defined (index >= W),
    # both should flag the same indices (positive moves -> 1).
    assert (sig_pct.iloc[W:] == sig_log.iloc[W:]).all()

def test_handles_head_nans():
    s = pd.Series([np.nan, 100.0, 101.0, 102.0, 103.0])
    strat = VolatilityBreakoutStrategy(window=2, k=0.5)
    sig = strat.signals(s)
    # Should not crash; length preserved; name correct
    assert len(sig) == len(s)
    assert sig.name == "signal"

def test_len_guard_reindex_is_hit(monkeypatch):
    s = pd.Series([100.0, 101.0, 102.0, 103.0])

    # Capture the original before patching
    orig_pct_change = pd.Series.pct_change

    # Make pct_change return a shorter series to force the guard
    def fake_pct_change(self, *args, **kwargs):
        real = orig_pct_change(self, *args, **kwargs)
        return real.iloc[1:]  # length becomes len(s) - 1

    # Patch only for this test
    monkeypatch.setattr(pd.Series, "pct_change", fake_pct_change, raising=False)

    strat = VolatilityBreakoutStrategy(window=2, k=0.5, use_log_returns=False)
    sig = strat.signals(s)

    # Guard should have reindexed back to s' length
    assert len(sig) == len(s)
    assert sig.index.equals(s.index)
    assert sig.name == "signal"