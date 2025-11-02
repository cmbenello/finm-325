from __future__ import annotations
import time
import pandas as pd
import polars as pl

def pandas_rolling_metrics(df: pd.DataFrame, window: int = 20, min_periods: int = 20) -> tuple[pd.DataFrame, float]:
    t0 = time.perf_counter()
    if not isinstance(df.index, pd.DatetimeIndex):
        df = df.set_index("timestamp")
    df = df.sort_values(["symbol", "timestamp"], kind="mergesort")

    g = df.groupby("symbol", sort=False)
    ma = g["price"].transform(lambda s: s.rolling(window, min_periods=min_periods).mean())
    sd = g["price"].transform(lambda s: s.rolling(window, min_periods=min_periods).std(ddof=0))

    ret = g["price"].pct_change()
    mu_r = ret.groupby(df["symbol"]).transform(lambda s: s.rolling(window, min_periods=min_periods).mean())
    sd_r = ret.groupby(df["symbol"]).transform(lambda s: s.rolling(window, min_periods=min_periods).std(ddof=0))
    sharpe = mu_r / sd_r

    out = df.assign(ma20=ma, std20=sd, ret=ret, sharpe20=sharpe)
    wall = time.perf_counter() - t0
    return out, wall

def polars_rolling_metrics(df: pl.DataFrame, window: int = 20, min_periods: int = 20) -> tuple[pl.DataFrame, float]:
    t0 = time.perf_counter()
    df = df.sort(["symbol", "timestamp"])
    out = (
        df
        .with_columns([
            pl.col("price").rolling_mean(window, min_samples=min_periods).over("symbol").alias("ma20"),
            pl.col("price").rolling_std(window, min_samples=min_periods).over("symbol").alias("std20"),
        ])
        .with_columns([
            (pl.col("price") / pl.col("price").shift(1) - 1).over("symbol").alias("ret")
        ])
        .with_columns([
            pl.col("ret").rolling_mean(window, min_samples=min_periods).over("symbol").alias("_mu_r"),
            pl.col("ret").rolling_std(window, min_samples=min_periods).over("symbol").alias("_sd_r"),
        ])
        .with_columns([
            (pl.col("_mu_r") / pl.col("_sd_r")).alias("sharpe20")
        ])
        .drop(["_mu_r", "_sd_r"])
    )
    wall = time.perf_counter() - t0
    return out, wall