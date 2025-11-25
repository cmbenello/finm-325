from .download_market_data import download_and_save_raw_data
from .clean_data import load_clean_and_save
from .strategy import MovingAverageCrossoverStrategy
from .config import PROCESSED_DATA_PATH


def main():
    # Step 1: Download raw intraday data
    download_and_save_raw_data()

    # Step 2: Clean and feature engineering
    df_clean = load_clean_and_save()

    # Step 3: Strategy signals
    strategy = MovingAverageCrossoverStrategy()
    df_with_signals = strategy.generate_signals(df_clean)

    # For now, just preview the last few rows
    print("Sample of cleaned data with signals:")
    print(df_with_signals.tail()[["Close", "ma_20", "ma_60", "signal", "position"]])

    # Optionally, overwrite processed file with signals included
    df_with_signals.to_csv(PROCESSED_DATA_PATH)
    print(f"Updated processed file with signals saved to {PROCESSED_DATA_PATH}")


if __name__ == "__main__":
    main()