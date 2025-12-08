"""
Backtesting utilities for ML-based trading signals.

This module is responsible for:
  * Taking a DataFrame with prices and model-generated signals
  * Simulating a simple trading strategy with fixed position size
  * Tracking PnL, returns, and equity curve
  * Comparing against a buy-and-hold baseline

Core ideas / conventions
------------------------
- We assume signals are already computed (e.g. using `signal_generator.py`)
  and are aligned with daily bars.
- Signals are in {-1, 0, +1} (short, flat, long).
- To avoid look-ahead bias, we trade *on the next bar*:
      position_t = signal_{t-1}
  while returns at t are computed from price_{t-1} → price_t.
- We ignore transaction costs and slippage.

The main entry points are:
  * `backtest_single_ticker`
  * `backtest_multi_ticker_equal_weight`
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Configuration and result containers
# ---------------------------------------------------------------------------


@dataclass
class BacktestConfig:
  """
  Configuration parameters for the backtest.

  Parameters
  ----------
  initial_capital : float
      Starting portfolio value.
  price_col : str
      Column name for the trade price (typically "close").
  signal_col : str
      Column name containing trading signals in {-1, 0, +1}.
  per_ticker_capital : bool
      If True, we allocate `initial_capital` *per ticker* when aggregating
      across multiple tickers. If False, `initial_capital` is the total
      capital and each ticker gets an equal fraction of it.
  """

  initial_capital: float = 100_000.0
  price_col: str = "close"
  signal_col: str = "signal"
  per_ticker_capital: bool = True


@dataclass
class BacktestResult:
  """
  Container for backtest outputs.

  Attributes
  ----------
  df : pd.DataFrame
      Per-bar results including prices, signals, positions, returns, and equity.
  summary : Dict[str, float]
      Summary statistics (cumulative return, Sharpe, etc.).
  """

  df: pd.DataFrame
  summary: Dict[str, float]


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------


def _compute_returns_from_prices(prices: pd.Series) -> pd.Series:
  """
  Simple daily returns from prices: r_t = P_t / P_{t-1} - 1.
  """
  return prices.pct_change()


def _equity_from_returns(
  returns: pd.Series,
  initial_capital: float,
) -> pd.Series:
  """
  Turn a return series into an equity curve.
  """
  equity = (1.0 + returns.fillna(0.0)).cumprod() * float(initial_capital)
  return equity


def _max_drawdown(equity: pd.Series) -> float:
  """
  Compute maximum drawdown of an equity curve.

  Drawdown_t = (peak_to_date - equity_t) / peak_to_date.
  """
  equity = equity.astype(float)
  running_max = equity.cummax()
  dd = (running_max - equity) / running_max.replace(0.0, np.nan)
  return float(dd.max(skipna=True))


def _annualised_return(
  returns: pd.Series,
  periods_per_year: int = 252,
) -> float:
  """
  Annualised return assuming `periods_per_year` bars per year.
  """
  avg_ret = returns.mean(skipna=True)
  if pd.isna(avg_ret):
    return 0.0
  return float((1.0 + avg_ret) ** periods_per_year - 1.0)


def _annualised_volatility(
  returns: pd.Series,
  periods_per_year: int = 252,
) -> float:
  """
  Annualised volatility of a return series.
  """
  vol = returns.std(ddof=0, skipna=True)
  if pd.isna(vol):
    return 0.0
  return float(vol * np.sqrt(periods_per_year))


def _sharpe_ratio(
  returns: pd.Series,
  risk_free_rate: float = 0.0,
  periods_per_year: int = 252,
) -> float:
  """
  Compute annualised Sharpe ratio using simple excess returns.
  """
  if risk_free_rate != 0.0:
    rf_per_period = (1.0 + risk_free_rate) ** (1.0 / periods_per_year) - 1.0
    excess = returns - rf_per_period
  else:
    excess = returns
  ann_ret = _annualised_return(excess, periods_per_year=periods_per_year)
  ann_vol = _annualised_volatility(excess, periods_per_year=periods_per_year)
  if ann_vol == 0.0:
    return 0.0
  return float(ann_ret / ann_vol)


# ---------------------------------------------------------------------------
# Single-ticker backtest
# ---------------------------------------------------------------------------


def backtest_single_ticker(
  df: pd.DataFrame,
  config: BacktestConfig,
  label: Optional[str] = None,
) -> BacktestResult:
  """
  Run a simple long/short/flat backtest for a single ticker.

  Parameters
  ----------
  df : pd.DataFrame
    Must contain columns:
      - config.price_col  (price used for returns)
      - config.signal_col (trading signal in {-1, 0, +1})
      - Optionally "ticker" and "date" for bookkeeping.
  config : BacktestConfig
    Backtest configuration.
  label : str, optional
    Label used in summary dictionary keys (defaults to ticker name if present).

  Logic
  -----
  - Compute asset returns r_t from price_t / price_{t-1} - 1.
  - Position_t = signal_{t-1} to avoid look-ahead.
  - Strategy return: pos_t * r_t.
  - Equity curve: cumprod of (1 + strategy_return) * initial_capital.
  - Buy & hold: always invested from first bar with non-NaN price.
  """
  if config.price_col not in df.columns:
    raise ValueError(f"Missing price column '{config.price_col}' in DataFrame.")
  if config.signal_col not in df.columns:
    raise ValueError(f"Missing signal column '{config.signal_col}' in DataFrame.")

  data = df.copy()
  prices = data[config.price_col].astype(float)
  signals = data[config.signal_col].astype(float)

  # Basic returns
  asset_ret = _compute_returns_from_prices(prices)

  # Positions lagged by one period to avoid look-ahead
  position = signals.shift(1).fillna(0.0)

  # Strategy returns
  strat_ret = position * asset_ret

  # Equity curves
  equity = _equity_from_returns(strat_ret, config.initial_capital)
  bh_equity = _equity_from_returns(asset_ret, config.initial_capital)

  # Attach to DataFrame
  data["asset_return"] = asset_ret
  data["position"] = position
  data["strategy_return"] = strat_ret
  data["equity"] = equity
  data["buy_hold_equity"] = bh_equity

  # Trades when position changes
  data["trade"] = position.diff().fillna(position).abs()

  # Summary stats
  label = (
    label
    or (str(data["ticker"].iloc[0]) if "ticker" in data.columns and len(data) > 0 else "strategy")
  )

  cum_return = float(equity.iloc[-1] / config.initial_capital - 1.0) if len(equity) else 0.0
  bh_cum_return = float(bh_equity.iloc[-1] / config.initial_capital - 1.0) if len(bh_equity) else 0.0

  summary = {
    "label": label,
    "cumulative_return": cum_return,
    "buy_hold_cumulative_return": bh_cum_return,
    "excess_return_vs_buy_hold": cum_return - bh_cum_return,
    "annualised_return": _annualised_return(strat_ret),
    "annualised_volatility": _annualised_volatility(strat_ret),
    "sharpe": _sharpe_ratio(strat_ret),
    "max_drawdown": _max_drawdown(equity),
    "num_trades": float((data["trade"] > 0).sum()),
  }

  return BacktestResult(df=data, summary=summary)


# ---------------------------------------------------------------------------
# Multi-ticker aggregation
# ---------------------------------------------------------------------------


def backtest_multi_ticker_equal_weight(
  df: pd.DataFrame,
  config: BacktestConfig,
) -> Tuple[BacktestResult, Dict[str, BacktestResult]]:
  """
  Run single-ticker backtests and aggregate them into an equal-weight portfolio.

  For the portfolio:
    - At each date, we take the simple average of strategy returns across
      available tickers.
    - We then build an equity curve from these portfolio returns.

  Parameters
  ----------
  df : pd.DataFrame
    Multi-ticker DataFrame containing at least:
      - "ticker"
      - config.price_col
      - config.signal_col
  config : BacktestConfig

  Returns
  -------
  (portfolio_result, per_ticker_results)
    portfolio_result : BacktestResult
        Aggregated equal-weight portfolio performance.
    per_ticker_results : dict
        Mapping ticker -> BacktestResult.
  """
  if "ticker" not in df.columns:
    raise ValueError("Multi-ticker backtest requires a 'ticker' column.")

  per_ticker: Dict[str, BacktestResult] = {}
  for ticker, g in df.groupby("ticker", sort=False):
    per_ticker[ticker] = backtest_single_ticker(g.sort_values("date"), config=config, label=str(ticker))

  # Build portfolio returns by averaging per-ticker strategy returns each day
  # First, concatenate per-ticker returns as columns aligned on date
  ret_frames = []
  for ticker, res in per_ticker.items():
    tmp = res.df[["date", "strategy_return"]].copy() if "date" in res.df.columns else res.df[["strategy_return"]].copy()
    if "date" in tmp.columns:
      tmp = tmp.set_index("date")
    tmp = tmp.rename(columns={"strategy_return": str(ticker)})
    ret_frames.append(tmp)

  if not ret_frames:
    # No data
    empty_df = pd.DataFrame()
    return BacktestResult(df=empty_df, summary={}), per_ticker

  all_returns = pd.concat(ret_frames, axis=1).sort_index()
  portfolio_ret = all_returns.mean(axis=1, skipna=True)

  # Portfolio equity
  equity = _equity_from_returns(portfolio_ret, config.initial_capital)

  portfolio_df = pd.DataFrame(
    {
      "date": equity.index,
      "portfolio_return": portfolio_ret.values,
      "portfolio_equity": equity.values,
    }
  )

  cum_return = float(equity.iloc[-1] / config.initial_capital - 1.0) if len(equity) else 0.0

  summary = {
    "label": "equal_weight_portfolio",
    "cumulative_return": cum_return,
    "annualised_return": _annualised_return(portfolio_ret),
    "annualised_volatility": _annualised_volatility(portfolio_ret),
    "sharpe": _sharpe_ratio(portfolio_ret),
    "max_drawdown": _max_drawdown(equity),
    "num_tickers": float(len(per_ticker)),
  }

  portfolio_result = BacktestResult(df=portfolio_df, summary=summary)
  return portfolio_result, per_ticker


# ---------------------------------------------------------------------------
# CLI for quick experimentation
# ---------------------------------------------------------------------------


if __name__ == "__main__":
  import argparse
  import json

  parser = argparse.ArgumentParser(description="Backtest ML trading signals.")
  parser.add_argument(
    "--signals",
    type=str,
    required=True,
    help="Path to CSV file containing prices + signals (e.g. output of signal_generator).",
  )
  parser.add_argument(
    "--signal-col",
    type=str,
    default="signal",
    help="Name of the signal column to backtest (default: 'signal').",
  )
  parser.add_argument(
    "--price-col",
    type=str,
    default="close",
    help="Name of the price column to use for returns (default: 'close').",
  )
  parser.add_argument(
    "--initial-capital",
    type=float,
    default=100_000.0,
    help="Initial capital for the backtest (default: 100000).",
  )
  parser.add_argument(
    "--per-ticker-capital",
    action="store_true",
    help="Interpret initial capital as per-ticker capital in multi-ticker mode.",
  )
  parser.add_argument(
    "--output-prefix",
    type=str,
    default=None,
    help="If provided, save per-ticker and portfolio results to CSV with this prefix.",
  )
  parser.add_argument(
    "--summary-out",
    type=str,
    default=None,
    help="Optional path to save summary metrics as JSON.",
  )

  args = parser.parse_args()

  df = pd.read_csv(args.signals)
  if "date" in df.columns:
    # Normalise date type for robustness
    df["date"] = pd.to_datetime(df["date"])

  bt_cfg = BacktestConfig(
    initial_capital=args.initial_capital,
    price_col=args.price_col,
    signal_col=args.signal_col,
    per_ticker_capital=args.per_ticker_capital,
  )

  if "ticker" in df.columns:
    portfolio_res, per_ticker_res = backtest_multi_ticker_equal_weight(df, config=bt_cfg)
    print("=== Portfolio summary ===")
    for k, v in portfolio_res.summary.items():
      print(f"{k}: {v}")
    print()

    print("=== Per-ticker summary ===")
    for tkr, res in per_ticker_res.items():
      print(f"TICKER {tkr}:")
      for k, v in res.summary.items():
        print(f"  {k}: {v}")
      print()

    if args.output_prefix is not None:
      # Save portfolio and per-ticker results
      portfolio_res.df.to_csv(f"{args.output_prefix}_portfolio.csv", index=False)
      for tkr, res in per_ticker_res.items():
        out_path = f"{args.output_prefix}_{tkr}.csv"
        res.df.to_csv(out_path, index=False)

    if args.summary_out is not None:
      summary = {
        "portfolio": portfolio_res.summary,
        "per_ticker": {t: r.summary for t, r in per_ticker_res.items()},
      }
      with open(args.summary_out, "w") as f:
        json.dump(summary, f, indent=2)

  else:
    # Single-ticker data
    res = backtest_single_ticker(df, config=bt_cfg)
    print("=== Single-ticker summary ===")
    for k, v in res.summary.items():
      print(f"{k}: {v}")

    if args.output_prefix is not None:
      res.df.to_csv(f"{args.output_prefix}_backtest.csv", index=False)

    if args.summary_out is not None:
      with open(args.summary_out, "w") as f:
        json.dump(res.summary, f, indent=2)
