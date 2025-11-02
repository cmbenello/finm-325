# tests/conftest.py
from __future__ import annotations
from pathlib import Path
import sys
import json
import pandas as pd
import polars as pl
import pytest

# --- ensure project root is importable ---
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data_loader import load_market_data_pandas, load_market_data_polars  # noqa: E402

DATA_CSV = PROJECT_ROOT / "data" / "market_data-1.csv"
PORTFOLIO_JSON = PROJECT_ROOT / "portfolio_structure-1.json"

@pytest.fixture(scope="session")
def pd_loaded() -> pd.DataFrame:
    res = load_market_data_pandas(DATA_CSV)
    df = res.df.reset_index() if isinstance(res.df.index, pd.DatetimeIndex) else res.df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    return df.sort_values(["symbol", "timestamp"], kind="mergesort").reset_index(drop=True)

@pytest.fixture(scope="session")
def pl_loaded() -> pl.DataFrame:
    res = load_market_data_polars(DATA_CSV)
    return res.df.sort(["symbol", "timestamp"])

@pytest.fixture(scope="session")
def symbols(pd_loaded: pd.DataFrame) -> list[str]:
    return sorted(pd_loaded["symbol"].unique().tolist())

@pytest.fixture(scope="session")
def portfolio_struct() -> dict:
    with open(PORTFOLIO_JSON, "r") as f:
        return json.load(f)