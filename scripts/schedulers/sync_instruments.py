import os
import pandas as pd
import numpy as np
from sqlalchemy import text # Use SQLAlchemy text for raw SQL execution
from src.veridian_quant.data.providers.factory import get_active_provider
from src.veridian_quant.data.db_client import DatabaseClient

def sync_instruments():
    """
    Synchronizes the local instrument master and derivative tables with the 
    active data provider (e.g., Upstox).
    """
    db = DatabaseClient()
    engine = db.get_engine() # Use the SQLAlchemy engine
    BATCH_SIZE = 2000 
    
    try:
        market_mode = os.getenv("MARKET_MODE")
        if not market_mode:
            raise EnvironmentError("❌ 'MARKET_MODE' is not set in the .env file.")
        
        market_mode = market_mode.upper()
        provider = get_active_provider()
        
        print(f"📡 Fetching Master List | Provider: {provider.__class__.__name__}")
        df = provider.get_instrument_list()

        # --- ADD THESE DIAGNOSTIC PRINTS HERE ---
        # print("\n🔍 DEBUG: UPSTOX DATA RECEIVED")
        # print(f"   - Total Rows: {len(df)}")
        # print(f"   - Available Columns: {df.columns.tolist()}")
        # print(f"   - Sample Data (First 2 rows):\n{df.head(2).to_string()}")
        # print("-" * 40 + "\n")
        
        if df is None or df.empty:
            print("❌ Error: Received empty data from provider.")
            return

        if 'symbol' in df.columns:
            df['trading_symbol'] = df['symbol']

        # Ensure exchange_token and segment are strings
        df['exchange_token'] = df['exchange_token'].astype(str)
        df['segment'] = df['segment'].astype(str)
        
        # --- DATA CLEANING (BIGINT & NULL HANDLING) ---
        df['lot_size'] = pd.to_numeric(df['lot_size'], errors='coerce').fillna(1).astype(int)
        
        # Convert NaN to None so PostgreSQL/SQLAlchemy sees them as NULL
        df['underlying_key'] = df['underlying_key'].replace({np.nan: None})

        if market_mode == "INDIA":
            df['instrument_type'] = df['instrument_type'].str.upper()
            df['segment'] = df['segment'].str.upper()
            df['exchange'] = df['exchange'].str.upper()

            # 1. UPSERT INTO MASTER 'instruments' TABLE
            # We filter for relevant columns and use :named_parameters for SQLAlchemy
            master_query = text("""
                INSERT INTO instruments (instrument_key, exchange_token, symbol, trading_symbol, name, exchange, segment)
                VALUES (:instrument_key, :exchange_token, :symbol, :trading_symbol, :name, :exchange, :segment)
                ON CONFLICT (instrument_key) DO UPDATE SET
                    trading_symbol = EXCLUDED.trading_symbol,
                    name = EXCLUDED.name;
            """)

            master_data = df[['instrument_key', 'exchange_token', 'symbol', 'trading_symbol', 'name', 'exchange', 'segment']].to_dict(orient='records')

            print(f"📦 Syncing {len(master_data)} Master Instruments...")
            for i in range(0, len(master_data), BATCH_SIZE):
                batch = master_data[i : i + BATCH_SIZE]
                with engine.begin() as conn: # Handles commit automatically per batch
                    conn.execute(master_query, batch)
                print(f"   - Processed {min(i + BATCH_SIZE, len(master_data))} master records...")

            # 2. UPSERT INTO 'instrument_derivatives' TABLE
            # Filter for rows that actually have derivative attributes
            derivatives = df[df['expiry_date'].notnull()].copy()
            
            if not derivatives.empty:
                # IMPORTANT: Data Integrity Check
                # Derivatives must reference an existing instrument_key in the master table
                valid_keys = set(df['instrument_key'].unique())

                deriv_query = text("""
                    INSERT INTO instrument_derivatives (instrument_key, underlying_key, expiry_date, strike_price, option_type, lot_size)
                    VALUES (:instrument_key, :underlying_key, :expiry_date, :strike_price, :option_type, :lot_size)
                    ON CONFLICT (instrument_key) DO UPDATE SET
                        underlying_key = EXCLUDED.underlying_key,
                        expiry_date = EXCLUDED.expiry_date,
                        strike_price = EXCLUDED.strike_price,
                        option_type = EXCLUDED.option_type,
                        lot_size = EXCLUDED.lot_size;
                """)
                
                # Prepare derivative records list
                deriv_records = []
                for _, row in derivatives.iterrows():
                    u_key = row['underlying_key']
                    # Ensure underlying_key exists in our master list to prevent FK violations
                    if u_key and u_key not in valid_keys:
                        u_key = None
                        
                    deriv_records.append({
                        'instrument_key': row['instrument_key'],
                        'underlying_key': u_key, 
                        'expiry_date': row.get('expiry_date'),
                        'strike_price': row.get('strike_price'),
                        'option_type': row.get('instrument_type'), # Mapping type to option_type column
                        'lot_size': int(row['lot_size'])
                    })

                print(f"📦 Syncing {len(deriv_records)} Validated Derivatives...")
                for i in range(0, len(deriv_records), BATCH_SIZE):
                    batch = deriv_records[i : i + BATCH_SIZE]
                    with engine.begin() as conn:
                        conn.execute(deriv_query, batch)
                    print(f"   - Processed {min(i + BATCH_SIZE, len(deriv_records))} derivatives...")

            print("🎉 Full Market Sync Complete!")

    except Exception as e:
        print(f"❌ Sync failed: {e}")
        # Note: SQLAlchemy's engine.begin() context manager handles rollbacks automatically on error

if __name__ == "__main__":
    sync_instruments()