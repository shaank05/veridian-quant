from datetime import datetime
from sqlalchemy import text
from src.veridian_quant.data.db_client import DatabaseClient

def cleanup_expired_instruments():
    """
    Identifies and archives expired derivative instruments and their price data
    to keep the primary tables lean and performant.
    """
    db = DatabaseClient()
    engine = db.get_engine()  # Use the SQLAlchemy engine
    today = datetime.now().date()
    BATCH_SIZE = 2000 # Keeps progress tracking consistent
    
    try:
        # 1. Identify Expired Derivatives using SQLAlchemy text()
        identify_query = text("""
            SELECT instrument_key 
            FROM instrument_derivatives 
            WHERE expiry_date < :today
        """)
        
        with engine.connect() as conn:
            result = conn.execute(identify_query, {"today": today})
            expired_keys = [row[0] for row in result.fetchall()]
        
        total_to_delete = len(expired_keys)
        
        if not expired_keys:
            print("✅ No expired instruments found. Database is already lean.")
            return

        print(f"📦 Found {total_to_delete} expired contracts. Moving to archive...")

        # 2. Process in Batches for Progress Tracking and Transaction Safety
        archived_count = 0
        price_archived_count = 0
        deleted_count = 0

        for i in range(0, total_to_delete, BATCH_SIZE):
            batch = expired_keys[i:i + BATCH_SIZE]
            
            # Using a single transaction per batch for efficiency and integrity
            with engine.begin() as conn:
                # A. Nullify underlying_key references to prevent ForeignKeyViolation
                # This fixes the error where an expired instrument is an underlying for another contract
                nullify_query = text("""
                    UPDATE instrument_derivatives 
                    SET underlying_key = NULL 
                    WHERE underlying_key = ANY(:batch);
                """)
                conn.execute(nullify_query, {"batch": batch})

                # B. Archive Derivative Metadata
                archive_query = text("""
                    INSERT INTO instruments_expired_archive (
                        instrument_key, underlying_key, expiry_date, strike_price, option_type, lot_size
                    )
                    SELECT instrument_key, underlying_key, expiry_date, strike_price, option_type, lot_size
                    FROM instrument_derivatives
                    WHERE instrument_key = ANY(:batch)
                    ON CONFLICT (instrument_key) DO NOTHING;
                """)
                arch_res = conn.execute(archive_query, {"batch": batch})
                archived_count += arch_res.rowcount

                # C. Archive Price Data (Moving to prices_ohlc_archive)
                # We do this BEFORE deleting from instruments to avoid CASCADE wipe
                price_archive_query = text("""
                    INSERT INTO prices_ohlc_archive (
                        timestamp, instrument_key, open, high, low, close, volume, open_interest, interval
                    )
                    SELECT timestamp, instrument_key, open, high, low, close, volume, open_interest, interval
                    FROM prices_ohlc
                    WHERE instrument_key = ANY(:batch);
                """)
                price_res = conn.execute(price_archive_query, {"batch": batch})
                price_archived_count += price_res.rowcount

                # D. Delete from Master Table (Triggers CASCADE in instrument_derivatives and prices_ohlc)
                delete_query = text("DELETE FROM instruments WHERE instrument_key = ANY(:batch);")
                del_res = conn.execute(delete_query, {"batch": batch})
                deleted_count += del_res.rowcount
                
            print(f"   - Progress: {min(i + BATCH_SIZE, total_to_delete)} / {total_to_delete} processed...")
            if price_res.rowcount > 0:
                print(f"     └─ Archived {price_res.rowcount} OHLC rows for this batch.")

        print("\n" + "="*40)
        print(f"🎉 CLEANUP SUMMARY")
        print(f"   - Total Expired Identified: {total_to_delete}")
        print(f"   - Metadata Archived:        {archived_count}")
        print(f"   - OHLC Rows Archived:       {price_archived_count}")
        print(f"   - Instruments Deleted:      {deleted_count}")
        print("="*40)

    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        # Note: engine.begin() automatically rolls back the current batch on exception

if __name__ == "__main__":
    cleanup_expired_instruments()