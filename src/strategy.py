from abc import ABC, abstractmethod
import pandas as pd

class Strategy(ABC):
    @abstractmethod
    def signal_for_ticker(self, prices: pd.DataFrame) -> pd.DataFrame:
        """Inputs one ticker and then outputs signal for it """
        pass

