import os
import requests
import pandas as pd
import gzip
import io
import json
from datetime import datetime
from src.veridian_quant.data.providers.base import DataProvider

class UpstoxProvider(DataProvider):
    def __init__(self):
        self.token = os.getenv("UPSTOX_ACCESS_TOKEN") or os.getenv("UPSTOX_ANALYTICS_TOKEN")
        self.base_url = os.getenv("UPSTOX_BASE_URL")
        self.headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {self.token}'
        }
        self.instrument_url = os.getenv("UPSTOX_INSTRUMENT_URL")

    def _convert_expiry(self, expiry_val):
        """
        Internal helper to handle Upstox's numeric expiry timestamps.
        Converts milliseconds to Python date objects.
        """
        if not expiry_val or pd.isna(expiry_val):
            return None
        try:
            # Handle milliseconds (13 digits) vs seconds (10 digits)
            ts = expiry_val / 1000 if expiry_val > 1e11 else expiry_val
            return datetime.fromtimestamp(ts).date()
        except Exception:
            return None

    def get_historical_data(self, instrument_key: str, interval: str = '1minute', 
                            to_date: str = None, from_date: str = None) -> pd.DataFrame:
        if not to_date:
            to_date = datetime.now().strftime('%Y-%m-%d')
        if not from_date:
            from_date = to_date

        url = f"{self.base_url}/historical-candle/{instrument_key}/{interval}/{to_date}/{from_date}"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print(f"❌ Upstox API Error: {e}")
            return pd.DataFrame()

        candles = data.get('data', {}).get('candles', [])
        if not candles:
            return pd.DataFrame()

        df = pd.DataFrame(candles, columns=['time', 'open', 'high', 'low', 'close', 'volume', 'oi'])
        df['time'] = pd.to_datetime(df['time'])
        
        return df[['time', 'open', 'high', 'low', 'close', 'volume']]

    def get_instrument_list(self) -> pd.DataFrame:
        """
        Fetches the master instrument list and cleans provider-specific 
        formats (like expiry timestamps) before returning.
        """
        print(f"🔗 Requesting: {self.instrument_url}")
        try:
            response = requests.get(self.instrument_url, headers=self.headers, stream=True, timeout=30)
            response.raise_for_status()
            
            with gzip.GzipFile(fileobj=io.BytesIO(response.content)) as gz:
                decompressed_data = gz.read()
            
            raw_data = json.loads(decompressed_data)
            df = pd.DataFrame(raw_data)

            # 1. Standardize Column Names
            rename_map = {
                'tradingsymbol': 'symbol',
                'trading_symbol': 'symbol',
                'display_name': 'name'
            }
            df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

            # 2. Provider-Specific Cleaning: Handle Expiry Dates
            # This moves the logic out of your sync script and into the provider
            if 'expiry' in df.columns:
                df['expiry_date'] = df['expiry'].apply(self._convert_expiry)

            # 3. Handle specific numeric types for DB compatibility
            if 'strike_price' in df.columns:
                df['strike_price'] = pd.to_numeric(df['strike_price'], errors='coerce')

            return df
            
        except Exception as e:
            print(f"❌ Decompression/Parsing Error: {e}")
            return pd.DataFrame()