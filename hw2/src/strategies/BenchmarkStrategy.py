import pandas as pd
import numpy as np

class Benchmark_Strategy:
    def __init__(self, initial_cash: float, participation_rate: float = 0.10,
                 adv_window: int = 20, dollar_cap_usd: float | None = None):
        assert 0 < participation_rate <= 0.20, "keep PR in [0, 0.20]"
        self.initial_cash = float(initial_cash)
        self.pr = float(participation_rate)
        self.adv_win = int(adv_window)
        self.dollar_cap = dollar_cap_usd

    def generate_signals(self, close_df: pd.DataFrame, vol_df: pd.DataFrame) -> pd.DataFrame:
        close = close_df.sort_index().astype("float64")
        vol   = vol_df.reindex_like(close).astype("float64")

        # --- choose t0 so ADV exists: first index where we have adv_window rows
        if len(close.index) < self.adv_win:
            t0 = close.index[-1]
        else:
            t0 = close.index[self.adv_win - 1]

        # eligible tickers: finite positive price at t0
        price0 = close.loc[t0].where(np.isfinite(close.loc[t0]) & (close.loc[t0] > 0)).dropna()
        if price0.empty:
            return pd.DataFrame(0, index=close.index, columns=close.columns, dtype="int64")

        # ADV at t0 = mean of last adv_window valid days up to t0 (ffill/bfill to avoid NaNs)
        vol_filled = vol.ffill().bfill()
        adv0 = vol_filled.loc[:t0].tail(self.adv_win).mean().reindex(price0.index).fillna(0.0).clip(lower=0.0)

        # raw cap: 10% ADV shares per name
        cap = np.floor(self.pr * adv0).astype("int64")
        cap[cap < 0] = 0

        # if ADV is still 0 for a name, skip it (cannot enforce 10% PR there)
        cap = cap[cap > 0]
        price0 = price0.reindex(cap.index)

        if cap.empty:
            return pd.DataFrame(0, index=close.index, columns=close.columns, dtype="int64")

        # start at full caps, then scale to fit cash
        qty = cap.copy()
        notional_full = float((qty * price0).sum())
        cash = float(self.initial_cash)

        if notional_full > cash and notional_full > 0:
            scale = cash / notional_full
            qty = np.floor(qty * scale).astype("int64")

        # greedy top-up with any leftover cash, still ≤ cap (cheapest first)
        remaining_cash = cash - float((qty * price0).sum())
        if remaining_cash > 0:
            need = (cap - qty).clip(lower=0)
            if need.sum() > 0:
                order = np.argsort(price0.values)  # cheapest first
                for k in order:
                    name = price0.index[k]
                    p = float(price0.iloc[k])
                    if p <= 0 or not np.isfinite(p):
                        continue
                    room = int(need.iloc[k])
                    if room <= 0:
                        continue
                    add = min(room, int(remaining_cash // p))
                    if add > 0:
                        qty.iloc[k] += add
                        remaining_cash -= add * p
                    if remaining_cash < price0.iloc[order].min():
                        break

        print(remaining_cash)
        sig = pd.DataFrame(0, index=close.index, columns=close.columns, dtype="int64")
        if qty.sum() > 0:
            sig.loc[t0, qty.index] = qty.values
        return sig