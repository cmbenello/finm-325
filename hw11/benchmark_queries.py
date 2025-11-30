import os
import time
from pathlib import Path

import pandas as pd
import sqlite3

from src.sqlite_storage import (
    get_ticker_data_for_range,
    get_average_daily_volume_per_ticker,
    get_top_3_tickers_by_return_over_week,
    get_first_and_last_trade_price_per_ticker_per_day,
)
from src.parquet_storage import (
    get_ticker_data_for_range_parquet,
    compute_rolling_volatility_parquet,
)


DB_PATH = Path("market_data.db")
PARQUET_DIR = Path("market_data")


def time_call(fn, *args, repeats: int = 3, **kwargs):
    times = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        _ = fn(*args, **kwargs)
        t1 = time.perf_counter()
        times.append(t1 - t0)
    avg = sum(times) / len(times)
    return avg, min(times), max(times)


def sqlite_task_1_tsla_range():
    start = pd.Timestamp("2025-11-17")
    end = pd.Timestamp("2025-11-18")
    return get_ticker_data_for_range(DB_PATH, "TSLA", start, end)


def sqlite_task_2_avg_daily_volume():
    return get_average_daily_volume_per_ticker(DB_PATH)


def _sqlite_full_period(db_path: Path):
    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql_query(
            "SELECT MIN(timestamp) AS min_ts, MAX(timestamp) AS max_ts FROM prices;",
            conn,
        )
    start = pd.to_datetime(df.loc[0, "min_ts"])
    end = pd.to_datetime(df.loc[0, "max_ts"])
    return start, end


def sqlite_task_3_top3_full_period():
    start, end = _sqlite_full_period(DB_PATH)
    return get_top_3_tickers_by_return_over_week(DB_PATH, start, end)


def sqlite_task_4_first_last_per_day():
    return get_first_and_last_trade_price_per_ticker_per_day(DB_PATH)


def parquet_task_1_aapl_rolling_5min():
    df = pd.read_parquet(PARQUET_DIR, engine="pyarrow")
    df["ticker"] = df["ticker"].astype(str).str.upper()
    if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="raise")
    df = df[df["ticker"] == "AAPL"].copy()
    df = df.sort_values("timestamp")
    df = df.set_index("timestamp")
    df["rolling_5min_close"] = df["close"].rolling("5min").mean()
    df = df.reset_index()
    return df


def parquet_task_2_rolling_vol_5d():
    return compute_rolling_volatility_parquet(PARQUET_DIR, window=5)


def sqlite_aapl_rolling_5min():
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query(
            """
            SELECT p.timestamp, t.symbol AS ticker, p.close
            FROM prices p
            JOIN tickers t ON p.ticker_id = t.ticker_id
            WHERE t.symbol = ?
            ORDER BY p.timestamp
            """,
            conn,
            params=("AAPL",),
            parse_dates=["timestamp"],
        )
    df["ticker"] = df["ticker"].astype(str).str.upper()
    df = df.sort_values("timestamp")
    df = df.set_index("timestamp")
    df["rolling_5min_close"] = df["close"].rolling("5min").mean()
    df = df.reset_index()
    return df


def sqlite_file_size_bytes() -> int:
    return DB_PATH.stat().st_size


def parquet_file_size_bytes() -> int:
    total = 0
    for root, _, files in os.walk(PARQUET_DIR):
        for f in files:
            total += os.path.getsize(Path(root) / f)
    return total


def main():
    print("SQLite3 Task 1: TSLA between 2025-11-17 and 2025-11-18")
    tsla = sqlite_task_1_tsla_range()
    print(tsla.head())

    print("\nSQLite3 Task 2: average daily volume per ticker")
    avg_vol = sqlite_task_2_avg_daily_volume()
    print(avg_vol)

    print("\nSQLite3 Task 3: top 3 tickers by return over full period")
    top3 = sqlite_task_3_top3_full_period()
    print(top3)

    print("\nSQLite3 Task 4: first and last trade price per ticker per day")
    first_last = sqlite_task_4_first_last_per_day()
    print(first_last.head())

    print("\nParquet Task 1: AAPL 5-minute rolling average of close price")
    aapl_roll = parquet_task_1_aapl_rolling_5min()
    print(aapl_roll.head())

    print("\nParquet Task 2: 5-day rolling volatility per ticker")
    vol5 = parquet_task_2_rolling_vol_5d()
    print(vol5.head())

    print("\nParquet Task 3: compare query time and file size with SQLite3 for Task 1")
    avg_sql, _, _ = time_call(sqlite_aapl_rolling_5min)
    avg_parq, _, _ = time_call(parquet_task_1_aapl_rolling_5min)

    sqlite_size = sqlite_file_size_bytes()
    parquet_size = parquet_file_size_bytes()

    print("SQLite AAPL rolling 5min avg time: {:.6f} s".format(avg_sql))
    print("Parquet AAPL rolling 5min avg time: {:.6f} s".format(avg_parq))
    print("SQLite file size (bytes):", sqlite_size)
    print("Parquet file size (bytes):", parquet_size)


if __name__ == "__main__":
    main()