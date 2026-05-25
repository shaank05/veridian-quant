import os
import json
import logging
from datetime import datetime, timedelta
from sqlalchemy import text
import upstox_client
from upstox_client.rest import ApiException
from src.veridian_quant.data.db_client import DatabaseClient

# --- LOGGING CONFIGURATION ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MarketIndicatorIngestor:
    def __init__(self):
        self.db = DatabaseClient()
        self.engine = self.db.get_engine()
        self.env = os.getenv("ENV", "DEV")
        self.api_version = os.getenv("UPSTOX_API_VERSION", "2.0")
        self.indicators_config = self._load_config()
        
    def _load_config(self):
        config_path = os.path.join("config", "indicators.json")
        try:
            with open(config_path, "r") as f:
                return json.load(f).get("market_indicators", [])
        except FileNotFoundError:
            print(f"❌ ERROR: Config file not found at {config_path}")
            return []

    def fetch_and_save(self, indicator):
        name = indicator['name']
        key = indicator['upstox_key']
        freq = indicator['frequency']
        ind_type = indicator.get('type', 'ohlc') # Default to ohlc
        
        to_date = datetime.now().strftime('%Y-%m-%d')
        from_date = '2020-01-01' if self.env == "DEV" else (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

        print(f"\n{'='*60}")
        print(f"📡 INDICATOR: {name} | MODE: {self.env} | TYPE: {ind_type}")
        print(f"📅 RANGE: {from_date} to {to_date}")
        print(f"{'='*60}")

        try:
            history_api = upstox_client.HistoryApi()
            api_response = history_api.get_historical_candle_data1(
                key, freq, to_date, from_date, self.api_version
            )
            
            candles = api_response.data.candles
            if not candles:
                print(f"⚠️  No data returned for {name}. Skipping...")
                return

            total_rows = len(candles)
            print(f"📥 Received {total_rows} candles from Upstox. Starting DB insertion...")

            # Metadata for the Ensemble Layer to know provenance
            meta_payload = json.dumps({"source": "upstox", "ind_type": ind_type})

            insert_query = text("""
                INSERT INTO market_indicators 
                (timestamp, indicator_name, open, high, low, close, value, interval, metadata)
                VALUES (:ts, :name, :o, :h, :l, :c, :val, :inter, :meta)
                ON CONFLICT (timestamp, indicator_name, interval) DO NOTHING;
            """)

            rows_inserted = 0
            with self.engine.begin() as conn:
                for idx, c in enumerate(candles):
                    # POLYMORPHIC MAPPING:
                    # If type is OHLC, map the list. If type is VALUE, put c[4] (close) into 'value'.
                    data_map = {
                        "ts": c[0],
                        "name": name,
                        "o": c[1] if ind_type == 'ohlc' else None,
                        "h": c[2] if ind_type == 'ohlc' else None,
                        "l": c[3] if ind_type == 'ohlc' else None,
                        "c": c[4],
                        "val": c[4] if ind_type == 'value' else None,
                        "inter": freq,
                        "meta": meta_payload
                    }
                    
                    result = conn.execute(insert_query, data_map)
                    if result.rowcount > 0:
                        rows_inserted += 1
                    
                    # Progress Print every 50 rows
                    if (idx + 1) % 50 == 0 or (idx + 1) == total_rows:
                        pct = ((idx + 1) / total_rows) * 100
                        print(f"⏳ Progress: {pct:3.0f}% | Processed: {idx+1}/{total_rows} | New Rows: {rows_inserted}", end='\r')

            print(f"\n✅ FINISHED: {name} | Total Processed: {total_rows} | New Inserts: {rows_inserted}")

        except ApiException as e:
            print(f"❌ API ERROR for {name}: {e}")
        except Exception as e:
            print(f"❌ CRITICAL ERROR for {name}: {str(e)}")

    def run(self):
        if not os.getenv("UPSTOX_ACCESS_TOKEN"):
            print("❌ ACCESS DENIED: UPSTOX_ACCESS_TOKEN not found in .env")
            return
        
        start_time = datetime.now()
        for indicator in self.indicators_config:
            self.fetch_and_save(indicator)
        
        duration = datetime.now() - start_time
        print(f"\n{'*'*60}")
        print(f"✨ ALL INDICATORS SYNCED | Total Time: {duration}")
        print(f"{'*'*60}\n")

if __name__ == "__main__":
    MarketIndicatorIngestor().run()