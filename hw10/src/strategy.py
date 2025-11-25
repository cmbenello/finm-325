from dataclasses import dataclass

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