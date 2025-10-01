from abc import ABC, abstractmethod
import pandas as pd

class Strategy(ABC):
    @abstractmethod
    def generate_signals(self, prices: pd.DataFrame) -> pd.DataFrame:
        """Generates signal at a certain time period """
        pass

