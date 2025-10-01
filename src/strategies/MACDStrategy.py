from src.strategy import Strategy
import pandas as pd
import numpy as np


class MovingAverageStrategy(Strategy):
    def __init__(self, fast: int, slow: int, sig: int):
        if slow >= fast:
            raise ValueError("fast must be < slow")
        self.fast = fast
        self.slow = slow
        self.sig = sig


    def generate_signals(self, prices: pd.DataFrame) -> pd.DataFrame:
        ema_fast = prices.ewm(span=self.fast, adjust=False).mean()
        ema_slow = prices.ewm(span=self.slow, adjust=False).mean()

        macd = ema_fast - ema_slow
        signal = macd.ewm(span=self.sig, adjust=False).mean()

        was_above = macd.shift(1) > signal.shift(1)
        is_above  = macd > signal
        cross_up  = (~was_above) & is_above

        signal_t1 = cross_up.shift(1).fillna(False).astype("Int8")

        return signal_t1
