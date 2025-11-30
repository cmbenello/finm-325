

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

from .data_loader import load_and_validate_market_data


def _to_path(path: str | Path) -> Path:
    return path if isinstance(path, Path) else Path(path)


def write_parquet_from_dataframe(df: pd.DataFrame, out_dir: str | Path) -> None:
    """Write partitioned Parquet dataset (partitioned by ticker)."""
    out_path = _to_path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # Rely on pyarrow dataset writer to create ticker=... partitions
    df.to_parquet(
        out_path,
        engine="pyarrow",
        partition_cols=["ticker"],
        index=False,
    )


def write_parquet_from_csv(
    market_csv: str | Path,
    tickers_csv: str | Path,
    out_dir: str | Path,
) -> None:
    """Load CSVs, validate, and write partitioned Parquet dataset."""
    df = load_and_validate_market_data(market_csv, tickers_csv)
    write_parquet_from_dataframe(df, out_dir)


def _coerce_timestamp(ts) -> str:
    if isinstance(ts, pd.Timestamp):
        return ts.to_pydatetime().isoformat()
    return str(ts)


def _load_parquet_dataset(parquet_dir: str | Path) -> pd.DataFrame:
    path = _to_path(parquet_dir)
    df = pd.read_parquet(path, engine="pyarrow")
    # Normalise ticker case for robustness
    df["ticker"] = df["ticker"].astype(str).str.upper()
    if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="raise")
    df = df.sort_values(["ticker", "timestamp"]).reset_index(drop=True)
    return df


def get_ticker_data_for_range_parquet(
    parquet_dir: str | Path,
    ticker: str,
    start_ts,
    end_ts,
) -> pd.DataFrame:
    """Return OHLCV for ticker over timestamp range from Parquet dataset."""
    df = _load_parquet_dataset(parquet_dir)

    ticker_u = ticker.upper()
    start_s = pd.to_datetime(_coerce_timestamp(start_ts))
    end_s = pd.to_datetime(_coerce_timestamp(end_ts))

    mask = (
        (df["ticker"] == ticker_u)
        & (df["timestamp"] >= start_s)
        & (df["timestamp"] <= end_s)
    )
    out = df.loc[mask, [
        "timestamp",
        "ticker",
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]].copy()
    out = out.sort_values("timestamp").reset_index(drop=True)
    return out


def compute_rolling_volatility_parquet(
    parquet_dir: str | Path,
    window: int = 5,
) -> pd.DataFrame:
    """Compute rolling volatility of daily returns per ticker from Parquet dataset."""
    df = _load_parquet_dataset(parquet_dir)

    df = df.sort_values(["ticker", "timestamp"]).reset_index(drop=True)

    def _per_ticker(group: pd.DataFrame) -> pd.DataFrame:
        group = group.sort_values("timestamp")
        group["return"] = group["close"].pct_change()
        group[f"rolling_vol_{window}d"] = (
            group["return"].rolling(window=window, min_periods=window).std()
        )
        return group

    out = df.groupby("ticker", group_keys=False).apply(_per_ticker)
    out = out.reset_index(drop=True)
    return out[[
        "timestamp",
        "ticker",
        "close",
        "return",
        f"rolling_vol_{window}d",
    ]]


__all__ = [
    "write_parquet_from_dataframe",
    "write_parquet_from_csv",
    "get_ticker_data_for_range_parquet",
    "compute_rolling_volatility_parquet",
]