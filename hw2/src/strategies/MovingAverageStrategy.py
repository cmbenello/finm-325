from strategy import Strategy
import pandas as pd
import numpy as np


class MovingAverageStrategy(Strategy):
    def __init__(self, short_window: int, long_window: int):
        if short_window >= long_window:
            raise ValueError("short_window must be < long_window")
        self.short_window = short_window
        self.long_window = long_window


    def generate_signals(self, prices: pd.DataFrame) -> pd.DataFrame:
        ma_fast = prices.rolling(self.short_window, min_periods=self.short_window).mean()
        ma_slow = prices.rolling(self.long_window,  min_periods=self.long_window).mean()

        was_above = ma_fast.shift(1) > ma_slow.shift(1)
        is_above  = ma_fast > ma_slow
        cross_up  = (~was_above) & is_above

        signal_t1 = cross_up.shift(1).fillna(False).astype("Int8")

        return signal_t1
