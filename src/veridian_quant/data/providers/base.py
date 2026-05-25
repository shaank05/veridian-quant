from abc import ABC, abstractmethod
import pandas as pd

class DataProvider(ABC):
    """
    Abstract Base Class for all market data providers.
    Ensures that the Core Engine remains agnostic of the data source.
    """
    
    @abstractmethod
    def get_historical_data(self, instrument_key: str, interval: str, to_date: str, from_date: str) -> pd.DataFrame:
        """
        Fetches historical OHLCV data.
        Returns:
            pd.DataFrame: Columns [time, open, high, low, close, volume]
        """
        pass

    @abstractmethod
    def get_instrument_list(self) -> pd.DataFrame:
        """
        Every provider must implement this to return a standardized 
        DataFrame with columns: [instrument_key, exchange, symbol, name, instrument_type]
        """
        pass