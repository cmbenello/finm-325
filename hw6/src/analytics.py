# decorator.py
from __future__ import annotations
from collections import deque
from typing import Optional, Dict, Any
import math


class MetricsSubject:
    """
    Minimal subject that exposes a symbol and get_metrics().
    Decorators wrap this (or any object providing get_metrics()).
    """
    def __init__(self, symbol: str):
        if not isinstance(symbol, str) or not symbol:
            raise ValueError("symbol must be a non-empty string")
        self.symbol = symbol

    def get_metrics(self) -> Dict[str, Any]:
        return {"symbol": self.symbol}

class MetricsDecorator:
    """
    Wraps a subject that has .get_metrics() and optional observe_* methods.
    Designed to be stacked. Call observe_* (or ingest_tick) once on the OUTERMOST decorator.
    """
    def __init__(self, base):
        self._base = base
        self.symbol = getattr(base, "symbol", None) 

    def _forward(self, name: str, *args, **kwargs) -> None:
        fn = getattr(self._base, name, None)
        if callable(fn):
            fn(*args, **kwargs)

    def get_metrics(self) -> Dict[str, Any]:
        base_metrics = self._base.get_metrics() if hasattr(self._base, "get_metrics") else {}
        return dict(base_metrics)

    def observe_price(self, price: float, prev_price: Optional[float] = None) -> None:
        """For volatility & drawdown layers."""
        self._forward("observe_price", price, prev_price)

    def observe_market_pair(
        self,
        price: float,
        prev_price: Optional[float],
        mkt_price: Optional[float],
        mkt_prev_price: Optional[float],
    ) -> None:
        """For beta layers (asset vs market)."""
        self._forward("observe_market_pair", price, prev_price, mkt_price, mkt_prev_price)

    def ingest_tick(
        self,
        price: float,
        prev_price: Optional[float] = None,
        mkt_price: Optional[float] = None,
        mkt_prev_price: Optional[float] = None,
    ) -> None:
        self.observe_price(price, prev_price)
        if mkt_price is not None:
            self.observe_market_pair(price, prev_price, mkt_price, mkt_prev_price)

    def reset(self) -> None:
        fn = getattr(self._base, "reset", None)
        if callable(fn):
            fn()

class VolatilityDecorator(MetricsDecorator):
    def __init__(self, base, window: int = 20):
        super().__init__(base)
        self.window = int(window)
        self._rets = deque(maxlen=self.window)

    def observe_price(self, price: float, prev_price: Optional[float] = None) -> None:
        super().observe_price(price, prev_price)  
        if prev_price is not None and prev_price != 0:
            r = float(price) / float(prev_price) - 1.0
            self._rets.append(r)

    def get_metrics(self) -> Dict[str, Any]:
        m = super().get_metrics()
        n = len(self._rets)
        if n >= 1:
            mu = sum(self._rets) / n
            # Population variance:
            var = sum((r - mu) ** 2 for r in self._rets) / n
            m["volatility"] = math.sqrt(var)
        else:
            m["volatility"] = None
        return m

    def reset(self) -> None:
        self._rets.clear()
        super().reset()

class BetaDecorator(MetricsDecorator):
    """
    Rolling CAPM beta using simple returns. Beta = Cov(r, r_m) / Var(r_m).
    """
    def __init__(self, base, window: int = 60):
        super().__init__(base)
        self.window = int(window)
        self._r = deque(maxlen=self.window)    
        self._rm = deque(maxlen=self.window)   

    def observe_market_pair(
        self,
        price: float,
        prev_price: Optional[float],
        mkt_price: Optional[float],
        mkt_prev_price: Optional[float],
    ) -> None:
        super().observe_market_pair(price, prev_price, mkt_price, mkt_prev_price)
        if (
            prev_price is not None and prev_price != 0 and
            mkt_prev_price is not None and mkt_prev_price != 0
        ):
            r = float(price) / float(prev_price) - 1.0
            rm = float(mkt_price) / float(mkt_prev_price) - 1.0
            self._r.append(r)
            self._rm.append(rm)

    def get_metrics(self) -> Dict[str, Any]:
        m = super().get_metrics()
        n = min(len(self._r), len(self._rm))
        if n >= 2:
            mr = sum(self._r) / n
            mrm = sum(self._rm) / n
            cov = sum((a - mr) * (b - mrm) for a, b in zip(self._r, self._rm)) / n
            varm = sum((b - mrm) ** 2 for b in self._rm) / n
            m["beta"] = (cov / varm) if varm != 0 else None
        else:
            m["beta"] = None
        return m

    def reset(self) -> None:
        self._r.clear()
        self._rm.clear()
        super().reset()

class DrawdownDecorator(MetricsDecorator):
    """
    Max drawdown computed on price path: min over t of (P_t / peak - 1).
    Returns a non-positive number (e.g., -0.27 for -27%).
    """
    def __init__(self, base):
        super().__init__(base)
        self._peak: Optional[float] = None
        self._max_dd: float = 0.0

    def observe_price(self, price: float, prev_price: Optional[float] = None) -> None:
        super().observe_price(price, prev_price)
        p = float(price)
        self._peak = p if self._peak is None else max(self._peak, p)
        if self._peak and self._peak > 0:
            dd = p / self._peak - 1.0
            self._max_dd = min(self._max_dd, dd)

    def get_metrics(self) -> Dict[str, Any]:
        m = super().get_metrics()
        m["max_drawdown"] = self._max_dd
        return m

    def reset(self) -> None:
        self._peak = None
        self._max_dd = 0.0
        super().reset()