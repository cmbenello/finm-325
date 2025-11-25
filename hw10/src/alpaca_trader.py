# src/alpaca_trader.py

from __future__ import annotations

import time
from datetime import datetime, timedelta

import alpaca_trade_api as tradeapi
import numpy as np
import pandas as pd

from .alpaca_settings import API_KEY_ID, API_SECRET_KEY, BASE_URL, SYMBOL, TIMEFRAME
from .strategy import MovingAverageCrossoverStrategy
from .config import SHORT_MA_WINDOW, LONG_MA_WINDOW


class AlpacaPaperTrader:
    def __init__(
        self,
        symbol: str = SYMBOL,
        timeframe: str = TIMEFRAME,
        lookback_bars: int = 500,
        target_position_size: int = 10,
        poll_interval_sec: int = 60,
    ):
        if not API_KEY_ID or not API_SECRET_KEY:
            raise RuntimeError("Set ALPACA_API_KEY_ID and ALPACA_API_SECRET_KEY.")

        self.api: tradeapi.REST = tradeapi.REST(
            API_KEY_ID,
            API_SECRET_KEY,
            BASE_URL,
            api_version="v2",
        )
        self.symbol = symbol
        self.timeframe = timeframe
        self.lookback_bars = lookback_bars
        self.target_position_size = target_position_size
        self.poll_interval_sec = poll_interval_sec

        self.strategy = MovingAverageCrossoverStrategy()
        self._bars_df: pd.DataFrame | None = None

    def _fetch_recent_bars(self) -> pd.DataFrame:
        end = datetime.utcnow()
        start = end - timedelta(minutes=self.lookback_bars + 5)

        bars = self.api.get_bars(
            self.symbol,
            self.timeframe,
            start=start.isoformat() + "Z",
            end=end.isoformat() + "Z",
            feed="iex",
        )

        # Use the index (timestamp) directly and normalize columns
        df = bars.df.copy()
        # Index is the timestamp in UTC; convert to naive datetime
        df.index = pd.to_datetime(df.index, utc=True).tz_convert(None)

        # Normalize column names to lowercase, then rename to our standard schema
        df.columns = [c.lower() for c in df.columns]
        rename_map = {
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
        }
        df = df.rename(columns=rename_map)

        # Keep only the standard OHLCV columns that are present
        keep = [col for col in ["Open", "High", "Low", "Close", "Volume"] if col in df.columns]
        df = df[keep]

        # Set index name to Datetime and ensure chronological order
        df.index.name = "Datetime"
        df = df.sort_index()

        return df

    def _update_bars(self) -> None:
        # First call: load a recent history window
        if self._bars_df is None:
            df = self._fetch_recent_bars()
            if df is None or df.empty:
                # Nothing to do yet – probably no bars in the window
                return
            self._bars_df = df
            return

        # If we somehow have an empty frame or NaT index, just refetch
        if self._bars_df.empty:
            df = self._fetch_recent_bars()
            if df is None or df.empty:
                return
            self._bars_df = df
            return

        last_ts = self._bars_df.index.max()
        if pd.isna(last_ts):
            # Invalid last timestamp – refetch instead of sending NaTZ
            df = self._fetch_recent_bars()
            if df is None or df.empty:
                return
            self._bars_df = df
            return

        end = datetime.utcnow()
        start = last_ts + timedelta(seconds=1)

        bars = self.api.get_bars(
            self.symbol,
            self.timeframe,
            start=start.isoformat() + "Z",
            end=end.isoformat() + "Z",
            feed="iex",
        )

        if bars.df.empty:
            return

        # Use the index (timestamp) directly and normalize columns
        df_new = bars.df.copy()
        df_new.index = pd.to_datetime(df_new.index, utc=True).tz_convert(None)

        df_new.columns = [c.lower() for c in df_new.columns]
        rename_map = {
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
        }
        df_new = df_new.rename(columns=rename_map)

        keep = [col for col in ["Open", "High", "Low", "Close", "Volume"] if col in df_new.columns]
        df_new = df_new[keep]

        df_new.index.name = "Datetime"
        df_new = df_new.sort_index()

        self._bars_df = pd.concat([self._bars_df, df_new], axis=0)
        self._bars_df = self._bars_df.iloc[-self.lookback_bars :]
        
    def _get_current_position(self) -> int:
        positions = self.api.list_positions()
        for p in positions:
            if p.symbol == self.symbol:
                return int(float(p.qty))
        return 0

    def _compute_desired_position(self) -> int:
        assert self._bars_df is not None

        df = self._bars_df.copy()

        df["ma_short"] = df["Close"].rolling(SHORT_MA_WINDOW, min_periods=1).mean()
        df["ma_long"] = df["Close"].rolling(LONG_MA_WINDOW, min_periods=1).mean()

        signals = self.strategy.generate_signals(
            df.rename(columns={"ma_short": self.strategy.short_ma_col,
                               "ma_long": self.strategy.long_ma_col})
        )

        last_pos = signals[self.strategy.position_col].iloc[-1]

        desired_shares = int(np.sign(last_pos) * self.target_position_size)
        return desired_shares

    def _submit_order(self, delta_shares: int) -> None:
        if delta_shares == 0:
            return

        side = "buy" if delta_shares > 0 else "sell"
        qty = abs(delta_shares)

        print(f"Submitting {side} {qty} {self.symbol}")
        self.api.submit_order(
            symbol=self.symbol,
            qty=qty,
            side=side,
            type="market",
            time_in_force="day",
        )

    def run(self) -> None:
        print("Initializing bars...")
        self._update_bars()
        print("Starting paper trading loop.")

        while True:
            try:
                self._update_bars()
                if self._bars_df is None or len(self._bars_df) < max(
                    SHORT_MA_WINDOW, LONG_MA_WINDOW
                ):
                    print("Not enough data yet, waiting...")
                    time.sleep(self.poll_interval_sec)
                    continue

                current_pos = self._get_current_position()
                desired_pos = self._compute_desired_position()
                delta = desired_pos - current_pos

                print(
                    f"{datetime.utcnow().isoformat()} "
                    f"current={current_pos}, desired={desired_pos}, delta={delta}"
                )

                if delta != 0:
                    self._submit_order(delta)

            except Exception as e:
                print(f"Error in trading loop: {e}")

            time.sleep(self.poll_interval_sec)