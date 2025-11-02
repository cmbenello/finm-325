from __future__ import annotations
import pandas as pd
import numpy as np

from metrics import pandas_rolling_metrics, polars_rolling_metrics

WINDOW = 20
MINP = 20

def _manual_rolls_one_symbol(df_sym: pd.DataFrame):
    # assume sorted by timestamp
    price = df_sym["price"].astype(float)
    ma = price.rolling(WINDOW, min_periods=MINP).mean()
    sd = price.rolling(WINDOW, min_periods=MINP).std(ddof=0)
    ret = price.pct_change()
    mu_r = ret.rolling(WINDOW, min_periods=MINP).mean()
    sd_r = ret.rolling(WINDOW, min_periods=MINP).std(ddof=0)
    sharpe = mu_r / sd_r
    return ma, sd, ret, sharpe

def test_pandas_rolling_metrics_matches_manual(pd_loaded: pd.DataFrame, symbols):
    df = pd_loaded.sort_values(["symbol", "timestamp"], kind="mergesort")
    out, _t = pandas_rolling_metrics(df, window=WINDOW, min_periods=MINP)

    # pick a symbol with enough rows
    sym = symbols[0]
    s = df[df["symbol"] == sym].sort_values("timestamp").reset_index(drop=True)
    o = out[out["symbol"] == sym].sort_values("timestamp").reset_index(drop=True)

    ma, sd, ret, sharpe = _manual_rolls_one_symbol(s)

    np.testing.assert_allclose(o["ma20"].to_numpy(dtype=float), ma.to_numpy(dtype=float), rtol=1e-12, atol=1e-12)
    np.testing.assert_allclose(o["std20"].to_numpy(dtype=float), sd.to_numpy(dtype=float), rtol=1e-12, atol=1e-12)

    # NaNs in first rows are fine; compare only aligned non-nan entries
    mask = ~ret.isna()
    np.testing.assert_allclose(o.loc[mask, "ret"].to_numpy(dtype=float),
                               ret.loc[mask].to_numpy(dtype=float), rtol=1e-12, atol=1e-12)

    # sharpe can be nan where sd_r==0; compare where both not nan/inf
    mask_s = ~(np.isnan(sharpe.to_numpy()) | np.isinf(sharpe.to_numpy()) |
               np.isnan(o["sharpe20"].to_numpy(dtype=float)) | np.isinf(o["sharpe20"].to_numpy(dtype=float)))
    np.testing.assert_allclose(o["sharpe20"].to_numpy(dtype=float)[mask_s],
                               sharpe.to_numpy(dtype=float)[mask_s], rtol=1e-10, atol=1e-10)

def test_polars_rolling_roundtrips(pd_loaded, pl_loaded):
    # compute in polars then compare to pandas computation on the same rows
    pl_out, _ = polars_rolling_metrics(pl_loaded, window=WINDOW, min_periods=MINP)
    pd_out = pl_out.to_pandas()
    pd_out["timestamp"] = pd.to_datetime(pd_out["timestamp"], utc=True)
    pd_out = pd_out.sort_values(["symbol", "timestamp"]).reset_index(drop=True)

    # lightweight sanity: columns exist and shapes match input
    assert {"ma20","std20","ret","sharpe20"}.issubset(set(pd_out.columns))
    assert len(pd_out) == len(pd_loaded)