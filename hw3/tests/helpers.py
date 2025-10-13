from __future__ import annotations
from dataclasses import dataclass, fields, is_dataclass
from typing import List, get_type_hints
import inspect
from datetime import datetime, timedelta
import numpy as np

try:
    # use your project's class if available
    from src.models import MarketDataPoint  # noqa: F401
except Exception:
    # minimal fallback for isolated testing
    @dataclass
    class MarketDataPoint:
        symbol: str
        price: float
        timestamp: datetime | None = None


def _build_tick(symbol: str, price: float, idx: int) -> MarketDataPoint:
    """
    Construct MarketDataPoint using your actual signature.
    Supports common timestamp field names: 'timestamp', 'time', 'ts', 'datetime'.
    Falls back to None or a synthetic datetime if needed.
    """
    cls = MarketDataPoint
    params = list(inspect.signature(cls).parameters.keys())

    # start building kwargs with what we know we have
    kwargs = {}
    if "symbol" in params:
        kwargs["symbol"] = symbol
    if "price" in params:
        kwargs["price"] = float(price)

    # choose a timestamp value
    ts_val = datetime(2020, 1, 1) + timedelta(minutes=idx)

    # try common names
    ts_keys = ["timestamp", "time", "ts", "datetime", "dt"]
    for key in ts_keys:
        if key in params:
            kwargs[key] = ts_val
            break

    # fill any remaining required parameters with simple defaults if they have no default
    sig = inspect.signature(cls)
    for name, p in sig.parameters.items():
        if name in kwargs:
            continue
        if p.default is not inspect._empty:
            continue  # has a default
        # heuristic defaults for common fields
        if name.lower() in {"qty", "quantity", "volume"}:
            kwargs[name] = 0
        elif name.lower() in {"side", "action"}:
            kwargs[name] = None
        elif name.lower() in {"symbol"}:
            kwargs[name] = symbol
        elif name.lower() in {"price"}:
            kwargs[name] = float(price)
        else:
            # last resort: None
            kwargs[name] = None

    return cls(**kwargs)


def make_synthetic_ticks(n: int, symbol: str = "SYN", seed: int = 123) -> List[MarketDataPoint]:
    rng = np.random.default_rng(seed)
    dt = 1.0 / 252
    mu = 0.05
    sigma = 0.2
    prices = [100.0]
    for _ in range(n - 1):
        z = rng.standard_normal()
        prices.append(prices[-1] * np.exp((mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * z))

    return [_build_tick(symbol, float(p), i) for i, p in enumerate(prices)]