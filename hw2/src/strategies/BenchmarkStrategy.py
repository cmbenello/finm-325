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

        # choose first day with adv_window history so ADV is defined
        t0 = close.index[self.adv_win - 1] if len(close.index) >= self.adv_win else close.index[-1]

        # eligible tickers at t0
        price0 = close.loc[t0].where(np.isfinite(close.loc[t0]) & (close.loc[t0] > 0)).dropna()
        if price0.empty:
            return pd.DataFrame(0, index=close.index, columns=close.columns, dtype="int64")

        # 20-day ADV up to t0
        adv0 = (
            vol.ffill().bfill()
            .loc[:t0].tail(self.adv_win).mean()
            .reindex(price0.index).fillna(0.0).clip(lower=0.0)
        )

        # target = 10% ADV shares (integer cap)
        cap = np.floor(self.pr * adv0).astype("int64")
        cap = cap[cap > 0]                       # skip names with no ADV
        price0 = price0.reindex(cap.index)

        if cap.empty:
            return pd.DataFrame(0, index=close.index, columns=close.columns, dtype="int64")

        # spend at full 10% caps
        notional_full = float((cap * price0).sum())
        cash = float(self.initial_cash)

        # proportional scale to fit cash (no greedy top-up)
        if notional_full > 0 and notional_full > cash:
            s = cash / notional_full
            qty = np.floor(cap * s).astype("int64")
        else:
            qty = cap.copy()

        # build signals: integer qty on day-0, zeros elsewhere
        sig = pd.DataFrame(0, index=close.index, columns=close.columns, dtype="int64")
        if qty.sum() > 0:
            sig.loc[t0, qty.index] = qty.values
        return sig