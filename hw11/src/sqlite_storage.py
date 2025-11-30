from __future__ import annotations

from pathlib import Path
from typing import Iterable

import sqlite3
import pandas as pd

from .data_loader import load_and_validate_market_data


def _to_path(path: str | Path) -> Path:
    return path if isinstance(path, Path) else Path(path)


def init_sqlite_db(db_path: str | Path, schema_sql_path: str | Path) -> None:
    """Initialize SQLite DB using schema.sql."""

    db_path = _to_path(db_path)
    schema_sql_path = _to_path(schema_sql_path)

    with schema_sql_path.open("r", encoding="utf-8") as f:
        schema_sql = f.read()

    with sqlite3.connect(db_path) as conn:
        conn.executescript(schema_sql)
        conn.commit()


def populate_from_dataframe(db_path: str | Path, df: pd.DataFrame) -> None:
    """Insert tickers and prices from DataFrame."""

    db_path = _to_path(db_path)

    # Prepare dimension table contents
    tickers = sorted(df["ticker"].astype(str).str.upper().unique())
    ticker_rows = [(i + 1, symbol) for i, symbol in enumerate(tickers)]
    ticker_id_map = {symbol: i + 1 for i, symbol in enumerate(tickers)}

    price_rows: list[tuple] = []
    for row in df.itertuples(index=False):
        ts = getattr(row, "timestamp")
        symbol = str(getattr(row, "ticker")).upper()
        price_rows.append(
            (
                ts.isoformat(),
                ticker_id_map[symbol],
                float(getattr(row, "open")),
                float(getattr(row, "high")),
                float(getattr(row, "low")),
                float(getattr(row, "close")),
                float(getattr(row, "volume")),
            )
        )

    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()

        # Insert into tickers table
        cur.executemany(
            "INSERT INTO tickers (ticker_id, symbol) VALUES (?, ?);",
            ticker_rows,
        )

        # Insert into prices table
        cur.executemany(
            """
            INSERT INTO prices
                (timestamp, ticker_id, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            price_rows,
        )

        conn.commit()


def ingest_from_csv(
    market_csv: str | Path,
    tickers_csv: str | Path,
    db_path: str | Path,
    schema_sql_path: str | Path,
) -> None:
    """Load CSVs, validate, initialize DB, insert rows."""

    df = load_and_validate_market_data(market_csv, tickers_csv)
    init_sqlite_db(db_path, schema_sql_path)
    populate_from_dataframe(db_path, df)


def _coerce_timestamp(ts) -> str:
    if isinstance(ts, pd.Timestamp):
        return ts.to_pydatetime().isoformat()
    return str(ts)


def get_ticker_data_for_range(
    db_path: str | Path,
    ticker: str,
    start_ts,
    end_ts,
) -> pd.DataFrame:
    """Return OHLCV for ticker over timestamp range."""

    db_path = _to_path(db_path)
    ticker = ticker.upper()
    start_s = _coerce_timestamp(start_ts)
    end_s = _coerce_timestamp(end_ts)

    query = """
        SELECT
            p.timestamp,
            t.symbol AS ticker,
            p.open,
            p.high,
            p.low,
            p.close,
            p.volume
        FROM prices p
        JOIN tickers t ON p.ticker_id = t.ticker_id
        WHERE t.symbol = ?
          AND p.timestamp >= ?
          AND p.timestamp <= ?
        ORDER BY p.timestamp;
    """

    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql_query(
            query,
            conn,
            params=(ticker, start_s, end_s),
            parse_dates=["timestamp"],
        )

    return df


def get_average_daily_volume_per_ticker(db_path: str | Path) -> pd.DataFrame:
    """Compute average daily volume per ticker."""

    db_path = _to_path(db_path)

    query = """
        WITH daily AS (
            SELECT
                t.symbol AS ticker,
                DATE(p.timestamp) AS trading_day,
                SUM(p.volume) AS daily_volume
            FROM prices p
            JOIN tickers t ON p.ticker_id = t.ticker_id
            GROUP BY t.symbol, trading_day
        )
        SELECT
            ticker,
            AVG(daily_volume) AS avg_daily_volume
        FROM daily
        GROUP BY ticker
        ORDER BY ticker;
    """

    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql_query(query, conn)

    return df


def get_top_3_tickers_by_return_over_week(
    db_path: str | Path,
    week_start,
    week_end,
) -> pd.DataFrame:
    """Top 3 tickers by weekly return."""

    db_path = _to_path(db_path)
    start_s = _coerce_timestamp(week_start)
    end_s = _coerce_timestamp(week_end)

    query = """
        WITH bounds AS (
            SELECT
                t.symbol AS ticker,
                MIN(p.timestamp) AS first_ts,
                MAX(p.timestamp) AS last_ts
            FROM prices p
            JOIN tickers t ON p.ticker_id = t.ticker_id
            WHERE p.timestamp >= ? AND p.timestamp < ?
            GROUP BY t.symbol
        ),
        first_price AS (
            SELECT
                b.ticker,
                p.close AS first_close
            FROM bounds b
            JOIN prices p
              ON p.timestamp = b.first_ts
            JOIN tickers t
              ON t.ticker_id = p.ticker_id AND t.symbol = b.ticker
        ),
        last_price AS (
            SELECT
                b.ticker,
                p.close AS last_close
            FROM bounds b
            JOIN prices p
              ON p.timestamp = b.last_ts
            JOIN tickers t
              ON t.ticker_id = p.ticker_id AND t.symbol = b.ticker
        )
        SELECT
            f.ticker,
            (l.last_close - f.first_close) / f.first_close AS return
        FROM first_price f
        JOIN last_price l ON l.ticker = f.ticker
        ORDER BY return DESC
        LIMIT 3;
    """

    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql_query(query, conn, params=(start_s, end_s))

    return df


def get_first_and_last_trade_price_per_ticker_per_day(
    db_path: str | Path,
) -> pd.DataFrame:
    """First and last close price per ticker per day."""

    db_path = _to_path(db_path)

    query = """
        WITH day_bounds AS (
            SELECT
                t.symbol AS ticker,
                DATE(p.timestamp) AS trading_day,
                MIN(p.timestamp) AS first_ts,
                MAX(p.timestamp) AS last_ts
            FROM prices p
            JOIN tickers t ON p.ticker_id = t.ticker_id
            GROUP BY t.symbol, trading_day
        ),
        first_trade AS (
            SELECT
                d.ticker,
                d.trading_day,
                p.close AS first_price
            FROM day_bounds d
            JOIN prices p
              ON p.timestamp = d.first_ts
            JOIN tickers t
              ON t.ticker_id = p.ticker_id AND t.symbol = d.ticker
        ),
        last_trade AS (
            SELECT
                d.ticker,
                d.trading_day,
                p.close AS last_price
            FROM day_bounds d
            JOIN prices p
              ON p.timestamp = d.last_ts
            JOIN tickers t
              ON t.ticker_id = p.ticker_id AND t.symbol = d.ticker
        )
        SELECT
            f.ticker,
            f.trading_day AS date,
            f.first_price,
            l.last_price
        FROM first_trade f
        JOIN last_trade l
          ON f.ticker = l.ticker AND f.trading_day = l.trading_day
        ORDER BY f.ticker, f.trading_day;
    """

    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql_query(query, conn, parse_dates=["date"])

    return df


__all__ = [
    "init_sqlite_db",
    "populate_from_dataframe",
    "ingest_from_csv",
    "get_ticker_data_for_range",
    "get_average_daily_volume_per_ticker",
    "get_top_3_tickers_by_return_over_week",
    "get_first_and_last_trade_price_per_ticker_per_day",
]
