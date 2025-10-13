# fast_data_generator.py

from __future__ import annotations
import os
import numpy as np
import pandas as pd

TIMESTAMP_FMT = "%Y-%m-%d %H:%M:%S.%f"

def generate_market_csv_fast(
    symbol: str,
    start_price: float,
    filename: str,
    num_ticks: int = 1_000_000,
    volatility: float = 0.01,
    interval: float = 0.0,
    chunk_size: int = 250_000,
    seed: int | None = None,
    append: bool = False,
    restart_price: float | None = None,
):
    """
    Generate 'num_ticks' market data as a Gaussian random walk and write to CSV.

    Robust features:
      - Creates output directory if needed
      - Safe header handling
      - Ensures all prices stay strictly > 0
      - If price ever ≤ 0, immediately restarts from restart_price (default start_price)
    """
    assert num_ticks > 0 and start_price > 0 and volatility >= 0 and chunk_size > 0
    restart_price = restart_price or start_price
    assert restart_price > 0

    # Ensure parent dir exists
    os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)

    rng = np.random.default_rng(seed)
    wrote = 0
    last_price = float(start_price)

    # Handle file + header safely
    if append:
        file_exists = os.path.exists(filename)
        file_empty = (not file_exists) or os.path.getsize(filename) == 0
        mode = "a"
        header_written = not file_empty
    else:
        mode = "w"
        header_written = False
        with open(filename, "w"):
            pass  # truncate file

    base = pd.Timestamp.now()
    step_ns = np.int64(round(interval * 1e9))

    while wrote < num_ticks:
        n = min(chunk_size, num_ticks - wrote)

        # Vectorized deltas
        deltas = rng.normal(0.0, volatility, size=n)
        multipliers = 1.0 + deltas

        # Sequential simulation ensures positivity
        prices = np.empty(n, dtype=float)
        p = last_price
        for i in range(n):
            p *= multipliers[i]
            if p <= 0.5 or not np.isfinite(p):
                # restart at restart_price strictly positive
                p = float(restart_price)
            prices[i] = p
        prices = np.maximum(prices, 1e-6)  # hard floor just in case
        prices = np.around(prices, 2)
        last_price = float(prices[-1])

        # Generate timestamps
        if step_ns == 0:
            ts_series = pd.Series([base]).repeat(n)
        else:
            offsets = pd.to_timedelta(
                np.arange(wrote, wrote + n, dtype=np.int64) * step_ns, unit="ns"
            )
            ts_series = base + offsets
        ts_str = ts_series.dt.strftime(TIMESTAMP_FMT)

        df = pd.DataFrame({
            "timestamp": ts_str,
            "symbol":    np.full(n, symbol, dtype=object),
            "price":     prices,
        })
        df.to_csv(
            filename,
            mode="a",
            header=not header_written,
            index=False,
            lineterminator="\n",
        )
        header_written = True
        wrote += n


if __name__ == "__main__":
    generate_market_csv_fast(
        symbol="AAPL",
        start_price=150.0,
        filename="data/market_data.csv",
        num_ticks=100_000,
        volatility=0.02,
        interval=0.0,
        chunk_size=1000,
        seed=42,
        append=False,
        restart_price=150.0,
    )
    print("market_data.csv generated.")