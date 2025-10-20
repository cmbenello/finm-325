import numpy as np
import pandas as pd

class VolatilityBreakoutStrategy:
    def __init__(self, window: int = 20, k: float = 1.0, use_log_returns: bool = False):
        if window < 1:
            raise ValueError("window must be >= 1")
        if k < 0:
            raise ValueError("k must be >= 0")
        self.window = int(window)
        self.k = float(k)
        self.use_log_returns = bool(use_log_returns)

    def signals(self, prices: pd.Series) -> pd.Series:
        s = pd.Series(prices, copy=False).astype(float)
        if s.empty:
            return pd.Series(dtype=float, name="signal")

        if self.use_log_returns:
            r = np.log(s).diff()
        else:
            r = s.pct_change()

        # Rolling volatility
        vol = r.rolling(self.window, min_periods=self.window).std()

        # Breakout condition
        sig = (r > self.k * vol).astype(int)

        # Warmup -> 0, first return is NaN -> 0
        sig = sig.fillna(0).rename("signal")
        # Ensure same length as prices
        if len(sig) != len(s):
            sig = sig.reindex_like(s, fill_value=0)
        return sig