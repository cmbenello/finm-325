from strategy import Strategy
import pandas as pd
import numpy as np


class VolatilityBreakoutStrategy(Strategy):
    def __init__(self, window):
        self.window = window


    def generate_signals(self, prices: pd.DataFrame) -> pd.DataFrame:
        daily_returns = prices.pct_change()
        vol_window = daily_returns.rolling(self.window, min_periods=self.window).std()


        signal = (daily_returns > vol_window).shift(1).fillna(False).astype("Int8")

        return signal