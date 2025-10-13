from abc import ABC, abstractmethod
from src.models import MarketDataPoint, Action, Signal
import numpy as np
from collections import deque



class Strategy(ABC):
    @abstractmethod
    def generate_signals(self, tick: MarketDataPoint) -> Signal:
        raise NotImplementedError("Subclasses must implement this method")


class NaiveMovingAverageStrategy(Strategy):
    """
    Per tick time: O(long_window)  (means over slices of size s and L)
    Space: O(n)  (stores all prices)
    Memory vs windowed: uses O(n) vs O(L) for bounded-window approach
    """
    def __init__(self, short_window: int, long_window: int):
        if short_window >= long_window:
            raise ValueError("short_window must be < long_window")
        self.short_window = int(short_window)
        self.long_window = int(long_window)
        self.prices: list[float] = []  # grows with n -> O(n) space

    def generate_signals(self, tick: MarketDataPoint):
        self.prices.append(tick.price)  # append is amortized O(1)

        # warm-up check O(1)
        if len(self.prices) < self.long_window + 1:
            return Signal(Action.HOLD, tick.symbol, qty=0, price=tick.price)

        p = self.prices

        # np.mean over k items costs O(k)
        ma_fast = float(np.mean(p[-self.short_window:]))        # O(short_window)
        ma_slow = float(np.mean(p[-self.long_window:]))         # O(long_window)

        # previous windows: same costs
        ma_fast_prev = float(np.mean(p[-self.short_window-1:-1]))  # O(short_window)
        ma_slow_prev = float(np.mean(p[-self.long_window-1:-1]))   # O(long_window)

        is_above = ma_fast > ma_slow      # O(1)
        was_above = ma_fast_prev > ma_slow_prev  # O(1)

        if is_above and not was_above:
            return Signal(Action.BUY, tick.symbol, qty=1, price=tick.price)
        else:
            return Signal(Action.HOLD, tick.symbol, qty=0, price=tick.price)


class WindowedMovingAverageStrategy(Strategy):
    """
    Intended per tick time (with deque): O(1) after warm-up
    Actual here (list.pop(0)): O(n) per tick because pop(0) shifts list
    Space: O(long_window) if oldest is evicted each tick
    Memory vs naive: O(L) vs O(n)
    """
    def __init__(self, short_window: int, long_window: int):
        if short_window >= long_window:
            raise ValueError("short_window must be < long_window")
        self.short_window = short_window
        self.long_window = long_window
        self.curr_fast_sum = 0.0  # O(1) state
        self.curr_slow_sum = 0.0  # O(1) state
        self.prices = []          # using list means pop(0) is O(n)

    def generate_signals(self, tick: MarketDataPoint) -> Signal:
        prices = self.prices
        price = tick.price

        prev_fast = self.curr_fast_sum  # O(1)
        prev_slow = self.curr_slow_sum  # O(1)

        prices.append(price)            # amortized O(1)
        self.curr_fast_sum += price     # O(1)
        self.curr_slow_sum += price     # O(1)

        if len(prices) < self.short_window + 1:  # O(1)
            return Signal(Action.HOLD, tick.symbol, qty=0, price=price)

        # remove the element that fell out of short window: O(1) to index and subtract
        self.curr_fast_sum -= prices[-self.short_window - 1]

        if len(prices) < self.long_window + 1:  # O(1)
            return Signal(Action.HOLD, tick.symbol, qty=0, price=price)

        # evict oldest for long window bound:
        self.curr_slow_sum -= prices[0]  # O(1) to read
        prices.pop(0)                    # O(n)  <-- bottleneck

        # current averages: O(1)
        ma_fast = self.curr_fast_sum / self.short_window
        ma_slow = self.curr_slow_sum / self.long_window

        # previous averages from saved sums: O(1)
        ma_fast_prev = prev_fast / self.short_window
        ma_slow_prev = prev_slow / self.long_window

        is_above = ma_fast > ma_slow      # O(1)
        was_above = ma_fast_prev > ma_slow_prev  # O(1)

        if is_above and not was_above:
            return Signal(Action.BUY, tick.symbol, qty=1, price=price)
        else:
            return Signal(Action.HOLD, tick.symbol, qty=0, price=price)
    
class NaiveMovingAverageStrategyOptimized(Strategy):
    """
    Refactor of naive MA:
      per tick time: O(1) after warm-up
      space: O(L) (stores at most long_window prices)
    Key ideas: deque for O(1) popleft, rolling sums for O(1) averages,
               save previous sums to detect crossovers.
    """
    def __init__(self, short_window: int, long_window: int):
        if short_window >= long_window:
            raise ValueError("short_window must be < long_window")
        self.s = int(short_window)
        self.L = int(long_window)

        self._prices = deque()   # holds up to L recent prices -> O(L) space
        self._fast_sum = 0.0     # rolling sum over last s
        self._slow_sum = 0.0     # rolling sum over last L

        self._prev_fast_sum = None  # previous-tick sums for "prev" MAs
        self._prev_slow_sum = None

    def generate_signals(self, tick: MarketDataPoint) -> Signal:
        price = float(tick.price)

        # save previous sums (O(1))
        self._prev_fast_sum = self._fast_sum
        self._prev_slow_sum = self._slow_sum

        # push new price (O(1))
        self._prices.append(price)
        self._fast_sum += price           # O(1)
        self._slow_sum += price           # O(1)

        # when size > s, the element at index -s-1 just fell out of the fast window
        if len(self._prices) > self.s:
            self._fast_sum -= self._prices[-self.s - 1]  # O(1) indexing on deque

        # when size > L, evict oldest for slow window (O(1))
        if len(self._prices) > self.L:
            self._slow_sum -= self._prices[0]
            self._prices.popleft()

        # warm-up: need at least L items for current MAs
        if len(self._prices) < self.L:
            return Signal(Action.HOLD, tick.symbol, qty=0, price=price)

        # need previous sums to form "prev" MAs (first tick after warm-up lacks these)
        if self._prev_fast_sum is None or self._prev_slow_sum is None:
            return Signal(Action.HOLD, tick.symbol, qty=0, price=price)

        # current and previous MAs are divisions on rolling sums -> O(1)
        ma_fast = self._fast_sum / self.s
        ma_slow = self._slow_sum / self.L
        ma_fast_prev = self._prev_fast_sum / self.s
        ma_slow_prev = self._prev_slow_sum / self.L

        is_above = ma_fast > ma_slow
        was_above = ma_fast_prev > ma_slow_prev

        if is_above and not was_above:
            return Signal(Action.BUY, tick.symbol, qty=1, price=price)
        return Signal(Action.HOLD, tick.symbol, qty=0, price=price)