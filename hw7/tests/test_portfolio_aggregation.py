from __future__ import annotations
import math
import numpy as np
import pandas as pd
import pytest

# If your build_portfolio lives elsewhere, update this import.
from portfolio import build_portfolio

def test_portfolio_parallel_equals_sequential(pd_loaded, portfolio_struct):
    # Make sure timestamps are proper
    df = pd_loaded.sort_values(["symbol","timestamp"]).reset_index(drop=True)

    seq = build_portfolio(df, portfolio_struct, parallel=False)
    par = build_portfolio(df, portfolio_struct, parallel=True)

    # Totals within cents
    assert abs(seq["total_value"] - par["total_value"]) <= 0.01

    # Volatility: non-negative and numerically close (allow tiny tolerance)
    def n(x): 
        return np.nan if x is None else float(x)
    s_vol, p_vol = n(seq["aggregate_volatility"]), n(par["aggregate_volatility"])
    if not (math.isnan(s_vol) or math.isnan(p_vol)):
        assert s_vol >= 0.0 and p_vol >= 0.0
        assert abs(s_vol - p_vol) <= 1e-9

    # Drawdown should be <= 0 and close
    s_dd, p_dd = n(seq["max_drawdown"]), n(par["max_drawdown"])
    if not (math.isnan(s_dd) or math.isnan(p_dd)):
        assert s_dd <= 0.0 and p_dd <= 0.0
        assert abs(s_dd - p_dd) <= 1e-9