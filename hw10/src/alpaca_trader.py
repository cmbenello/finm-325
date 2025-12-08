# src/alpaca_trader.py

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Sequence

import alpaca_trade_api as tradeapi
import numpy as np
import pandas as pd

from .alpaca_settings import API_KEY_ID, API_SECRET_KEY, BASE_URL, SYMBOL, TIMEFRAME
from .config import LONG_MA_COL, LONG_MA_WINDOW, SHORT_MA_COL, SHORT_MA_WINDOW
from .strategy import (
    AggressiveMomentumStrategy,
    MeanReversionStrategy,
    MomentumStrategy,
    MovingAverageCrossoverStrategy,
    VWAPReversionStrategy,
)


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
                qty = float(p.qty)
                if getattr(p, "side", "").lower() == "short":
                    qty = -qty
                return int(qty)
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


@dataclass
class PortfolioLegConfig:
    """
    Configuration for a single ticker inside a multi-asset Alpaca paper
    trading loop.
    """

    symbol: str
    allocation: float
    strategies: Sequence[object]
    lookback_bars: int = 500
    long_only: bool = False
    short_only: bool = False
    asset_type: str = "equity"  # "equity" or "crypto"
    feed: str | None = None     # e.g., "iex" for equities, "us" for crypto

    def __post_init__(self) -> None:
        self.symbol = self.symbol.upper()


class AlpacaPortfolioTrader:
    """
    Trade a portfolio of symbols on Alpaca paper accounts with per-ticker
    strategy assignments and target allocations sized off account equity.
    """

    def __init__(
        self,
        legs: Sequence[PortfolioLegConfig],
        timeframe: str = TIMEFRAME,
        poll_interval_sec: int = 60,
        min_trade_notional: float = 10.0,
        rebalance_on_start: bool = True,
    ) -> None:
        if not API_KEY_ID or not API_SECRET_KEY:
            raise RuntimeError("Set ALPACA_API_KEY_ID and ALPACA_API_SECRET_KEY.")
        if not legs:
            raise ValueError("Provide at least one portfolio leg.")

        self.api: tradeapi.REST = tradeapi.REST(
            API_KEY_ID,
            API_SECRET_KEY,
            BASE_URL,
            api_version="v2",
        )

        self.legs = list(legs)
        self.timeframe = timeframe
        self.poll_interval_sec = poll_interval_sec
        self.min_trade_notional = float(min_trade_notional)
        self.rebalance_on_start = rebalance_on_start

        self._bars: Dict[str, pd.DataFrame] = {}
        self._position_cache: Dict[str, float] = {}
        self._did_initial_rebalance = False

    @staticmethod
    def _symbol_aliases(symbol: str) -> List[str]:
        """
        Return normalized symbol aliases so that BTC/USD and BTCUSD resolve
        to the same position entry.
        """
        sym = symbol.upper()
        aliases = {sym, sym.replace("/", "")}
        return list(aliases)

    @staticmethod
    def _normalize_bars_df(raw_df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize the Alpaca bars DataFrame to a single-index datetime frame
        with standardized OHLCV column names.
        """
        if raw_df is None or raw_df.empty:
            return pd.DataFrame()

        df = raw_df.copy()

        # Handle possible MultiIndex (symbol, timestamp)
        if isinstance(df.index, pd.MultiIndex):
            ts_index = df.index.get_level_values(-1)
        else:
            ts_index = df.index

        if "timestamp" in df.columns:
            ts_index = df["timestamp"]
            df = df.drop(columns=["timestamp"], errors="ignore")

        df.index = pd.to_datetime(ts_index, utc=True).tz_convert(None)

        df.columns = [c.lower() for c in df.columns]
        rename_map = {
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
        }
        df = df.rename(columns=rename_map)

        keep = [col for col in ["Open", "High", "Low", "Close", "Volume"] if col in df.columns]
        df = df[keep]

        df.index.name = "Datetime"
        return df.sort_index()

    def _fetch_bars(
        self,
        leg: PortfolioLegConfig,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> pd.DataFrame:
        end = end or datetime.utcnow()
        start = start or (end - timedelta(minutes=leg.lookback_bars + 5))

        start_iso = start.isoformat() + "Z"
        end_iso = end.isoformat() + "Z"

        try:
            if leg.asset_type.lower() == "crypto":
                bars = self.api.get_crypto_bars(
                    leg.symbol,
                    self.timeframe,
                    start=start_iso,
                    end=end_iso,
                )
            else:
                feed = leg.feed or "iex"
                bars = self.api.get_bars(
                    leg.symbol,
                    self.timeframe,
                    start=start_iso,
                    end=end_iso,
                    feed=feed,
                )
        except Exception as exc:
            print(f"[{leg.symbol}] Error fetching bars: {exc}")
            return pd.DataFrame()

        df = getattr(bars, "df", None)
        return self._normalize_bars_df(df)

    def _update_bars_for_leg(self, leg: PortfolioLegConfig) -> None:
        """
        Maintain a rolling window of bars for a single leg.
        """
        current = self._bars.get(leg.symbol)
        if current is None or current.empty:
            df = self._fetch_bars(leg)
            if df is None or df.empty:
                return
            self._bars[leg.symbol] = df.tail(leg.lookback_bars)
            return

        last_ts = current.index.max()
        if pd.isna(last_ts):
            df_new = self._fetch_bars(leg)
        else:
            df_new = self._fetch_bars(leg, start=last_ts + timedelta(seconds=1))

        if df_new is None or df_new.empty:
            return

        combined = pd.concat([current, df_new], axis=0)
        combined = combined[~combined.index.duplicated(keep="last")]
        self._bars[leg.symbol] = combined.tail(leg.lookback_bars)

    def _refresh_positions_cache(self) -> None:
        positions: Dict[str, float] = {}
        try:
            for p in self.api.list_positions():
                raw_qty = float(p.qty)
                side = getattr(p, "side", "").lower()
                mkt_val = float(getattr(p, "market_value", 0) or 0)

                qty = abs(raw_qty)
                if side == "short":
                    qty = -qty
                elif side == "long":
                    qty = qty
                elif mkt_val < 0:
                    # Fallback for cases where side is missing but market value is negative
                    qty = -qty

                for alias in self._symbol_aliases(p.symbol):
                    positions[alias] = qty
        except Exception as exc:
            print(f"Error fetching positions: {exc}")
        self._position_cache = positions

    def _get_cached_position(self, leg: PortfolioLegConfig) -> float:
        """
        Return cached position size for a leg, honoring symbol aliases.
        """
        return (
            self._position_cache.get(leg.symbol)
            or self._position_cache.get(leg.symbol.replace("/", ""))
            or 0.0
        )

    def _get_account_snapshot(self) -> Dict[str, float]:
        account = self.api.get_account()
        return {
            "equity": float(account.equity),
            "cash": float(account.cash),
            "buying_power": float(getattr(account, "buying_power", account.cash)),
        }

    @staticmethod
    def _ensure_features(df: pd.DataFrame, strategies: Sequence[object]) -> pd.DataFrame:
        """
        Add any columns required by the configured strategies (e.g., MA columns).
        """
        out = df.copy()

        needs_ma = any(
            isinstance(s, (MovingAverageCrossoverStrategy, MomentumStrategy))
            for s in strategies
        )
        if needs_ma:
            out[SHORT_MA_COL] = out["Close"].rolling(SHORT_MA_WINDOW, min_periods=1).mean()
            out[LONG_MA_COL] = out["Close"].rolling(LONG_MA_WINDOW, min_periods=1).mean()

        return out

    @staticmethod
    def _min_history_needed(leg: PortfolioLegConfig) -> int:
        windows: List[int] = [SHORT_MA_WINDOW, LONG_MA_WINDOW, 10]
        for strat in leg.strategies:
            if hasattr(strat, "long_window"):
                windows.append(int(getattr(strat, "long_window")))
            if hasattr(strat, "lookback"):
                windows.append(int(getattr(strat, "lookback")))
        return max(windows)

    def _combine_strategy_signals(self, leg: PortfolioLegConfig, df: pd.DataFrame) -> float:
        prepared = self._ensure_features(df, leg.strategies)
        positions: List[float] = []

        for strat in leg.strategies:
            try:
                signals = strat.generate_signals(prepared)
                positions.append(float(signals[strat.position_col].iloc[-1]))
            except Exception as exc:
                name = getattr(strat, "name", strat.__class__.__name__)
                print(f"[{leg.symbol}] {name} signal error: {exc}")

        if not positions:
            return 0.0

        avg_pos = float(np.mean(positions))
        combined = float(np.sign(avg_pos))

        if leg.long_only:
            combined = max(0.0, combined)
        if leg.short_only:
            combined = min(0.0, combined)

        return combined

    def _desired_shares(
        self,
        leg: PortfolioLegConfig,
        account: Dict[str, float],
    ) -> float | None:
        bars = self._bars.get(leg.symbol)
        if bars is None or bars.empty:
            return None

        if len(bars) < self._min_history_needed(leg):
            return None

        direction = self._combine_strategy_signals(leg, bars)
        if direction == 0:
            return 0.0

        last_price = float(bars["Close"].iloc[-1])
        if last_price <= 0:
            return 0.0

        equity_target = account["equity"] * abs(leg.allocation)
        cash_available = account["cash"]
        bp_available = account["buying_power"]

        buffer = 0.98  # avoid edge rejections due to rounding

        if direction > 0:
            # Longs: crypto is cash-only; equities can tap buying power
            notional_cap = cash_available if leg.asset_type.lower() == "crypto" else bp_available
        else:
            # Shorts rely on buying power
            notional_cap = bp_available

        target_notional = min(equity_target, notional_cap * buffer) * direction
        desired_shares = target_notional / last_price
        return desired_shares

    def _rebalance_once(self, account: Dict[str, float]) -> None:
        """
        One-off rebalance to target allocations using current positions.
        """
        self._refresh_positions_cache()
        for leg in self.legs:
            self._update_bars_for_leg(leg)
            desired = self._desired_shares(leg, account)
            if desired is None:
                continue
            current = self._get_cached_position(leg)
            delta = desired - current
            if abs(delta) < 1e-6:
                continue
            self._submit_order(leg, delta)

    def _submit_order(self, leg: PortfolioLegConfig, delta_shares: float) -> None:
        if abs(delta_shares) < 1e-6:
            return

        side = "buy" if delta_shares > 0 else "sell"
        qty = abs(delta_shares)
        time_in_force = "gtc"
        current = self._position_cache.get(leg.symbol) or self._position_cache.get(
            leg.symbol.replace("/", "")
        ) or 0.0

        if leg.asset_type.lower() == "crypto":
            # Floor to 6 decimals and avoid overselling tiny dust amounts
            precision = 1e-6
            if side == "sell":
                qty = min(qty, max(0.0, abs(current)))
            qty = max(0.0, np.floor((qty - 1e-7) / precision) * precision)
        else:
            # Enforce one-sided constraints but still allow opening shorts when permitted.
            if leg.short_only and side == "buy":
                qty = min(qty, int(np.floor(max(0.0, -current))))
            elif leg.long_only and side == "sell":
                qty = min(qty, int(np.floor(max(0.0, current))))

            # Alpaca only accepts fractional equity orders with DAY TIF.
            fractional = abs(qty - round(qty)) > 1e-6
            if fractional:
                time_in_force = "day"
                qty = float(np.round(qty, 3))
            else:
                qty = int(np.floor(qty))

        if qty <= 0:
            return

        bars = self._bars.get(leg.symbol)
        notional = None
        if bars is not None and not bars.empty:
            last_price = float(bars["Close"].iloc[-1])
            notional = last_price * qty

        if notional is not None and notional < self.min_trade_notional:
            return

        print(f"Submitting {side} {qty} {leg.symbol}")
        self.api.submit_order(
            symbol=leg.symbol,
            qty=qty,
            side=side,
            type="market",
            time_in_force=time_in_force,
        )

    def run(self) -> None:
        print("Bootstrapping historical bars for portfolio...")
        for leg in self.legs:
            self._update_bars_for_leg(leg)

        if self.rebalance_on_start:
            account = self._get_account_snapshot()
            self._rebalance_once(account)
            self._did_initial_rebalance = True

        while True:
            try:
                account = self._get_account_snapshot()
                self._refresh_positions_cache()

                for leg in self.legs:
                    self._update_bars_for_leg(leg)

                    desired = self._desired_shares(leg, account)
                    if desired is None:
                        need = self._min_history_needed(leg)
                        have = len(self._bars.get(leg.symbol, []))
                        print(f"[{leg.symbol}] Waiting for data ({have}/{need} bars)...")
                        continue

                    current = self._get_cached_position(leg)
                    delta = desired - current

                    print(
                        f"{datetime.utcnow().isoformat()} "
                        f"[{leg.symbol}] current={current:.4f} desired={desired:.4f} delta={delta:.4f}"
                    )

                    self._submit_order(leg, delta)

            except Exception as exc:
                print(f"Error in portfolio loop: {exc}")

            time.sleep(self.poll_interval_sec)
