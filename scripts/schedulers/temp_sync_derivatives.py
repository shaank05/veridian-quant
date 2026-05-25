import os
import sys
import pandas as pd
import numpy as np
from sqlalchemy import text # Use SQLAlchemy text for SQL execution

# Ensuring the script can find the 'src' package
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.veridian_quant.data.providers.factory import get_active_provider
from src.veridian_quant.data.db_client import DatabaseClient

def sync_derivatives_only():
    """
    Performs a targeted sync for derivatives, ensuring parent-child 
    integrity between instruments and instrument_derivatives.
    """
    provider = get_active_provider()
    db = DatabaseClient()
    engine = db.get_engine() # Utilize the SQLAlchemy engine
    BATCH_SIZE = 2000
    
    deriv_inserted = 0
    
    print("🚀 Starting Validated Derivative Sync...")
    df = provider.get_instrument_list()
    
    if df is None or df.empty:
        print("❌ Failed to fetch instrument list.")
        return

    # 1. Clean data for BIGINT and handle NaN
    df['lot_size'] = pd.to_numeric(df['lot_size'], errors='coerce').fillna(1).astype(int)
    df['underlying_key'] = df['underlying_key'].replace({np.nan: None})

    # 2. Filter for derivatives (using the 'expiry' column from provider)
    derivatives = df[df['expiry'].notnull()].copy()

    try:
        # 3. FETCH VALID PARENT KEYS using SQLAlchemy
        # We need to ensure we don't try to insert a derivative whose parent isn't in 'instruments'
        parent_query = text("SELECT instrument_key FROM instruments")
        with engine.connect() as conn:
            result = conn.execute(parent_query)
            valid_parent_keys = {row[0] for row in result.fetchall()}

        print(f"🔍 Validated {len(valid_parent_keys)} potential parent instruments in DB.")

        # 4. Filter and Prepare Data
        deriv_data = []
        for _, row in derivatives.iterrows():
            # Check if the derivative itself exists in our master instrument table
            if row['instrument_key'] not in valid_parent_keys:
                continue
                
            u_key = row['underlying_key']
            # Also validate the underlying_key if it exists
            if u_key and u_key not in valid_parent_keys:
                u_key = None
                
            deriv_data.append({
                'ik': row['instrument_key'],
                'uk': u_key,
                'ex': row.get('expiry_date'),
                'sp': row.get('strike_price'),
                'ot': row.get('option_type'),
                'ls': int(row['lot_size'])
            })

        # 5. EXECUTE TARGETED SYNC
        # ON CONFLICT ensures we don't create duplicates but update existing records
        deriv_query = text("""
            INSERT INTO instrument_derivatives (
                instrument_key, underlying_key, expiry_date, strike_price, option_type, lot_size
            ) VALUES (:ik, :uk, :ex, :sp, :ot, :ls)
            ON CONFLICT (instrument_key) DO UPDATE SET
                underlying_key = EXCLUDED.underlying_key,
                expiry_date = EXCLUDED.expiry_date,
                strike_price = EXCLUDED.strike_price,
                lot_size = EXCLUDED.lot_size;
        """)

        print(f"📦 Syncing {len(deriv_data)} Validated Derivative entries...")
        
        # Process in batches for performance and stability
        for i in range(0, len(deriv_data), BATCH_SIZE):
            batch = deriv_data[i : i + BATCH_SIZE]
            with engine.begin() as conn: # engine.begin handles the COMMIT automatically
                res = conn.execute(deriv_query, batch)
                deriv_inserted += res.rowcount
            print(f"   - Derivative Progress: {min(i + BATCH_SIZE, len(deriv_data))} processed...")
                
        print("\n" + "="*40)
        print(f"🎉 VALIDATED SYNC COMPLETE")
        print(f"   - Total Derivatives Synced: {deriv_inserted}")
        print("="*40)

    except Exception as e:
        print(f"❌ Critical error during derivative sync: {e}")
        # SQLAlchemy's engine.begin() automatically rolls back on failure

if __name__ == "__main__":
    sync_derivatives_only()