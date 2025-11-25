# src/alpaca_data.py

from __future__ import annotations

from datetime import datetime, timedelta

import alpaca_trade_api as tradeapi
import pandas as pd

from .alpaca_settings import API_KEY_ID, API_SECRET_KEY, BASE_URL, SYMBOL, TIMEFRAME
from .config import RAW_DATA_DIR


def make_alpaca_client() -> tradeapi.REST:
    if not API_KEY_ID or not API_SECRET_KEY:
        raise RuntimeError("Set ALPACA_API_KEY_ID and ALPACA_API_SECRET_KEY env vars.")
    api = tradeapi.REST(API_KEY_ID, API_SECRET_KEY, BASE_URL, api_version="v2")
    return api


def download_intraday_data(
    days: int = 7,
    symbol: str = SYMBOL,
    timeframe: str = TIMEFRAME,
) -> pd.DataFrame:
    api = make_alpaca_client()

    end = datetime.utcnow()
    start = end - timedelta(days=days)

    bars = api.get_bars(
        symbol,
        timeframe,
        start=start.isoformat() + "Z",
        end=end.isoformat() + "Z",
        feed="iex"
    )

    if bars.df.empty:
        raise RuntimeError("No data returned from Alpaca. Check symbol/timeframe.")

    df = bars.df.reset_index()
    # The IEX feed does not include a 'symbol' column, so no filtering is needed.
    df.rename(
        columns={
            "timestamp": "Datetime",
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
        },
        inplace=True,
    )

    df = df[["Datetime", "Open", "High", "Low", "Close", "Volume"]]
    df["Datetime"] = pd.to_datetime(df["Datetime"], utc=True).dt.tz_convert(None)

    return df


def download_and_save_csv(days: int = 7) -> str:
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DATA_DIR / "alpaca_intraday_raw.csv"

    df = download_intraday_data(days=days)
    df.to_csv(path, index=False)
    print(f"Saved Alpaca intraday data to {path}")
    return str(path)


if __name__ == "__main__":
    download_and_save_csv()