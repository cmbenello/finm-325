# backtester/price_loader.py
import pandas as pd
from pathlib import Path

class PriceLoader:
    """Loads a local CSV or Parquet file and returns a price Series."""

    def __init__(self, path: str, date_col: str = "Date", price_col: str = "Close"):
        self.path = Path(path)
        self.date_col = date_col
        self.price_col = price_col
        if not self.path.exists():
            raise FileNotFoundError(f"File not found: {self.path}")

    def series(self) -> pd.Series:
        """Return a pandas.Series of prices indexed by datetime."""
        if self.path.suffix == ".csv":
            df = pd.read_csv(self.path)
        elif self.path.suffix in {".parquet", ".pq"}:
            df = pd.read_parquet(self.path)
        else:
            raise ValueError("File must be .csv or .parquet")

        if self.date_col not in df or self.price_col not in df:
            raise KeyError("Missing required columns")

        s = (
            df[[self.date_col, self.price_col]]
            .assign(**{self.date_col: pd.to_datetime(df[self.date_col])})
            .dropna(subset=[self.date_col])
            .set_index(self.date_col)[self.price_col]
            .astype(float)
            .sort_index()
        )
        s.name = self.price_col
        return s