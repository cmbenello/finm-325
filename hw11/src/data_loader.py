from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

# Canonical column names
REQUIRED_COLUMNS = [
    "timestamp",
    "ticker",
    "open",
    "high",
    "low",
    "close",
    "volume",
]


def _to_path(path: str | Path) -> Path:
    """Helper to normalize paths to Path objects."""
    return path if isinstance(path, Path) else Path(path)


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of df with normalized column names and dtypes.

    - Lower-case and strip all column names
    - Enforce presence of REQUIRED_COLUMNS
    - Rename obvious variants (e.g. "symbol" -> "ticker")
    - Parse the timestamp column to pandas datetime
    """

    # Basic normalization: lower-case and strip whitespace
    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]

    # Handle common synonyms for key fields
    rename_map: dict[str, str] = {}
    if "symbol" in df.columns and "ticker" not in df.columns:
        rename_map["symbol"] = "ticker"
    if "datetime" in df.columns and "timestamp" not in df.columns:
        rename_map["datetime"] = "timestamp"
    if "date" in df.columns and "timestamp" not in df.columns:
        rename_map["date"] = "timestamp"

    if rename_map:
        df = df.rename(columns=rename_map)

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Input market data is missing required columns: {missing}")

    # Keep only the columns we care about, in a stable order
    df = df[REQUIRED_COLUMNS].copy()

    # Parse timestamp
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="raise")

    # Enforce dtypes for numeric columns when possible
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="raise")

    # Sort for convenience and downstream use
    df = df.sort_values(["ticker", "timestamp"]).reset_index(drop=True)

    return df


def _load_ticker_universe(tickers_csv: str | Path) -> pd.Series:
    """Load the list of allowed tickers from tickers.csv.

    Returns a Series of ticker symbols, upper-cased.
    """
    path = _to_path(tickers_csv)
    tickers_df = pd.read_csv(path)

    # Normalize column names
    tickers_df.columns = [c.strip().lower() for c in tickers_df.columns]

    # Support either a "ticker" or "symbol" column
    if "ticker" in tickers_df.columns:
        col = "ticker"
    elif "symbol" in tickers_df.columns:
        col = "symbol"
    else:
        raise ValueError("tickers.csv must contain a 'ticker' or 'symbol' column")

    tickers = tickers_df[col].astype(str).str.upper()
    return tickers


def _validate_no_missing_prices(df: pd.DataFrame) -> None:
    """Ensure there are no missing timestamps or price fields.

    Raises ValueError if any required column has missing values.
    """
    cols_to_check: Iterable[str] = ["timestamp", "open", "high", "low", "close"]

    missing_counts = {c: int(df[c].isna().sum()) for c in cols_to_check}
    problematic = {c: n for c, n in missing_counts.items() if n > 0}
    if problematic:
        raise ValueError(
            "Market data contains missing values in required columns: "
            + ", ".join(f"{c}={n}" for c, n in problematic.items())
        )


def _validate_tickers_covered(df: pd.DataFrame, tickers: pd.Series) -> None:
    """Ensure that all tickers in tickers.csv appear in the market data.

    Raises ValueError if any expected ticker is missing.
    """
    data_tickers = set(df["ticker"].astype(str).str.upper().unique())
    expected = set(tickers.astype(str).str.upper())

    missing = sorted(expected - data_tickers)
    if missing:
        raise ValueError(
            "The following tickers from tickers.csv are missing in market_data_multi.csv: "
            + ", ".join(missing)
        )


def load_and_validate_market_data(
    market_csv: str | Path,
    tickers_csv: str | Path,
) -> pd.DataFrame:
    """Load multi-ticker OHLCV data and validate it.

    This is the main entry point used by the rest of the assignment.

    Steps:
    1. Load raw CSV data with pandas.
    2. Normalize column names and dtypes.
    3. Verify there are no missing timestamps or price fields.
    4. Ensure that all tickers listed in tickers.csv are present.

    Returns a cleaned DataFrame with columns:
        timestamp (datetime64[ns])
        ticker (str)
        open, high, low, close, volume (numeric)
    """

    market_path = _to_path(market_csv)
    if not market_path.exists():
        raise FileNotFoundError(f"Market data CSV not found: {market_path}")

    tickers_path = _to_path(tickers_csv)
    if not tickers_path.exists():
        raise FileNotFoundError(f"Tickers CSV not found: {tickers_path}")

    raw_df = pd.read_csv(market_path)
    normalized_df = _normalize_columns(raw_df)

    # Load the ticker universe and validate coverage
    tickers = _load_ticker_universe(tickers_path)

    # Validation checks
    _validate_no_missing_prices(normalized_df)
    _validate_tickers_covered(normalized_df, tickers)

    return normalized_df


__all__ = [
    "load_and_validate_market_data",
]
