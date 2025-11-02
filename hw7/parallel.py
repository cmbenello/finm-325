from __future__ import annotations
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
import os
import psutil
import pandas as pd
import polars as pl
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed

def _rss_mb() -> float:
    return psutil.Process(os.getpid()).memory_info().rss / (1024**2)

def _summary(df_rows: int, df_cols: int, t: float, rss_delta: Optional[float]) -> str:
    rd = f"{rss_delta:.2f} MB" if rss_delta is not None else "?"
    return f"rows={df_rows} cols={df_cols} time={t:.3f}s rss_delta={rd}"

def _pandas_metrics_one(df_sym: pd.DataFrame, window: int, min_periods: int) -> pd.DataFrame:
    s = df_sym.sort_values("timestamp")
    s = s.set_index("timestamp", drop=True)
    price = s["price"]
    ma = price.rolling(window, min_periods=min_periods).mean()
    sd = price.rolling(window, min_periods=min_periods).std(ddof=0)
    ret = price.pct_change()
    mu_r = ret.rolling(window, min_periods=min_periods).mean()
    sd_r = ret.rolling(window, min_periods=min_periods).std(ddof=0)
    sharpe = mu_r / sd_r
    out = s.assign(ma20=ma, std20=sd, ret=ret, sharpe20=sharpe).reset_index()
    return out

def pandas_threaded(df: pd.DataFrame, window: int = 20, min_periods: int = 20, max_workers: Optional[int] = None) -> Tuple[pd.DataFrame, float, Optional[float]]:
    t0 = time.perf_counter()
    rss0 = _rss_mb()
    parts: List[pd.DataFrame] = []
    by = [g for _, g in df.groupby("symbol", sort=False)]
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = [ex.submit(_pandas_metrics_one, g, window, min_periods) for g in by]
        for f in as_completed(futs):
            parts.append(f.result())
    out = pd.concat(parts, ignore_index=True).sort_values(["symbol", "timestamp"], kind="mergesort")
    t = time.perf_counter() - t0
    rss_delta = _rss_mb() - rss0
    return out, t, rss_delta

def _pandas_metrics_one_pickle(args: Tuple[pd.DataFrame, int, int]) -> pd.DataFrame:
    g, window, min_periods = args
    return _pandas_metrics_one(g, window, min_periods)

def pandas_multiproc(df: pd.DataFrame, window: int = 20, min_periods: int = 20, max_workers: Optional[int] = None, chunksize: int = 1) -> Tuple[pd.DataFrame, float, Optional[float]]:
    t0 = time.perf_counter()
    rss0 = _rss_mb()
    parts: List[pd.DataFrame] = []
    by = [g for _, g in df.groupby("symbol", sort=False)]
    with ProcessPoolExecutor(max_workers=max_workers) as ex:
        futs = [ex.submit(_pandas_metrics_one_pickle, (g, window, min_periods)) for g in by]
        for f in as_completed(futs):
            parts.append(f.result())
    out = pd.concat(parts, ignore_index=True).sort_values(["symbol", "timestamp"], kind="mergesort")
    t = time.perf_counter() - t0
    rss_delta = _rss_mb() - rss0
    return out, t, rss_delta


def _polars_metrics_one(df_sym: pl.DataFrame, window: int, min_periods: int) -> pl.DataFrame:
    s = df_sym.sort("timestamp")
    out = (
        s
        .with_columns([
            pl.col("price").rolling_mean(window, min_samples=min_periods).alias("ma20"),
            pl.col("price").rolling_std(window, min_samples=min_periods).alias("std20"),
        ])
        .with_columns([
            (pl.col("price") / pl.col("price").shift(1) - 1).alias("ret")
        ])
        .with_columns([
            pl.col("ret").rolling_mean(window, min_samples=min_periods).alias("_mu_r"),
            pl.col("ret").rolling_std(window, min_samples=min_periods).alias("_sd_r"),
        ])
        .with_columns([
            (pl.col("_mu_r") / pl.col("_sd_r")).alias("sharpe20")
        ])
        .drop(["_mu_r", "_sd_r"])
    )
    return out

def _polars_group_parts(df: pl.DataFrame) -> List[Tuple[str, pl.DataFrame]]:
    """Return (symbol, DataFrame) tuples compatible across polars versions."""
    try:
        parts_dict = df.partition_by("symbol", maintain_order=True, as_dict=True)
        return [(str(sym), g) for sym, g in parts_dict.items()]
    except TypeError:
        # older polars without as_dict argument
        parts = df.partition_by("symbol", maintain_order=True)
        out: List[Tuple[str, pl.DataFrame]] = []
        for g in parts:
            sym_val = g["symbol"][0]
            out.append((str(sym_val), g))
        return out


def polars_threaded(df: pl.DataFrame, window: int = 20, min_periods: int = 20, max_workers: Optional[int] = None) -> Tuple[pl.DataFrame, float, Optional[float]]:
    t0 = time.perf_counter()
    rss0 = _rss_mb()
    parts = _polars_group_parts(df)
    out_parts: List[pl.DataFrame] = []
    def job(x):
        sym, g = x
        return (
            _polars_metrics_one(g, window, min_periods)
            .with_columns(pl.lit(str(sym)).cast(pl.Utf8).alias("symbol"))
        )
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = [ex.submit(job, x) for x in parts]
        for f in as_completed(futs):
            out_parts.append(f.result())
    out = pl.concat(out_parts)
    # normalize symbol to scalar Utf8 (handles accidental List/Array dtypes)
    dtype = out.schema.get("symbol")
    if dtype is not None and ("List" in str(dtype) or "Array" in str(dtype)):
        out = out.with_columns(pl.col("symbol").arr.first().cast(pl.Utf8))
    else:
        out = out.with_columns(pl.col("symbol").cast(pl.Utf8))
    out = out.sort(["symbol", "timestamp"])
    t = time.perf_counter() - t0
    rss_delta = _rss_mb() - rss0
    return out, t, rss_delta

def _polars_metrics_one_pickle(args: Tuple[str, List[Dict[str, Any]], Dict[str, pl.DataType], int, int]) -> pl.DataFrame:
    sym, rows, schema, window, min_periods = args
    g = pl.DataFrame(rows, schema=schema)
    return _polars_metrics_one(g, window, min_periods).with_columns(
        [pl.lit(str(sym)).cast(pl.Utf8).alias("symbol")]
    )

def polars_multiproc(df: pl.DataFrame, window: int = 20, min_periods: int = 20, max_workers: Optional[int] = None) -> Tuple[pl.DataFrame, float, Optional[float]]:
    t0 = time.perf_counter()
    rss0 = _rss_mb()
    schema = df.schema
    parts: List[Tuple[str, List[Dict[str, Any]]]] = []
    for sym, g in _polars_group_parts(df):
        parts.append((sym, g.to_dicts()))
    out_parts: List[pl.DataFrame] = []
    with ProcessPoolExecutor(max_workers=max_workers) as ex:
        futs = [ex.submit(_polars_metrics_one_pickle, (sym, rows, schema, window, min_periods)) for sym, rows in parts]
        for f in as_completed(futs):
            out_parts.append(f.result())
    out = pl.concat(out_parts)
    dtype = out.schema.get("symbol")
    if dtype is not None and ("List" in str(dtype) or "Array" in str(dtype)):
        out = out.with_columns(pl.col("symbol").arr.first().cast(pl.Utf8))
    else:
        out = out.with_columns(pl.col("symbol").cast(pl.Utf8))
    out = out.sort(["symbol", "timestamp"])
    t = time.perf_counter() - t0
    rss_delta = _rss_mb() - rss0
    return out, t, rss_delta
