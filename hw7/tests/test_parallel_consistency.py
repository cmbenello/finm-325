from __future__ import annotations
import pandas as pd
import numpy as np

from parallel import (
    pandas_threaded, pandas_multiproc,
    polars_threaded, polars_multiproc
)

def _sort_cols_pd(df: pd.DataFrame) -> pd.DataFrame:
    cols = ["symbol", "timestamp", "price", "ma20", "std20", "ret", "sharpe20"]
    keep = [c for c in cols if c in df.columns] + [c for c in df.columns if c not in cols]
    out = df[keep].sort_values(["symbol", "timestamp"]).reset_index(drop=True)
    return out

def test_pandas_thread_vs_multiproc_same(pd_loaded: pd.DataFrame):
    thr_df, t_thr, r_thr = pandas_threaded(pd_loaded)
    mp_df,  t_mp,  r_mp  = pandas_multiproc(pd_loaded)

    thr_df = _sort_cols_pd(thr_df)
    mp_df  = _sort_cols_pd(mp_df)

    # exact equal for symbol/timestamp; floats close
    assert thr_df[["symbol","timestamp"]].equals(mp_df[["symbol","timestamp"]])

    for col in ["price","ma20","std20","ret","sharpe20"]:
        if col in thr_df.columns and col in mp_df.columns:
            a = thr_df[col].to_numpy(dtype=float)
            b = mp_df[col].to_numpy(dtype=float)
            mask = ~(np.isnan(a) | np.isnan(b) | np.isinf(a) | np.isinf(b))
            np.testing.assert_allclose(a[mask], b[mask], rtol=1e-10, atol=1e-10)

def test_polars_thread_vs_multiproc_same(pl_loaded):
    thr_df, *_ = polars_threaded(pl_loaded)
    mp_df,  *_ = polars_multiproc(pl_loaded)

    thr_pd = thr_df.to_pandas().sort_values(["symbol","timestamp"]).reset_index(drop=True)
    mp_pd  = mp_df.to_pandas().sort_values(["symbol","timestamp"]).reset_index(drop=True)

    assert thr_pd[["symbol","timestamp"]].equals(mp_pd[["symbol","timestamp"]])
    for col in ["price","ma20","std20","ret","sharpe20"]:
        if col in thr_pd.columns and col in mp_pd.columns:
            a = thr_pd[col].to_numpy(dtype=float)
            b = mp_pd[col].to_numpy(dtype=float)
            mask = ~(np.isnan(a) | np.isnan(b) | np.isinf(a) | np.isinf(b))
            np.testing.assert_allclose(a[mask], b[mask], rtol=1e-10, atol=1e-10)