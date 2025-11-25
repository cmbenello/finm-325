import yfinance as yf
import pandas as pd

from .config import (
    ASSET_TYPE,
    TICKER,
    DATA_PERIOD,
    DATA_INTERVAL,
    RAW_DATA_PATH,
)


def download_equity_data() -> pd.DataFrame:
    """
    Download intraday equity data using yfinance and return a DataFrame
    with columns: Datetime, Open, High, Low, Close, Volume.
    """
    data = yf.download(
        tickers=TICKER,
        period=DATA_PERIOD,
        interval=DATA_INTERVAL,
        auto_adjust=False,
        progress=False,
    )

    if data.empty:
        raise RuntimeError("Downloaded data is empty. Check ticker/period/interval.")

    # Ensure the index is a DatetimeIndex without timezone for consistency
    if data.index.tz is not None:
        data = data.tz_convert(None)

    df = data.reset_index()

    # yfinance typically names the index "Datetime" or "Date" depending on frequency
    if "Datetime" in df.columns:
        datetime_col = "Datetime"
    elif "Date" in df.columns:
        datetime_col = "Date"
        df.rename(columns={"Date": "Datetime"}, inplace=True)
        datetime_col = "Datetime"
    else:
        raise RuntimeError("Could not find a datetime column in downloaded data.")

    # Keep only required columns
    df = df[["Datetime", "Open", "High", "Low", "Close", "Volume"]]

    # Enforce datetime dtype
    df["Datetime"] = pd.to_datetime(df["Datetime"])

    return df


def download_and_save_raw_data() -> None:
    """
    High-level function for Part 1, Step 1:
    - Download data
    - Save to CSV at RAW_DATA_PATH
    """
    if ASSET_TYPE != "equity":
        raise NotImplementedError(
            "Only equity via yfinance is implemented in Part 1. "
            "Crypto (Binance) can be added later."
        )

    df = download_equity_data()
    df.to_csv(RAW_DATA_PATH, index=False)
    print(f"Saved raw market data to {RAW_DATA_PATH}")


if __name__ == "__main__":
    download_and_save_raw_data()