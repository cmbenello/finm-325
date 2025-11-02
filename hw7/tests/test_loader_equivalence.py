from __future__ import annotations
import pandas as pd
import numpy as np

def test_pandas_vs_polars_equivalence(pd_loaded: pd.DataFrame, pl_loaded):
    # compare columns & values after converting Polars -> Pandas
    pl_pd = pl_loaded.to_pandas()
    pl_pd["timestamp"] = pd.to_datetime(pl_pd["timestamp"], utc=True)
    pl_pd = pl_pd.sort_values(["symbol", "timestamp"]).reset_index(drop=True)

    pd_df = pd_loaded.copy().sort_values(["symbol", "timestamp"]).reset_index(drop=True)

    # same rows, same symbols, same timestamps
    assert len(pd_df) == len(pl_pd)
    assert pd_df["symbol"].tolist() == pl_pd["symbol"].tolist()
    assert pd_df["timestamp"].tolist() == pl_pd["timestamp"].tolist()

    # prices equal within float tolerance
    np.testing.assert_allclose(pd_df["price"].to_numpy(dtype=float),
                               pl_pd["price"].to_numpy(dtype=float),
                               rtol=1e-12, atol=1e-12)