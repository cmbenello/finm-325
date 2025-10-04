from dataclasses import dataclass
from typing import Dict, Mapping
import numpy as np
import pandas as pd

@dataclass
class BacktestResult:
    cash: pd.Series
    shares: pd.DataFrame
    portfolio_value: pd.Series
    pnl: pd.Series
    executed_buys: pd.DataFrame  # 0/1 per (date,ticker)

class Backtester:
    """
    Assumes input 'signals' are ALREADY LAGGED so that a 1 at date t buys at
    the chosen execution price on date t (or t+1 if exec_next_day=True).
    Constraints: no shorts, no leverage, at most 1 share per (date,ticker).
    Greedy cash allocation per day: buy cheaper tickers first.
    """
    def __init__(self, close: pd.DataFrame, initial_cash: float = 1_000_000.0):
        assert isinstance(close.index, pd.DatetimeIndex), "close must have DatetimeIndex"
        self.close = close.sort_index()
        self.initial_cash = float(initial_cash)

    def run(self, signals: pd.DataFrame, exec_next_day: bool = False) -> BacktestResult:
        prices = self.close.astype("float64")

        # integer non-negative signals (desired qty)
        sig = (signals.reindex(index=prices.index, columns=prices.columns)
                    .fillna(0).astype(np.int64).clip(lower=0))

        exec_px = prices.shift(-1) if exec_next_day else prices

        dates, tickers = prices.index, prices.columns
        n_dates, n_tickers = prices.shape

        executed = pd.DataFrame(0, index=dates, columns=tickers, dtype=np.int64)
        cash = pd.Series(np.nan, index=dates, dtype="float64")
        cash_prev = float(self.initial_cash)

        px_vals  = exec_px.values
        need_vals= sig.values

        for i in range(n_dates):
            px_row   = px_vals[i]
            need_row = need_vals[i]              # integer desired qty per name
            # buyable if we want >0 and price is finite/positive
            buyable = (need_row > 0) & np.isfinite(px_row) & (px_row > 0)

            if buyable.any() and cash_prev > 0:
                idx = np.where(buyable)[0]
                # cheapest first
                idx = idx[np.argsort(px_row[idx], kind="mergesort")]

                for j in idx:
                    p = float(px_row[j])
                    if p <= 0 or not np.isfinite(p):
                        continue
                    max_by_cash = int(cash_prev // p)
                    qty = min(int(need_row[j]), max_by_cash)
                    if qty <= 0:
                        continue
                    spent = qty * p
                    cash_prev -= spent
                    executed.iat[i, j] = qty

            cash.iat[i] = cash_prev

        shares = executed.cumsum().astype(np.int64)
        mv = (shares * prices).sum(axis=1).astype("float64")
        portfolio_value = (cash + mv).astype("float64")
        pnl = (portfolio_value - self.initial_cash).astype("float64")

        return BacktestResult(
            cash=cash.rename("cash"),
            shares=shares,
            portfolio_value=portfolio_value.rename("portfolio_value"),
            pnl=pnl.rename("pnl"),
            executed_buys=executed,
        )

    def run_many(self, signals_by_name: Mapping[str, pd.DataFrame]) -> Dict[str, BacktestResult]:
        return {name: self.run(sig) for name, sig in signals_by_name.items()}