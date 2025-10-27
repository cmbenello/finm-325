from __future__ import annotations
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Deque, List, Optional, Any

import json
import math

from src.models import MarketDataPoint, Signal, Action



def load_strategy_params(path: str = "configs/strategy_params.json") -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {
            "mean_reversion": {"window": 20, "z_entry": 1.0, "qty": 10, "min_window": 5},
            "breakout": {"lookback": 20, "qty": 10, "buffer": 0.0}
        }
    try:
        return json.loads(p.read_text())
    except Exception:
        return {
            "mean_reversion": {"window": 20, "z_entry": 1.0, "qty": 10, "min_window": 5},
            "breakout": {"lookback": 20, "qty": 10, "buffer": 0.0}
        }


class Strategy(ABC):
    """
    Abstract Strategy interface.
    Returns a list of Signal(s) for a given tick.
    """
    @abstractmethod
    def generate_signals(self, tick: MarketDataPoint) -> List[Signal]:
        ㅊ


@dataclass
class _RollingSeries:
    maxlen: int
    vals: Deque[float]

    def __init__(self, maxlen: int):
        self.maxlen = int(maxlen)
        self.vals = deque(maxlen=self.maxlen)

    def push(self, x: float) -> None:
        self.vals.append(float(x))

    def __len__(self) -> int:
        return len(self.vals)

    def mean(self) -> Optional[float]:
        if not self.vals:
            return None
        return sum(self.vals) / len(self.vals)

    def std(self) -> Optional[float]:
        n = len(self.vals)
        if n < 2:
            return None
        m = self.mean()
        var = sum((v - m) ** 2 for v in self.vals) / (n - 1)  # sample std for signals
        return math.sqrt(var)

    def max(self) -> Optional[float]:
        return max(self.vals) if self.vals else None

    def min(self) -> Optional[float]:
        return min(self.vals) if self.vals else None



class MeanReversionStrategy(Strategy):
    """
    BUY when price < SMA - z_entry * std
    SELL when price > SMA + z_entry * std
    """
    def __init__(self,
                 window: Optional[int] = None,
                 z_entry: Optional[float] = None,
                 qty: Optional[int] = None,
                 min_window: Optional[int] = None,
                 params_path: str = "configs/strategy_params.json"):
        params = load_strategy_params(params_path).get("mean_reversion", {})
        self.window = int(window if window is not None else params.get("window", 20))
        self.z_entry = float(z_entry if z_entry is not None else params.get("z_entry", 1.0))
        self.qty = int(qty if qty is not None else params.get("qty", 10))
        self.min_window = int(min_window if min_window is not None else params.get("min_window", 5))

        # one price series per symbol
        self._series: Dict[str, _RollingSeries] = {}

    def _series_for(self, symbol: str) -> _RollingSeries:
        if symbol not in self._series:
            self._series[symbol] = _RollingSeries(self.window)
        return self._series[symbol]

    def generate_signals(self, tick: MarketDataPoint) -> List[Signal]:
        s = self._series_for(tick.symbol)
        s.push(tick.price)

        if len(s) < max(self.min_window, 2):
            return []  # not enough data

        mu = s.mean()
        sd = s.std()
        if sd is None or sd == 0:
            return []

        upper = mu + self.z_entry * sd
        lower = mu - self.z_entry * sd

        signals: List[Signal] = []
        if tick.price < lower:
            signals.append(Signal(Action.BUY, tick.symbol, self.qty, tick.price))
        elif tick.price > upper:
            signals.append(Signal(Action.SELL, tick.symbol, self.qty, tick.price))
        return signals


class BreakoutStrategy(Strategy):
    """
    BUY when price breaks above rolling max (plus buffer).
    SELL when price breaks below rolling min (minus buffer).
    """
    def __init__(self,
                 lookback: Optional[int] = None,
                 qty: Optional[int] = None,
                 buffer: Optional[float] = None,
                 params_path: str = "configs/strategy_params.json"):
        params = load_strategy_params(params_path).get("breakout", {})
        self.lookback = int(lookback if lookback is not None else params.get("lookback", 20))
        self.qty = int(qty if qty is not None else params.get("qty", 10))
        self.buffer = float(buffer if buffer is not None else params.get("buffer", 0.0))
        self._series: Dict[str, _RollingSeries] = {}

    def _series_for(self, symbol: str) -> _RollingSeries:
        if symbol not in self._series:
            self._series[symbol] = _RollingSeries(self.lookback)
        return self._series[symbol]

    def generate_signals(self, tick: MarketDataPoint) -> List[Signal]:
        s = self._series_for(tick.symbol)

        # pre-push values to compare with prior window
        prev_max = s.max()
        prev_min = s.min()

        s.push(tick.price)  # include current price in the rolling window

        if len(s) < self.lookback:
            return []

        signals: List[Signal] = []
        # Use previous window extrema; if None, no signals
        if prev_max is not None and tick.price > prev_max + self.buffer:
            signals.append(Signal(Action.BUY, tick.symbol, self.qty, tick.price))
        elif prev_min is not None and tick.price < prev_min - self.buffer:
            signals.append(Signal(Action.SELL, tick.symbol, self.qty, tick.price))
        return signals


class FirstSignalAdapter:
    """
    Adapter so existing engine code expecting a single Signal can use any Strategy
    that returns List[Signal]. If no signals, returns a HOLD.
    """
    def __init__(self, strategy: Strategy):
        self.strategy = strategy

    def generate_signals(self, tick: MarketDataPoint) -> Signal:
        sigs = self.strategy.generate_signals(tick)
        if sigs:
            return sigs[0]
        return Signal(Action.HOLD, tick.symbol, 0, tick.price)