import os
import logging
from sqlalchemy import text
from dotenv import load_dotenv
from src.veridian_quant.data.db_client import DatabaseClient
from src.veridian_quant.core.signals.equity_scanner import EquityScanner

# Load configuration from .env
load_dotenv()

# Logger setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_live_portfolio_equity(engine):
    """
    Interface wrapper to determine active portfolio capital.
    Provides a seamless hook for database states or Broker API integrations.
    """
    # TODO: Future Implementation - Pull live cash margins directly via Upstox API:
    # return upstox_client.get_profile_balance()
    
    # Alternative: Pull the latest balance snapshot from your internal database tables
    try:
        # Example query structure to fetch from a broker tracking ledger:
        # query = text("SELECT current_balance FROM account_ledger ORDER BY timestamp DESC LIMIT 1;")
        # with engine.connect() as conn:
        #     balance = conn.execute(query).scalar()
        #     if balance and balance > 0:
        #         return float(balance)
        pass
    except Exception as e:
        logger.warning(f"Failed to query active ledger: {e}. Falling back to configuration defaults.")
    
    # Institutional baseline configuration fallback (₹10,00,000)
    return float(os.getenv("PRODUCTION_INITIAL_EQUITY", 10000000.0))

def run_scheduler():
    """
    Main entry point for daily scans. Fetches active NSE equities, 
    extracts active capital balances, and processes them through the 
    Stage 2.5 Risk-Equalized Sizing Alpha engine.
    """
    # 1. Configurable Scanner Values from .env
    SCAN_MODE = os.getenv("SCAN_MODE", "PROD") 
    SOURCE_TABLE = os.getenv("SCAN_SOURCE_TABLE", "ohlc_1d")
    
    # Initialize DB Client and retrieve the SQLAlchemy engine
    db = DatabaseClient() 
    engine = db.get_engine()

    try:
        # 2. Initialize Scanner with the Engine
        scanner = EquityScanner(engine, mode=SCAN_MODE, source_table=SOURCE_TABLE)
        
        # 3. Dynamic Capital Extraction Layer (Stage 2.5 Infrastructure)
        # live_equity = fetch_live_portfolio_equity(engine)
        # logger.info(f"💰 Active Capital Profile loaded: ₹{live_equity:,.2f}")

        # 4. Fetch instruments to scan using SQLAlchemy
        # We target NSE equity segments for the Stage 1 Z-Score strategy
        instrument_query = text("""
            SELECT instrument_key, trading_symbol 
            FROM instruments 
            WHERE exchange = 'NSE' AND segment = 'EQUITY';
        """)

        with engine.connect() as conn:
            instruments = conn.execute(instrument_query).fetchall()

        logger.info(f"🚀 Starting {SCAN_MODE} scan for {len(instruments)} symbols using {SOURCE_TABLE}")
        
        signals_found = 0
        for inst_key, symbol in instruments:
            try:
                # Core processing logic - Passing live capital snapshot down to calculation engine
                recommendation = scanner.scan_instrument(
                    instrument_key=inst_key, 
                    symbol=symbol
                )
                
                if recommendation:
                    scanner.save_recommendation(recommendation)
                    signals_found += 1
            except Exception as e:
                # Log error for specific instrument but continue the loop
                logger.error(f"Error scanning {symbol}: {e}")
                continue

        logger.info(f"✅ Scan Complete. New signals generated: {signals_found}")

    except Exception as e:
        logger.error(f"Critical error in scheduler: {e}")
    # No manual close required; SQLAlchemy engine manages the pool automatically

if __name__ == "__main__":
    run_scheduler()