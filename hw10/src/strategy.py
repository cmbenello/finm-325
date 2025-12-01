from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import SHORT_MA_COL, LONG_MA_COL


@dataclass
class MovingAverageCrossoverStrategy:
    """
    Simple moving average crossover strategy.

    Rules:
      - If short MA crosses above long MA: go long (+1).
      - If short MA crosses below long MA: go short (-1).
      - Otherwise, hold previous position.
    """
    name: str = "ma_crossover"
    short_ma_col: str = SHORT_MA_COL
    long_ma_col: str = LONG_MA_COL
    position_col: str = "position"
    signal_col: str = "signal"

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Given a DataFrame with short/long MA columns, return a copy with:
          - 'signal' column: +1 (buy), -1 (sell), 0 (hold)
          - 'position' column: actual held position after applying signals
        """
        required_cols = {self.short_ma_col, self.long_ma_col}
        missing_cols = required_cols - set(df.columns)
        if missing_cols:
            raise ValueError(f"DataFrame is missing required columns: {missing_cols}")

        signals = df.copy()

        # Initialize signal column
        signals[self.signal_col] = 0

        short_ma = signals[self.short_ma_col]
        long_ma = signals[self.long_ma_col]

        # Generate raw crossover signals
        #  +1 when short MA above long MA
        #  -1 when short MA below long MA
        signals.loc[short_ma > long_ma, self.signal_col] = 1
        signals.loc[short_ma < long_ma, self.signal_col] = -1

        # Turn signals into positions with "previous bar" logic
        # position_t = signal_{t-1}
        signals[self.position_col] = signals[self.signal_col].shift(1).fillna(0)

        return signals


@dataclass
class MomentumStrategy(MovingAverageCrossoverStrategy):
    """
    Alias for the moving-average crossover, exposed as a momentum strategy.
    """
    name: str = "momentum"


@dataclass
class MeanReversionStrategy:
    """
    Simple mean reversion strategy using a z-score of price relative to a
    rolling mean and standard deviation.
    """

    lookback: int = 20
    z_entry: float = 1.0
    price_col: str = "Close"
    position_col: str = "position"
    signal_col: str = "signal"
    name: str = "mean_reversion"

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Go long when price is sufficiently below its rolling mean
        (z < -z_entry), go short when sufficiently above (z > +z_entry).
        Hold the previous position otherwise.
        """
        if self.price_col not in df.columns:
            raise ValueError(f"DataFrame is missing required column: {self.price_col}")

        signals = df.copy()
        rolling_mean = signals[self.price_col].rolling(window=self.lookback, min_periods=1).mean()
        rolling_std = signals[self.price_col].rolling(window=self.lookback, min_periods=1).std()
        rolling_std = rolling_std.replace(0, np.nan)

        zscore = (signals[self.price_col] - rolling_mean) / rolling_std
        signals["zscore"] = zscore

        signals[self.signal_col] = 0
        signals.loc[zscore < -self.z_entry, self.signal_col] = 1
        signals.loc[zscore > self.z_entry, self.signal_col] = -1
        signals[self.signal_col] = signals[self.signal_col].fillna(0)

        signals[self.position_col] = signals[self.signal_col].shift(1).fillna(0)
        return signals



@dataclass
class AggressiveMomentumStrategy:
    """
    High-turnover intraday momentum strategy based on short/long moving
    averages of the price itself. This is meant to be an aggressive,
    always-in-the-market trend follower.

    Rules:
      - Compute short and long rolling means of `price_col`.
      - Go long (+1) when short MA > long MA.
      - Go short (-1) when short MA < long MA.
      - Hold previous position otherwise.
    """

    price_col: str = "Close"
    short_window: int = 5
    long_window: int = 20
    position_col: str = "position"
    signal_col: str = "signal"
    name: str = "aggressive_momentum"

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        if self.price_col not in df.columns:
            raise ValueError(f"DataFrame is missing required column: {self.price_col}")

        signals = df.copy()

        price = signals[self.price_col]
        short_ma = price.rolling(window=self.short_window, min_periods=1).mean()
        long_ma = price.rolling(window=self.long_window, min_periods=1).mean()

        signals["short_ma_price"] = short_ma
        signals["long_ma_price"] = long_ma

        # Initialize signal column
        signals[self.signal_col] = 0

        # +1 when short MA above long MA, -1 when below
        signals.loc[short_ma > long_ma, self.signal_col] = 1
        signals.loc[short_ma < long_ma, self.signal_col] = -1

        # Turn signals into positions with previous-bar logic
        signals[self.position_col] = signals[self.signal_col].shift(1).fillna(0)

        return signals


@dataclass
class VWAPReversionStrategy:
    """
    Intraday VWAP-based mean reversion strategy.

    For each trading day:
      - Compute intraday VWAP using price * volume / cumulative volume.
      - Measure deviation of price from VWAP.
      - Go long when price is sufficiently below VWAP (contrarian).
      - Go short when price is sufficiently above VWAP.

    This is designed as an aggressive, high-EV intraday reversion strategy.
    """

    price_col: str = "Close"
    volume_col: str = "Volume"
    position_col: str = "position"
    signal_col: str = "signal"
    lookback: int = 30        # bars for rolling std of deviation
    z_entry: float = 1.0      # entry threshold in z-score units
    name: str = "vwap_reversion"

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        if self.price_col not in df.columns:
            raise ValueError(f"DataFrame is missing required column: {self.price_col}")
        if self.volume_col not in df.columns:
            raise ValueError(f"DataFrame is missing required column: {self.volume_col}")
        if not isinstance(df.index, pd.DatetimeIndex):
            raise ValueError("VWAPReversionStrategy requires a DatetimeIndex.")

        signals = df.copy()

        price = signals[self.price_col]
        volume = signals[self.volume_col]

        # Group by trading day based on the index's date
        dates = signals.index.normalize()

        # Intraday cumulative PV and volume per day
        pv = (price * volume).groupby(dates).cumsum()
        cum_vol = volume.groupby(dates).cumsum().replace(0, np.nan)

        vwap = pv / cum_vol
        signals["vwap"] = vwap

        # Deviation from VWAP and rolling std of that deviation
        deviation = price - vwap
        rolling_std = deviation.rolling(window=self.lookback, min_periods=1).std()
        rolling_std = rolling_std.replace(0, np.nan)

        zscore = deviation / rolling_std
        signals["vwap_zscore"] = zscore

        # Initialize signal column
        signals[self.signal_col] = 0

        # Contrarian: long when price is far below VWAP, short when far above
        signals.loc[zscore < -self.z_entry, self.signal_col] = 1
        signals.loc[zscore > self.z_entry, self.signal_col] = -1
        signals[self.signal_col] = signals[self.signal_col].fillna(0)

        # Previous-bar position logic
        signals[self.position_col] = signals[self.signal_col].shift(1).fillna(0)

        return signals

@dataclass
class TurboReversionMomentumSwitch:
    """
    Ultra-aggressive intraday strategy combining:
    - VWAP deviation (reversion)
    - Short-term momentum (trend filter)
    - Bias override for specific tickers (e.g., NVDA long-only)

    Always produces frequent trades.
    """

    price_col: str = "Close"
    volume_col: str = "Volume"
    lookback: int = 20
    z_entry: float = 0.7          # tighter than VWAPReversion
    mom_window: int = 5           # fast momentum filter
    nvda_bias_long_only: bool = True

    signal_col: str = "signal"
    position_col: str = "position"
    name: str = "turbo_reversion"

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        if not isinstance(df.index, pd.DatetimeIndex):
            raise ValueError("Index must be DatetimeIndex")

        signals = df.copy()

        price = signals[self.price_col]
        volume = signals[self.volume_col]
        dates = signals.index.normalize()

        pv = (price * volume).groupby(dates).cumsum()
        cum_vol = volume.groupby(dates).cumsum().replace(0, np.nan)
        vwap = pv / cum_vol
        signals["vwap"] = vwap

        deviation = price - vwap
        rolling_std = deviation.rolling(self.lookback, min_periods=1).std().replace(0, np.nan)
        zscore = deviation / rolling_std
        signals["zscore"] = zscore

        # short-term momentum
        momentum = price.diff(self.mom_window)
        signals["momentum"] = momentum

        signals[self.signal_col] = 0

        # Core VWAP reversion
        long_cond = (zscore < -self.z_entry) & (momentum <= 0)
        short_cond = (zscore > self.z_entry) & (momentum >= 0)

        signals.loc[long_cond, self.signal_col] = 1
        signals.loc[short_cond, self.signal_col] = -1

        # Bias override for NVDA
        if self.nvda_bias_long_only and "NVDA" in signals.get("ticker", ""):
            signals.loc[signals[self.signal_col] == -1, self.signal_col] = 0

        signals[self.position_col] = signals[self.signal_col].shift(1).fillna(0)

        return signals