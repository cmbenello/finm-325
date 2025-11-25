import pandas as pd

from .config import PROCESSED_DATA_PATH


class MarketDataGateway:
    """
    Simple gateway that simulates a live market feed by streaming
    cleaned historical bars one at a time.
    """

    def __init__(self, data_path=PROCESSED_DATA_PATH):
        self.data_path = data_path
        self._df: pd.DataFrame | None = None

    def load_data(self) -> None:
        df = pd.read_csv(self.data_path, parse_dates=["Datetime"])
        df = df.set_index("Datetime").sort_index()
        self._df = df

    def get_dataframe(self) -> pd.DataFrame:
        """
        Return the full cleaned DataFrame.
        """
        if self._df is None:
            self.load_data()
        return self._df

    def __iter__(self):
        if self._df is None:
            self.load_data()

        # Yield (timestamp, row) pairs to mimic real-time bars
        for ts, row in self._df.iterrows():
            yield ts, row