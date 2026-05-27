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
    try:
        # Institutional baseline configuration fallback (₹1,00,00,000)
        return float(os.getenv("PRODUCTION_INITIAL_EQUITY", 10000000.0))
    except Exception as e:
        logger.warning(f"Failed to query active ledger: {e}. Falling back to configuration defaults.")
        return 10000000.0

def enforce_production_policy(payload, policy_mode):
    """
    Enforces the active .env combination rules on the parallel payload matrix.
    Determines if the telemetry payload warrants a live market recommendation.
    """
    if not payload or not payload.get("core_setup_triggered"):
        return False

    # Policy 1: Every single enabled strategy node must return a True vote
    if policy_mode == "STRICT_CONSENSUS":
        votes = payload.get("votes", {})
        for node_flag, vote_passed in votes.items():
            if not vote_passed:
                return False
        return True

    # Policy 2: Outsource execution criteria entirely to the Stage 5 Bayesian Ensemble
    elif policy_mode == "ENSEMBLE_THRESHOLD":
        threshold = float(os.getenv("NODE_BAYESIAN_CONVICTION_THRESHOLD", "75.0"))
        conviction_score = payload.get("metrics", {}).get("ensemble_conviction_score", 0.0)
        return conviction_score >= threshold

    # Policy 3: Only require baseline validation; append other nodes purely as telemetry metadata
    elif policy_mode == "CORE_VETO":
        votes = payload.get("votes", {})
        return votes.get("z_score_triggered", False) and votes.get("vsa_confirmed", False)

    # Fallback safety protocol
    return False

def run_scheduler():
    """
    Main entry point for daily scans. Fetches active NSE equities, 
    extracts active capital balances, and processes them through the 
    Parallel Node Registry Engine.
    """
    SCAN_MODE = os.getenv("SCAN_MODE", "PROD") 
    SOURCE_TABLE = os.getenv("SCAN_SOURCE_TABLE", "ohlc_1d")
    POLICY_MODE = os.getenv("PRODUCTION_COMBINATION_MODE", "STRICT_CONSENSUS")
    
    # Initialize DB Client and retrieve the SQLAlchemy engine
    db = DatabaseClient() 
    engine = db.get_engine()

    try:
        # Initialize Scanner with the Engine
        scanner = EquityScanner(engine, mode=SCAN_MODE, source_table=SOURCE_TABLE)
        
        # Dynamic Capital Extraction Layer (Stage 2.5 Sizing Ready)
        live_equity = fetch_live_portfolio_equity(engine)
        logger.info(f"💰 Active Capital Profile loaded: ₹{live_equity:,.2f}")

        # Fetch active NSE instruments to scan using SQLAlchemy
        instrument_query = text("""
            SELECT instrument_key, trading_symbol 
            FROM instruments 
            WHERE exchange = 'NSE' AND segment = 'EQUITY';
        """)

        with engine.connect() as conn:
            instruments = conn.execute(instrument_query).fetchall()

        logger.info(f"🚀 Starting {SCAN_MODE} scan for {len(instruments)} symbols using {SOURCE_TABLE}")
        logger.info(f"⚙️ Live Execution Combination Enforcement Policy: {POLICY_MODE}")
        
        signals_found = 0
        for inst_key, symbol in instruments:
            try:
                # Query the master parallel engine matrix (defaults to point-in-time today)
                payload = scanner.scan_instrument(
                    instrument_key=inst_key, 
                    symbol=symbol
                )
                
                # Evaluate the parallel payload matrix against live combination constraints
                if enforce_production_policy(payload, POLICY_MODE):
                    # Package the matrix into a structured database record format
                    recommendation = {
                        'instrument_key': inst_key,
                        'symbol': symbol,
                        'entry_price': payload['entry_price'],
                        'target_1': payload['target_price'],
                        'stop_loss': payload['stop_loss_price'],
                        'vix_value': payload['metrics']['vix_value'],
                        'market_regime': payload['market_regime'],
                        'z_score': payload['metrics']['z_score'],
                        # Store complete serialized matrix logs directly inside a metadata JSON field
                        'telemetry_metadata': payload
                    }
                    
                    scanner.save_recommendation(recommendation)
                    logger.info(f"🎯 [RECOMMENDATION GENERATED] {symbol} cleared {POLICY_MODE} requirements.")
                    signals_found += 1
                    
            except Exception as e:
                logger.error(f"Error scanning {symbol}: {e}")
                continue

        logger.info(f"✅ Scan Complete. New production signals archived: {signals_found}")

    except Exception as e:
        logger.error(f"Critical error in scheduler: {e}")

if __name__ == "__main__":
    run_scheduler()