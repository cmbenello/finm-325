import time
from pathlib import Path
from typing import List, Optional, Sequence

import pandas as pd
import requests
import yfinance as yf

class PriceLoader:
    def __init__(self, start_time: str, end_time: str, output_dir: str):
        self.start_time = start_time
        self.end_time = end_time
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def fetch_sp500_tickers(self) -> List[str]:
        """Return the current S&P 500 ticker symbols as listed today."""
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        response = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            timeout=15,
        )
        response.raise_for_status()
        tables = pd.read_html(response.text)
        sp500_table = tables[0]
        # Replace '.' with '-' to match common ticker formatting (e.g., BRK.B -> BRK-B)
        tickers = sp500_table["Symbol"].str.replace(".", "-", regex=False)
        return tickers.sort_values().tolist()

    #Function that gets data for all tickers in batched loads
    def batch_download(self, batch_size: int = 100, pause: float = 2.0, tickers: Optional[Sequence[str]] = None):
        if tickers is None:
            tickers = self.fetch_sp500_tickers()
        for i in range(0, len(tickers), batch_size):
            batch = tickers[i: i + batch_size]
            try:
                df = yf.download(
                    batch,
                    start = self.start_time,
                    end = self.end_time,
                    group_by = "ticker",
                    auto_adjust = True,
                    threads = True
                )
                if df.empty:
                    continue

                if isinstance(df.columns, pd.MultiIndex):
                    available = set(df.columns.get_level_values(0))
                    for t in batch:
                        if t not in available:
                            continue
                        df[t].reset_index().to_parquet(self.output_dir / f"{t}.parquet", engine="pyarrow", index=False)
                else:
                    # Single ticker downloads return a flat column structure
                    ticker_name = batch[0]
                    df.reset_index().to_parquet(self.output_dir / f"{ticker_name}.parquet", engine="pyarrow", index=False)
            except Exception as e:
                print(f"Batch {batch} failed: {e}")
            time.sleep(pause)
        
    
    #Reads a ticker 
    def read_ticker(self, ticker):
        file = self.output_dir / f"{ticker}.parquet"
        return pd.read_parquet(file, engine = "pyarrow")

    
if __name__ == "__main__":
    loader = PriceLoader("2005-01-01", "2025-01-01", "data/")
    tickers = loader.fetch_sp500_tickers()
    print(len(tickers), tickers[:10])
    # loader.batch_download(tickers=tickers)
    print(loader.read_ticker("AAPL"))
