from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Tuple
import time

import pandas as pd
import polars as pl
import psutil


@dataclass
class LoadResult:
    df: Any
    wall_time_s: float
    rss_delta_mb: float
    rows: int
    cols: int

    @property
    def shape(self) -> Tuple[int, int]:
        return self.rows, self.cols


def _rss_mb() -> float:
    return psutil.Process().memory_info().rss / (1024**2)


def _finalize(df: Any, wall_time_s: float, rss_delta_mb: float) -> LoadResult:
    if isinstance(df, pd.DataFrame):
        rows, cols = df.shape
    elif isinstance(df, pl.DataFrame):
        rows, cols = df.height, len(df.columns)
    else:
        raise TypeError("Unsupported dataframe type")
    return LoadResult(df=df, wall_time_s=wall_time_s, rss_delta_mb=rss_delta_mb, rows=rows, cols=cols)


def load_market_data_pandas(path: str | Path) -> LoadResult:
    """
    Load market data via pandas, returning the parsed DataFrame and timing stats.
    """
    path = Path(path)
    rss0 = _rss_mb()
    t0 = time.perf_counter()
    df = pd.read_csv(path, parse_dates=["timestamp"])
    df = df.sort_values(["symbol", "timestamp"], kind="mergesort").reset_index(drop=True)
    wall = time.perf_counter() - t0
    rss_delta = _rss_mb() - rss0
    return _finalize(df, wall, rss_delta)


def load_market_data_polars(path: str | Path) -> LoadResult:
    """
    Load market data via polars, returning the parsed DataFrame and timing stats.
    """
    path = Path(path)
    rss0 = _rss_mb()
    t0 = time.perf_counter()
    df = pl.read_csv(path, try_parse_dates=True, schema_overrides={"timestamp": pl.Datetime})
    # ensure deterministic ordering for downstream joins/plots
    df = df.sort(["symbol", "timestamp"])
    wall = time.perf_counter() - t0
    rss_delta = _rss_mb() - rss0
    return _finalize(df, wall, rss_delta)
