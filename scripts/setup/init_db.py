import logging
from sqlalchemy import text
from src.veridian_quant.data.db_client import DatabaseClient

# Logger setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def initialize_production_database():
    db = DatabaseClient()
    engine = db.get_engine()
    
    # 1. CORE TABLE DEFINITIONS
    tables_sql = [
        # Master Instruments
        """
        CREATE TABLE IF NOT EXISTS instruments (
            instrument_key TEXT PRIMARY KEY,
            exchange_token TEXT,
            exchange TEXT NOT NULL,
            symbol TEXT NOT NULL,
            trading_symbol TEXT,
            name TEXT,
            segment TEXT,
            instrument_type TEXT,
            lot_size BIGINT DEFAULT 1,
            last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        # Active Derivatives
        """
        CREATE TABLE IF NOT EXISTS instrument_derivatives (
            instrument_key TEXT PRIMARY KEY REFERENCES instruments(instrument_key) ON DELETE CASCADE,
            underlying_key TEXT REFERENCES instruments(instrument_key),
            expiry_date DATE NOT NULL,
            strike_price NUMERIC,
            option_type TEXT,
            lot_size BIGINT NOT NULL
        );
        """,
        # Expired Metadata Archive
        """
        CREATE TABLE IF NOT EXISTS instruments_expired_archive (
            instrument_key TEXT PRIMARY KEY,
            underlying_key TEXT,
            expiry_date DATE,
            strike_price NUMERIC,
            option_type TEXT,
            lot_size BIGINT,
            archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        # Live OHLC Price Table
        """
        CREATE TABLE IF NOT EXISTS prices_ohlc (
            timestamp TIMESTAMPTZ NOT NULL,
            instrument_key TEXT NOT NULL REFERENCES instruments(instrument_key) ON DELETE CASCADE,
            open NUMERIC,
            high NUMERIC,
            low NUMERIC,
            close NUMERIC,
            volume BIGINT,
            open_interest BIGINT,
            interval TEXT NOT NULL,
            PRIMARY KEY (timestamp, instrument_key, interval)
        );
        """,
        # Price Archive Table
        """
        CREATE TABLE IF NOT EXISTS prices_ohlc_archive (
            timestamp TIMESTAMPTZ NOT NULL,
            instrument_key TEXT NOT NULL,
            open NUMERIC,
            high NUMERIC,
            low NUMERIC,
            close NUMERIC,
            volume BIGINT,
            open_interest BIGINT,
            interval TEXT NOT NULL,
            archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        # Equity Recommendations Table
        """
        CREATE TABLE IF NOT EXISTS equity_recommendations (
            id SERIAL PRIMARY KEY,
            instrument_key TEXT NOT NULL REFERENCES instruments(instrument_key),
            trading_symbol TEXT NOT NULL,
            investment_type TEXT NOT NULL CHECK (investment_type IN ('SWING', 'SHORT_TERM', 'LONG_TERM')),
            strategies_involved TEXT[] NOT NULL, 
            generation_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            entry_price NUMERIC(12, 2) NOT NULL,
            target_1 NUMERIC(12, 2) NOT NULL,
            target_2 NUMERIC(12, 2),
            stop_loss NUMERIC(12, 2) NOT NULL,
            risk_reward_ratio NUMERIC(4, 2) GENERATED ALWAYS AS (
                ROUND((target_1 - entry_price) / NULLIF(entry_price - stop_loss, 0), 2)
            ) STORED,
            expected_duration_val INTEGER, 
            expected_duration_unit TEXT DEFAULT 'DAYS', 
            expiry_date TIMESTAMP WITH TIME ZONE,
            
            -- --- STAGE 2.5: MONEY MANAGEMENT & ATR RISK SIZING LAYERS ---
            account_equity_snapshot NUMERIC(12, 2),
            risk_budget_applied NUMERIC(12, 2),
            raw_atr_allocation NUMERIC(12, 2),
            is_allocation_clamped BOOLEAN DEFAULT FALSE,
            final_share_quantity INTEGER,
            final_capital_allocation NUMERIC(12, 2),
            
            -- --- OMS & STATE MACHINE PLUMBING ---
            is_ordered BOOLEAN DEFAULT FALSE,
            external_order_id TEXT,
            execution_timestamp TIMESTAMP WITH TIME ZONE,
            status TEXT DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'ACTIVE', 'TARGET_HIT', 'STOP_LOSS_HIT', 'EXPIRED', 'CANCELLED')),
            actual_exit_price NUMERIC(12, 2),
            exit_date TIMESTAMP WITH TIME ZONE,
            pnl_percentage NUMERIC(6, 2),
            max_drawdown_seen NUMERIC(6, 2), 
            is_manual_entry BOOLEAN DEFAULT FALSE,
            notes TEXT
        );
        """,
        # Marktet Indicators Table
        """
        CREATE TABLE IF NOT EXISTS market_indicators (
            timestamp TIMESTAMPTZ NOT NULL,
            indicator_name TEXT NOT NULL, -- e.g., 'INDIA_VIX', 'NIFTY_PCR', 'DXY', 'FII_CASH'
            open NUMERIC,
            high NUMERIC,
            low NUMERIC,
            close NUMERIC,
            value NUMERIC,  -- For non-OHLC data (PCR, PE, etc.)
            interval TEXT NOT NULL,
            metadata JSONB,      -- For source context or extra data points
            PRIMARY KEY (timestamp, indicator_name, interval)
        );
        """
    ]

    # 2. TIMESCALEDB HYPERTABLES
    timescale_sql = [
        "SELECT create_hypertable('prices_ohlc', 'timestamp', if_not_exists => TRUE);",
        "SELECT create_hypertable('prices_ohlc_archive', 'timestamp', if_not_exists => TRUE);"
        "SELECT create_hypertable('market_indicators', 'timestamp', if_not_exists => TRUE);"
    ]

    # 3. INDEXES
    index_sql = [
        "CREATE INDEX IF NOT EXISTS idx_ohlc_query ON prices_ohlc (instrument_key, interval, timestamp DESC);",
        "CREATE INDEX IF NOT EXISTS idx_archive_query ON prices_ohlc_archive (instrument_key, timestamp DESC);",
        "CREATE INDEX IF NOT EXISTS idx_reco_status ON equity_recommendations (status, is_ordered);",
        "CREATE INDEX IF NOT EXISTS idx_indicator_time ON market_indicators (indicator_name, timestamp DESC)"
    ]

    # 4. CONTINUOUS AGGREGATES (Restored all 6 timeframes)
    view_sql = [
        "CREATE MATERIALIZED VIEW IF NOT EXISTS ohlc_5m  WITH (timescaledb.continuous) AS SELECT time_bucket('5 minutes', timestamp) AS bucket, instrument_key, first(open, timestamp) as open, max(high) as high, min(low) as low, last(close, timestamp) as close, sum(volume) as volume, last(open_interest, timestamp) as open_interest FROM prices_ohlc WHERE interval = '1minute' GROUP BY bucket, instrument_key;",
        "CREATE MATERIALIZED VIEW IF NOT EXISTS ohlc_15m WITH (timescaledb.continuous) AS SELECT time_bucket('15 minutes', timestamp) AS bucket, instrument_key, first(open, timestamp) as open, max(high) as high, min(low) as low, last(close, timestamp) as close, sum(volume) as volume, last(open_interest, timestamp) as open_interest FROM prices_ohlc WHERE interval = '1minute' GROUP BY bucket, instrument_key;",
        "CREATE MATERIALIZED VIEW IF NOT EXISTS ohlc_1h  WITH (timescaledb.continuous) AS SELECT time_bucket('1 hour', timestamp) AS bucket, instrument_key, first(open, timestamp) as open, max(high) as high, min(low) as low, last(close, timestamp) as close, sum(volume) as volume, last(open_interest, timestamp) as open_interest FROM prices_ohlc WHERE interval = '1minute' GROUP BY bucket, instrument_key;",
        "CREATE MATERIALIZED VIEW IF NOT EXISTS ohlc_1d  WITH (timescaledb.continuous) AS SELECT time_bucket('1 day', timestamp) AS bucket, instrument_key, first(open, timestamp) as open, max(high) as high, min(low) as low, last(close, timestamp) as close, sum(volume) as volume, last(open_interest, timestamp) as open_interest FROM prices_ohlc WHERE interval = '1minute' GROUP BY bucket, instrument_key;",
        "CREATE MATERIALIZED VIEW IF NOT EXISTS ohlc_1w  WITH (timescaledb.continuous) AS SELECT time_bucket('1 week', timestamp) AS bucket, instrument_key, first(open, timestamp) as open, max(high) as high, min(low) as low, last(close, timestamp) as close, sum(volume) as volume, last(open_interest, timestamp) as open_interest FROM prices_ohlc WHERE interval = '1minute' GROUP BY bucket, instrument_key;",
        "CREATE MATERIALIZED VIEW IF NOT EXISTS ohlc_1M WITH (timescaledb.continuous) AS SELECT time_bucket('1 month', timestamp, TIMESTAMPTZ '2000-01-01') AS bucket, instrument_key, first(open, timestamp) as open, max(high) as high, min(low) as low, last(close, timestamp) as close, sum(volume) as volume, last(open_interest, timestamp) as open_interest FROM prices_ohlc WHERE interval = '1minute' GROUP BY bucket, instrument_key;"
    ]

    # 5. REFRESH POLICIES
    policy_sql = [
        "SELECT add_continuous_aggregate_policy('ohlc_5m',  start_offset => INTERVAL '3 days', end_offset => INTERVAL '1 minute', schedule_interval => INTERVAL '5 minutes', if_not_exists => TRUE);",
        "SELECT add_continuous_aggregate_policy('ohlc_15m', start_offset => INTERVAL '3 days', end_offset => INTERVAL '1 minute', schedule_interval => INTERVAL '15 minutes', if_not_exists => TRUE);",
        "SELECT add_continuous_aggregate_policy('ohlc_1h',  start_offset => INTERVAL '7 days', end_offset => INTERVAL '1 minute', schedule_interval => INTERVAL '1 hour', if_not_exists => TRUE);",
        "SELECT add_continuous_aggregate_policy('ohlc_1d',  start_offset => NULL, end_offset => INTERVAL '1 hour', schedule_interval => INTERVAL '1 day', if_not_exists => TRUE);",
        "SELECT add_continuous_aggregate_policy('ohlc_1w',  start_offset => NULL, end_offset => INTERVAL '1 hour', schedule_interval => INTERVAL '1 day', if_not_exists => TRUE);",
        "SELECT add_continuous_aggregate_policy('ohlc_1M', start_offset => INTERVAL '1 year', end_offset => INTERVAL '1 hour', schedule_interval => INTERVAL '1 day', if_not_exists => TRUE);"
    ]

    try:
        # AUTOCOMMIT for TimescaleDB administration
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            logger.info("🛠️ Applying FINALIZED Comprehensive Database Schema...")
            
            for section, queries in [
                ("Tables", tables_sql),
                ("Hypertables", timescale_sql),
                ("Indexes", index_sql),
                ("Views", view_sql),
                ("Policies", policy_sql)
            ]:
                logger.info(f"Syncing {section}...")
                for sql in queries:
                    if "MATERIALIZED VIEW" in sql and "WITH NO DATA" not in sql:
                        sql = sql.strip().rstrip(';') + " WITH NO DATA;"
                    conn.execute(text(sql))
            
            logger.info("✅ Database schema is complete and future-ready.")
            
    except Exception as e:
        logger.error(f"❌ Initialization failed: {e}")

if __name__ == "__main__":
    initialize_production_database()