from src.strategy import Strategy
import pandas as pd
import numpy as np


class RSIStrategy(Strategy):
    def __init__(self, window: int, buy_threshold: int):
        self.window = window
        self.buy_threshold = buy_threshold


    def generate_signals(self, prices: pd.DataFrame) -> pd.DataFrame:

        diff = prices.diff()
        gains = diff.clip(lower = 0)
        losses = (- diff).clip(lower = 0)

        gain_window = gains.rolling(self.window, min_periods=self.window).mean()
        loss_window = losses.rolling(self.window, min_periods=self.window).mean()

        eps = 1e-12
        rs = gain_window / (loss_window + eps)

        rsi = 100 - 100 / (1 + rs)

        signal_t1 = (rsi < self.buy_threshold).shift(1).fillna(False).astype("Int8")

        return signal_t1
