import logging
from sqlalchemy import text # Use SQLAlchemy text for SQL execution
from src.veridian_quant.data.db_client import DatabaseClient # Import your existing DB client
from scripts.schedulers.price_ingestion import PriceIngestor # Import your existing ingestor

logger = logging.getLogger(__name__)

class DataReconciler:
    def __init__(self):
        self.db = DatabaseClient()
        self.engine = self.db.get_engine() # Utilize the SQLAlchemy engine
        self.ingestor = PriceIngestor()
        # Diwali Muhurat or half-days where lower counts are expected
        self.special_days = {'2025-10-21': 60} 

    def get_gaps(self):
        """
        Identifies days where the 1-minute candle count is lower than expected.
        Uses SQLAlchemy text() for parameter safety and structured results.
        """
        print("🔍 Scanning database for data gaps...")
        query = text("""
            SELECT instrument_key, date_trunc('day', timestamp)::date as gap_day, count(*) as actual_count
            FROM prices_ohlc
            WHERE interval = '1minute'
            GROUP BY 1, 2
            HAVING count(*) < 370 AND count(*) > 0
            ORDER BY gap_day DESC;
        """)
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(query)
                results = result.fetchall()
                print(f"📊 Found {len(results)} potential gaps in the database.")
                return results
        except Exception as e:
            print(f"❌ SQL Error in get_gaps: {e}")
            logger.exception("Error identifying gaps.")
            return []

    def fix_gaps(self):
        """
        Iterates through identified gaps, deletes the incomplete data, 
        and triggers a re-fetch from the Ingestor.
        """
        gaps = self.get_gaps()
        if not gaps:
            print("✅ No data gaps found matching the criteria (Count < 370).")
            return

        for row in gaps:
            instrument, day, count = row
            # Format date for comparison and logging
            day_str = day.strftime('%Y-%m-%d') if hasattr(day, 'strftime') else str(day)
            target = self.special_days.get(day_str, 375)

            if count >= target:
                print(f"ℹ️ Skipping {instrument} on {day_str}: {count} rows is normal for this day.")
                continue

            print(f"⚠️ Fixing Gap: {instrument} | {day_str} | Current: {count} | Target: {target}")

            # Using engine.begin() to ensure the DELETE is committed automatically
            delete_query = text("""
                DELETE FROM prices_ohlc 
                WHERE instrument_key = :ik 
                AND timestamp::date = :day 
                AND interval = '1minute'
            """)
            
            try:
                with self.engine.begin() as conn:
                    result = conn.execute(delete_query, {"ik": instrument, "day": day_str})
                    print(f"  🗑️ Deleted {result.rowcount} rows for {instrument}...")
            except Exception as e:
                print(f"  ❌ Delete failed: {e}")
                continue

            try:
                # Trigger the re-fetch logic in the ingestor
                # The updated PriceIngestor will now use SQLAlchemy internally as well
                self.ingestor.fetch_and_save(instrument, '1minute') 
                print(f"  ✨ Successfully re-triggered sync for {instrument}")
            except Exception as e:
                print(f"  ❌ Ingestion failed for {instrument}: {e}")

if __name__ == "__main__":
    reconciler = DataReconciler()
    reconciler.fix_gaps()