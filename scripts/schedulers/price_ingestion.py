import os
import time
import json
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import text # Use SQLAlchemy text for raw SQL execution
import upstox_client
from upstox_client.rest import ApiException
from src.veridian_quant.data.db_client import DatabaseClient

# --- LOGGING CONFIGURATION ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ingestion.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- CONFIGURATION FROM ENV ---
UPSTOX_ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")
MAX_DAYS_1M = int(os.getenv("MAX_PAGINATION_DAYS_1M", 30))
MAX_DAYS_1D = int(os.getenv("MAX_PAGINATION_DAYS_1D", 365))
INGESTION_MODE = os.getenv("DATA_INGESTION_MODE", "WATCHLIST")
HISTORICAL_LOOKBACK = int(os.getenv("HISTORICAL_LOOKBACK_DAYS", 0))
API_VERSION = str(os.getenv("UPSTOX_API_VERSION"))


class PriceIngestor:
    def __init__(self):
        self.db = DatabaseClient()
        self.engine = self.db.get_engine() # Use engine for pooled connections 
        configuration = upstox_client.Configuration()
        configuration.access_token = UPSTOX_ACCESS_TOKEN
        self.api_instance = upstox_client.HistoryApi(upstox_client.ApiClient(configuration))

    def load_watchlist(self):
        path = os.path.join("config", "watchlist.json")
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Could not load {path}: {e}")
            return {}

    def get_keys_from_symbols(self, symbols):
        """Resolves symbols to instrument keys using精 确 SQLAlchemy text binding."""
        if not symbols: return []
        
        # --- MODIFIED: Restrict retrieval strictly to NSE tokens to avoid dual-exchange duplication ---
        # TODO: Include BSE exchange support here in the future if cross-exchange validation becomes required.
        query = text("""
            SELECT instrument_key FROM instruments 
            WHERE symbol = ANY(:symbols) 
              AND (instrument_key LIKE 'NSE_EQ|%' OR instrument_key LIKE 'NSE_INDEX|%')
        """)
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(query, {"symbols": list(symbols)})
                print(f"query: --->>> {query}")
                return [row[0] for row in result.fetchall()]
        except Exception:
            logger.exception("Error resolving symbols.")
            return []

    def get_last_timestamp(self, instrument_key, interval):
        """Retrieves the latest available candle timestamp from the DB."""
        query = text("SELECT MAX(timestamp) FROM prices_ohlc WHERE instrument_key = :ik AND interval = :iv")
        try:
            with self.engine.connect() as conn:
                result = conn.execute(query, {"ik": instrument_key, "iv": interval})
                val = result.scalar()
                return val if val else None
        except Exception:
            return None

    def fetch_with_retry(self, instrument_key, interval, start, end, retries=3):
        from_date = start.strftime('%Y-%m-%d')
        to_date = end.strftime('%Y-%m-%d')

        for attempt in range(retries):
            try:
                api_response = self.api_instance.get_historical_candle_data1(
                    instrument_key, interval, to_date, from_date, str(API_VERSION)
                )
                if api_response.status == 'success' and api_response.data.candles:
                    return api_response.data.candles
                return []
            except ApiException as e:
                if e.status == 429:
                    wait = (attempt + 1) * 5
                    logger.warning(f"Rate limit hit. Waiting {wait}s...")
                    time.sleep(wait)
                else:
                    logger.error(f"Upstox API Error: {e}")
                    break
        return None

    def fetch_and_save(self, instrument_key, interval):
        """Fetches historical data in chunks and saves to DB via engine."""
        last_ts = self.get_last_timestamp(instrument_key, interval)
        now = datetime.now(timezone.utc)
        
        # Commented to insert data for 2018 and 2019
        if HISTORICAL_LOOKBACK > 0:
            start_date = now - timedelta(days=HISTORICAL_LOOKBACK)
        elif last_ts:
            start_date = last_ts if last_ts.tzinfo else last_ts.replace(tzinfo=timezone.utc)
            start_date += timedelta(seconds=1)
        else:
            # Initial backfill logic
            days = 365 if interval == '1minute' else 2300 
            start_date = now - timedelta(days=days)

        # --- MARKOV MODE: FORCE BACKFILL GAPS FOR 2018 & 2019 BACKTESTS ---
        # Instead of picking up from the latest date forward, we establish a strict structural 
        # lower bound at January 1, 2018 to pull historical data required for 2020 matrices.
        # target_backfill_start = datetime(2018, 1, 1, tzinfo=timezone.utc)
        
        # Delete/Comment once data is filled for 2018 and 2019
        # Pull the absolute earliest timestamp currently existing in the table
        # query_earliest = text("SELECT MIN(timestamp) FROM prices_ohlc WHERE instrument_key = :ik AND interval = :iv")
        # with self.engine.connect() as conn:
        #     earliest_ts = conn.execute(query_earliest, {"ik": instrument_key, "iv": interval}).scalar()
            
        # if earliest_ts:
        #     earliest_ts = earliest_ts if earliest_ts.tzinfo else earliest_ts.replace(tzinfo=timezone.utc)

        # if earliest_ts and earliest_ts <= target_backfill_start:
        #     # 1. If we already have data covering 2018-01-01, standard incremental ingestion behavior applies (Forward-looking)
        #     if last_ts:
        #         start_date = last_ts if last_ts.tzinfo else last_ts.replace(tzinfo=timezone.utc)
        #         start_date += timedelta(seconds=1)
        #     else:
        #         start_date = now - timedelta(days=365)
        # else:
        #     # 2. If data is completely missing or starts later than 2018, force step back to 2018-01-01 to pull backward
        #     logger.info(f"⏳ Backfill Gap Detected for {instrument_key}. Forcing lookup starting from 2018-01-01.")
        #     start_date = target_backfill_start

        
        chunk_start = start_date
        max_days = MAX_DAYS_1D if interval == 'day' else MAX_DAYS_1M

        while chunk_start < now:
            chunk_end = min(chunk_start + timedelta(days=max_days), now)
            if chunk_start >= chunk_end: break

            logger.info(f"FETCHING {interval} | {instrument_key} | {chunk_start.date()} to {chunk_end.date()}")
            candles = self.fetch_with_retry(instrument_key, interval, chunk_start, chunk_end)
            
            if candles:
                self.save_to_db(instrument_key, interval, candles)
            else:
                logger.warning(f"No data for {instrument_key} in window {chunk_start.date()} to {chunk_end.date()}. Skipping...")
            
            chunk_start = chunk_end + timedelta(seconds=1)
            time.sleep(0.5) 

    def save_to_db(self, instrument_key, interval, candles):
        """
        Saves candles using an UPSERT logic via SQLAlchemy.
        Optimized to use a single multi-row INSERT with parameter binding.
        """
        data_list = []
        for c in candles:
            try:
                data_list.append({
                    "ts": c[0],
                    "ik": instrument_key,
                    "op": float(c[1]),
                    "hi": float(c[2]),
                    "lo": float(c[3]),
                    "cl": float(c[4]),
                    "vo": int(float(c[5])),
                    "oi": int(float(c[6])) if len(c) > 6 else 0,
                    "iv": interval
                })
            except (IndexError, ValueError, TypeError) as e:
                logger.warning(f"Skipping malformed candle for {instrument_key}: {e}")
                continue
        
        if not data_list: return

        query = text("""
            INSERT INTO prices_ohlc (timestamp, instrument_key, open, high, low, close, volume, open_interest, interval)
            VALUES (:ts, :ik, :op, :hi, :lo, :cl, :vo, :oi, :iv)
            ON CONFLICT (timestamp, instrument_key, interval) DO UPDATE SET 
            close = EXCLUDED.close, 
            volume = EXCLUDED.volume,
            open_interest = EXCLUDED.open_interest;
        """)

        try:
            with self.engine.begin() as conn:
                conn.execute(query, data_list)
                logger.info(f"SUCCESS: Upserted {len(data_list)} rows for {instrument_key}")
        except Exception:
            logger.exception("DB Save Error")

    def run(self):
        """Production workflow leveraging SQLAlchemy engine."""
        instrument_keys = []

        if INGESTION_MODE == "WATCHLIST":
            logger.info("Running in WATCHLIST mode.")
            watchlist = self.load_watchlist()
            symbols = []
            for v in watchlist.values(): 
                print(f"v: --->>> {v}")
                symbols.extend(v)
                print(f"symbols: --->>> {symbols}")
            instrument_keys = self.get_keys_from_symbols(list(set(symbols)))

        elif INGESTION_MODE == "FULL":
            logger.info("Running in FULL mode. Syncing all active instruments.")
            query = text("SELECT instrument_key FROM instruments")
            try:
                with self.engine.connect() as conn:
                    result = conn.execute(query)
                    instrument_keys = [row[0] for row in result.fetchall()]
            except Exception:
                logger.exception("Failed to fetch instrument list.")

        print(f"instrument_keys: --->>> {instrument_keys}")

        if not instrument_keys:
            logger.error("No valid instruments identified for sync.")
            return

        for key in instrument_keys:
            try:
                # self.fetch_and_save(key, '1minute')
                if INGESTION_MODE == "WATCHLIST":
                    self.fetch_and_save(key, 'day')
            except Exception:
                logger.exception(f"CRITICAL: Failed to sync {key}.")

if __name__ == "__main__":
    if not UPSTOX_ACCESS_TOKEN:
        print("❌ ERROR: UPSTOX_ACCESS_TOKEN missing.")
    else:
        PriceIngestor().run()