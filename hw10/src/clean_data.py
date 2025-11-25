import pandas as pd
import numpy as np

from .config import (
    RAW_DATA_PATH,
    PROCESSED_DATA_PATH,
    RETURN_COLUMN,
    LOG_RETURN_COLUMN,
    SHORT_MA_WINDOW,
    LONG_MA_WINDOW,
    SHORT_MA_COL,
    LONG_MA_COL,
    VOL_COL,
)


def load_raw_data(path=RAW_DATA_PATH) -> pd.DataFrame:
    """
    Load raw CSV with columns: Datetime, Open, High, Low, Close, Volume.
    """
    df = pd.read_csv(path, parse_dates=["Datetime"])
    return df


def clean_and_add_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean the raw data and add derived features:
      - simple returns
      - log returns
      - short and long moving averages of Close
      - rolling volatility of returns
    """
    # Drop missing rows
    df = df.dropna()

    # Drop exact duplicates
    df = df.drop_duplicates(subset=["Datetime", "Open", "High", "Low", "Close", "Volume"])

    # Set index to Datetime and sort
    df = df.set_index("Datetime")
    df = df.sort_index()

    # Ensure numeric columns are floats
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # After coercion, drop any rows with NaNs again
    df = df.dropna()

    # Returns
    df[RETURN_COLUMN] = df["Close"].pct_change()
    df[LOG_RETURN_COLUMN] = np.log(df["Close"]).diff()

    # Moving averages
    df[SHORT_MA_COL] = df["Close"].rolling(window=SHORT_MA_WINDOW, min_periods=1).mean()
    df[LONG_MA_COL] = df["Close"].rolling(window=LONG_MA_WINDOW, min_periods=1).mean()

    # Rolling volatility (standard deviation of returns)
    df[VOL_COL] = df[RETURN_COLUMN].rolling(window=LONG_MA_WINDOW, min_periods=1).std()

    # Drop initial NaNs from returns if you want a "fully valid" set
    df = df.dropna()

    return df


def load_clean_and_save(
    raw_path: str | None = None,
    processed_path: str | None = None,
) -> pd.DataFrame:
    """
    High-level function for Part 1, Step 2:
      - Load raw CSV
      - Clean and add features
      - Save processed CSV
      - Return cleaned DataFrame
    """
    if raw_path is None:
        raw_path = RAW_DATA_PATH
    if processed_path is None:
        processed_path = PROCESSED_DATA_PATH

    df_raw = load_raw_data(raw_path)
    df_clean = clean_and_add_features(df_raw)
    df_clean.to_csv(processed_path)
    print(f"Saved cleaned data with features to {processed_path}")
    return df_clean


if __name__ == "__main__":
    load_clean_and_save()