"""
Feature engineering utilities for market data.

This module is responsible for:
  * Loading raw OHLCV data for multiple tickers
  * Computing returns, lagged features, and basic technical indicators
  * Creating prediction targets for classification or regression tasks

The core entry point is `generate_features_and_labels`, which will be used
by the training and backtesting code.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Literal, Optional, Sequence, Tuple

import numpy as np
import pandas as pd


TaskType = Literal["classification", "regression"]


@dataclass
class FeatureConfig:
  """
  Configuration for the feature engineering pipeline.

  Parameters
  ----------
  prediction_horizon : int
      Number of days ahead for the target (e.g. 1 for next-day return).
  sma_windows : Sequence[int]
      Window sizes for simple moving averages on the close price.
  rsi_period : int
      Lookback period used to compute the RSI.
  macd_fast : int
      Window size for the fast EMA used in MACD.
  macd_slow : int
      Window size for the slow EMA used in MACD.
  macd_signal : int
      Window size for the MACD signal EMA.
  lag_return_windows : Sequence[int]
      Lags (in days) for lagged returns.
  vol_window : int
      Rolling window size (in days) for realized volatility of returns.
  vol_norm_window : int
      Rolling window for volume z-score normalisation.
  task : TaskType
      Either "classification" (default) or "regression".
  classification_threshold : float
      Threshold on the future return for assigning class 1 when task is
      "classification". Default is 0.0 (just sign of the return).
  dropna : bool
      Whether to drop rows with missing values at the end of the pipeline.
  """

  prediction_horizon: int = 1
  sma_windows: Sequence[int] = (5, 10, 20)
  rsi_period: int = 14
  macd_fast: int = 12
  macd_slow: int = 26
  macd_signal: int = 9
  lag_return_windows: Sequence[int] = (1, 3, 5)
  vol_window: int = 5
  vol_norm_window: int = 20
  task: TaskType = "classification"
  classification_threshold: float = 0.0
  dropna: bool = True


# ---------------------------------------------------------------------------
# Helper functions for technical indicators
# ---------------------------------------------------------------------------


def _ema(series: pd.Series, span: int) -> pd.Series:
  """Exponential moving average using pandas' ewm."""
  return series.ewm(span=span, adjust=False).mean()


def _rsi(prices: pd.Series, period: int = 14) -> pd.Series:
  """
  Compute the Relative Strength Index (RSI).

  Parameters
  ----------
  prices : pd.Series
      Price series (e.g., close prices) indexed by time.
  period : int
      Lookback period.

  Returns
  -------
  pd.Series
      RSI values in [0, 100].
  """
  delta = prices.diff()

  gain = (delta.where(delta > 0, 0.0)).rolling(window=period, min_periods=period).mean()
  loss = (-delta.where(delta < 0, 0.0)).rolling(window=period, min_periods=period).mean()

  # Avoid division by zero
  rs = gain / loss.replace(0.0, np.nan)
  rsi = 100.0 - 100.0 / (1.0 + rs)
  return rsi


def _macd(
    prices: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> Tuple[pd.Series, pd.Series, pd.Series]:
  """
  Compute MACD indicator.

  Returns
  -------
  macd_line, signal_line, macd_histogram : pd.Series
  """
  ema_fast = _ema(prices, span=fast)
  ema_slow = _ema(prices, span=slow)
  macd_line = ema_fast - ema_slow
  signal_line = _ema(macd_line, span=signal)
  hist = macd_line - signal_line
  return macd_line, signal_line, hist


# ---------------------------------------------------------------------------
# Core feature engineering logic
# ---------------------------------------------------------------------------


def _normalise_column(
    series: pd.Series,
    method: Literal["zscore", "minmax", "none"] = "zscore",
) -> pd.Series:
  """
  Simple normalisation utility that operates per-column.

  This is used sparingly here (e.g., for volume). Most scaling for models
  should be done in the training pipeline with scikit-learn transformers.
  """
  if method == "none":
    return series

  if method == "zscore":
    mean = series.mean()
    std = series.std(ddof=0)
    if std == 0 or np.isnan(std):
      return series * 0.0
    return (series - mean) / std

  if method == "minmax":
    min_val = series.min()
    max_val = series.max()
    if max_val == min_val:
      return series * 0.0
    return (series - min_val) / (max_val - min_val)

  raise ValueError(f"Unknown normalisation method: {method}")


def _standardise_column_by_rolling(
    series: pd.Series,
    window: int,
) -> pd.Series:
  """
  Rolling z-score, used e.g. for volume.

  For each point, subtract the rolling mean and divide by rolling std over
  the previous `window` observations (including the current one).
  """
  rolling_mean = series.rolling(window=window, min_periods=1).mean()
  rolling_std = series.rolling(window=window, min_periods=1).std(ddof=0)
  # Avoid division by zero
  rolling_std = rolling_std.replace(0.0, np.nan)
  return (series - rolling_mean) / rolling_std


def _ensure_standard_columns(df: pd.DataFrame) -> pd.DataFrame:
  """
  Normalise column naming to lower-case OHLCV.

  Supported variants:
    - "date" or "Date"
    - "ticker" or "symbol"
    - OHLC columns in upper/lower case
  """
  col_map = {c.lower(): c for c in df.columns}

  # Build a new column dict with canonical names
  rename_map = {}

  def _map_one(candidates: Iterable[str], target: str) -> None:
    for cand in candidates:
      if cand in col_map:
        rename_map[col_map[cand]] = target
        return

  _map_one(["date"], "date")
  _map_one(["ticker", "symbol"], "ticker")
  _map_one(["open"], "open")
  _map_one(["high"], "high")
  _map_one(["low"], "low")
  _map_one(["close", "adj_close", "adjclose"], "close")
  _map_one(["volume", "vol"], "volume")

  df = df.rename(columns=rename_map)

  required = ["date", "ticker", "open", "high", "low", "close", "volume"]
  missing = [c for c in required if c not in df.columns]
  if missing:
    raise ValueError(f"Missing required columns in market data: {missing}")

  # Ensure proper dtypes
  df["date"] = pd.to_datetime(df["date"])
  return df


def load_market_data(
    market_data_path: str,
    tickers_path: Optional[str] = None,
) -> pd.DataFrame:
  """
  Load raw market data and optionally filter to a set of tickers.

  Parameters
  ----------
  market_data_path : str
      Path to `market_data_ml.csv`.
  tickers_path : str, optional
      Path to `tickers.csv` (or similar). If provided, the data is filtered
      to tickers listed in this file. The file is assumed to contain at
      least one column named "ticker" or a single unnamed column of symbols.

  Returns
  -------
  pd.DataFrame
      Raw (but column-standardised) data sorted by ticker, date.
  """
  df = pd.read_csv(market_data_path)
  df = _ensure_standard_columns(df)

  if tickers_path is not None:
    tickers_df = pd.read_csv(tickers_path)
    # Try to be flexible about column naming
    if "ticker" in tickers_df.columns:
      tickers = tickers_df["ticker"].astype(str).unique()
    else:
      # Assume first column contains tickers
      tickers = tickers_df.iloc[:, 0].astype(str).unique()
    df = df[df["ticker"].isin(tickers)]

  df = df.sort_values(["ticker", "date"]).reset_index(drop=True)
  return df


def engineer_features_for_single_ticker(
    df: pd.DataFrame,
    config: FeatureConfig,
) -> pd.DataFrame:
  """
  Compute features and targets for a single-ticker DataFrame.

  Parameters
  ----------
  df : pd.DataFrame
      Must contain columns: date, ticker, open, high, low, close, volume.
      All rows must correspond to the same ticker.
  config : FeatureConfig
      Configuration object.

  Returns
  -------
  pd.DataFrame
      DataFrame with additional feature and target columns.
  """
  df = df.copy()

  close = df["close"]
  volume = df["volume"]

  # Basic returns
  df["return_1d"] = close.pct_change()
  # log-return is numerically more stable
  df["log_return_1d"] = np.log(close).diff()

  # Lagged returns
  for lag in config.lag_return_windows:
    df[f"lag_return_{lag}d"] = df["return_1d"].shift(lag)

  # Realised volatility of returns
  df[f"vol_{config.vol_window}d"] = df["return_1d"].rolling(
    window=config.vol_window, min_periods=1
  ).std(ddof=0)

  # Simple moving averages and price / SMA ratios
  for w in config.sma_windows:
    df[f"sma_{w}"] = close.rolling(window=w, min_periods=1).mean()
    df[f"price_over_sma_{w}"] = close / df[f"sma_{w}"]

  # RSI
  df[f"rsi_{config.rsi_period}"] = _rsi(close, period=config.rsi_period)

  # MACD
  macd_line, macd_signal, macd_hist = _macd(
    close,
    fast=config.macd_fast,
    slow=config.macd_slow,
    signal=config.macd_signal,
  )
  df["macd_line"] = macd_line
  df["macd_signal"] = macd_signal
  df["macd_hist"] = macd_hist

  # Volume features
  df["volume_log"] = np.log(volume.replace(0, np.nan))
  df[f"volume_zscore_{config.vol_norm_window}d"] = _standardise_column_by_rolling(
    volume, window=config.vol_norm_window
  )

  # Future return for target definition
  horizon = config.prediction_horizon
  future_price = close.shift(-horizon)
  future_return = future_price / close - 1.0
  df[f"future_return_{horizon}d"] = future_return

  if config.task == "classification":
    thr = config.classification_threshold
    # 1 if future return > thr, else 0
    df["target"] = (future_return > thr).astype(int)
  elif config.task == "regression":
    df["target"] = future_return
  else:
    raise ValueError(f"Unknown task type: {config.task}")

  return df


def engineer_features(
    df: pd.DataFrame,
    config: Optional[FeatureConfig] = None,
) -> pd.DataFrame:
  """
  Apply feature engineering for a multi-ticker DataFrame.

  Parameters
  ----------
  df : pd.DataFrame
      Raw (but column-standardised) market data.
  config : FeatureConfig, optional
      Configuration for the feature pipeline. If None, the default
      configuration is used.

  Returns
  -------
  pd.DataFrame
      Data with engineered features and targets.
  """
  if config is None:
    config = FeatureConfig()

  df = _ensure_standard_columns(df)
  df = df.sort_values(["ticker", "date"]).reset_index(drop=True)

  # Apply per-ticker to avoid look-ahead leakage across tickers
  grouped = []
  for ticker, g in df.groupby("ticker", sort=False):
    engineered = engineer_features_for_single_ticker(g, config=config)
    grouped.append(engineered)

  out = pd.concat(grouped, axis=0).sort_values(["ticker", "date"]).reset_index(drop=True)

  if config.dropna:
    # Drop rows that contain any NaN in feature or target columns.
    # We keep the core OHLCV data even if partially missing.
    feature_cols = [
      c
      for c in out.columns
      if c
      not in {
        "date",
        "ticker",
        "open",
        "high",
        "low",
        "close",
        "volume",
      }
    ]
    out = out.dropna(subset=feature_cols + ["target"])

  return out


def generate_features_and_labels(
    market_data_path: str,
    tickers_path: Optional[str] = None,
    config: Optional[FeatureConfig] = None,
) -> pd.DataFrame:
  """
  High-level convenience function used by training / backtesting code.

  Parameters
  ----------
  market_data_path : str
      Path to the CSV file with OHLCV data (e.g. market_data_ml.csv).
  tickers_path : str, optional
      Optional path to a CSV with tickers to include.
  config : FeatureConfig, optional
      Feature configuration. If None, defaults are used.

  Returns
  -------
  pd.DataFrame
      A DataFrame containing:
        * Core columns: date, ticker, open, high, low, close, volume
        * Engineered feature columns (returns, lags, indicators, etc.)
        * A "target" column suitable for ML tasks.
  """
  raw = load_market_data(market_data_path, tickers_path=tickers_path)
  return engineer_features(raw, config=config)


__all__ = [
  "FeatureConfig",
  "TaskType",
  "load_market_data",
  "engineer_features_for_single_ticker",
  "engineer_features",
  "generate_features_and_labels",
]


if __name__ == "__main__":
  # Minimal CLI for manual testing / quick inspection.
  import argparse

  parser = argparse.ArgumentParser(description="Generate ML features from market data.")
  parser.add_argument(
    "--market-data",
    type=str,
    required=True,
    help="Path to market_data_ml.csv",
  )
  parser.add_argument(
    "--tickers",
    type=str,
    default=None,
    help="Optional path to tickers.csv (subset of tickers to keep).",
  )
  parser.add_argument(
    "--task",
    type=str,
    choices=["classification", "regression"],
    default="classification",
    help="Type of ML task to define the target for.",
  )
  parser.add_argument(
    "--prediction-horizon",
    type=int,
    default=1,
    help="Prediction horizon in days (default: 1).",
  )
  parser.add_argument(
    "--output",
    type=str,
    default=None,
    help="Optional path to save the engineered dataset as CSV. "
    "If not provided, the script just prints a preview.",
  )

  args = parser.parse_args()

  cfg = FeatureConfig(
    prediction_horizon=args.prediction_horizon,
    task=args.task,  # type: ignore[arg-type]
  )

  df_raw = load_market_data(args.market_data, tickers_path=args.tickers)
  df_features = engineer_features(df_raw, config=cfg)

  if args.output is not None:
    df_features.to_csv(args.output, index=False)
    print(f"Saved engineered features to {args.output}")
  else:
    print(df_features.head())
