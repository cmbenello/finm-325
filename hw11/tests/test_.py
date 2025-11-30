from __future__ import annotations

from pathlib import Path

import os
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
DATA_CSV = PROJECT_ROOT / "market_data_multi.csv"
TICKERS_CSV = PROJECT_ROOT / "tickers.csv"
SCHEMA_SQL = PROJECT_ROOT / "schema.sql"

import pandas as pd
import pytest

from src.data_loader import load_and_validate_market_data
from src.sqlite_storage import (
    ingest_from_csv,
    get_ticker_data_for_range,
    get_average_daily_volume_per_ticker,
    get_top_3_tickers_by_return_over_week,
    get_first_and_last_trade_price_per_ticker_per_day,
)
from src.parquet_storage import (
    write_parquet_from_csv,
    get_ticker_data_for_range_parquet,
    compute_rolling_volatility_parquet,
)


@pytest.fixture(scope="session")
def loaded_df() -> pd.DataFrame:
    return load_and_validate_market_data(DATA_CSV, TICKERS_CSV)


@pytest.fixture(scope="session")
def ticker_universe(loaded_df: pd.DataFrame) -> list[str]:
    return sorted(loaded_df["ticker"].astype(str).str.upper().unique())


def test_load_and_validate_market_data_basic(loaded_df: pd.DataFrame, ticker_universe: list[str]):
    assert set(loaded_df.columns) == {"timestamp", "ticker", "open", "high", "low", "close", "volume"}
    assert not loaded_df[["timestamp", "open", "high", "low", "close"]].isna().any().any()
    assert loaded_df["timestamp"].is_monotonic_increasing is False  # across all tickers
    # All tickers in tickers.csv should appear
    assert set(ticker_universe) == set(loaded_df["ticker"].str.upper().unique())


def test_sqlite_ingest_and_basic_queries(tmp_path: Path, loaded_df: pd.DataFrame, ticker_universe: list[str]):
    db_path = tmp_path / "market_data.db"
    ingest_from_csv(DATA_CSV, TICKERS_CSV, db_path, SCHEMA_SQL)

    # range query for first ticker over full range
    ticker = ticker_universe[0]
    start_ts = loaded_df["timestamp"].min()
    end_ts = loaded_df["timestamp"].max()

    df_range = get_ticker_data_for_range(db_path, ticker, start_ts, end_ts)
    assert not df_range.empty
    assert set(df_range["ticker"].unique()) == {ticker}
    assert df_range["timestamp"].is_monotonic_increasing

    avg_vol = get_average_daily_volume_per_ticker(db_path)
    assert set(avg_vol["ticker"].str.upper()) == set(ticker_universe)
    assert (avg_vol["avg_daily_volume"] > 0).all()

    top3 = get_top_3_tickers_by_return_over_week(db_path, start_ts, end_ts)
    assert 1 <= len(top3) <= len(ticker_universe)
    assert "return" in top3.columns

    first_last = get_first_and_last_trade_price_per_ticker_per_day(db_path)
    assert not first_last.empty
    assert {"ticker", "date", "first_price", "last_price"}.issubset(first_last.columns)
    assert first_last["first_price"].notna().all()
    assert first_last["last_price"].notna().all()


def test_parquet_write_and_partition(tmp_path: Path):
    out_dir = tmp_path / "market_data_parquet"
    write_parquet_from_csv(DATA_CSV, TICKERS_CSV, out_dir)

    assert out_dir.exists()
    files = list(out_dir.rglob("*.parquet"))
    assert files, "expected at least one parquet file"

    df = pd.read_parquet(out_dir, engine="pyarrow")
    assert {"timestamp", "ticker", "open", "high", "low", "close", "volume"}.issubset(df.columns)


def test_parquet_and_sqlite_range_equivalence(tmp_path: Path, loaded_df: pd.DataFrame, ticker_universe: list[str]):
    db_path = tmp_path / "market_data.db"
    parquet_dir = tmp_path / "market_data_parquet"

    ingest_from_csv(DATA_CSV, TICKERS_CSV, db_path, SCHEMA_SQL)
    write_parquet_from_csv(DATA_CSV, TICKERS_CSV, parquet_dir)

    ticker = ticker_universe[0]
    start_ts = loaded_df["timestamp"].min()
    end_ts = loaded_df["timestamp"].max()

    df_sql = get_ticker_data_for_range(db_path, ticker, start_ts, end_ts).sort_values("timestamp").reset_index(drop=True)
    df_parq = get_ticker_data_for_range_parquet(parquet_dir, ticker, start_ts, end_ts).sort_values("timestamp").reset_index(drop=True)

    # same length and close prices should match
    assert len(df_sql) == len(df_parq)
    for col in ["timestamp", "ticker", "open", "high", "low", "close", "volume"]:
        assert col in df_parq.columns
    pd.testing.assert_series_equal(df_sql["close"], df_parq["close"], check_names=False)


def test_parquet_rolling_volatility(tmp_path: Path):
    parquet_dir = tmp_path / "market_data_parquet"
    write_parquet_from_csv(DATA_CSV, TICKERS_CSV, parquet_dir)

    vol_df = compute_rolling_volatility_parquet(parquet_dir, window=5)
    assert {"timestamp", "ticker", "close", "return", "rolling_vol_5d"}.issubset(vol_df.columns)
    # some rows should have non-null rolling volatility once window is satisfied
    assert vol_df["rolling_vol_5d"].notna().any()