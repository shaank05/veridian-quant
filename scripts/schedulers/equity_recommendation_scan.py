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
        # Institutional baseline configuration fallback (₹1,0,00,000)
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
        # Added 'cwt_spectrum_vote' to the strict consensus validation suite for Stage 2.2 parity
        required_nodes = [
            "shannon_entropy_vote", 
            "fft_cycle_turning_vote", 
            "vsa_confirmed_vote", 
            "markov_vote",
            "cwt_spectrum_vote"
        ]
        return all(votes.get(node, False) for node in required_nodes)

    # Policy 2: Requires a specific consensus hurdle ratio from the master hub
    elif policy_mode == "CONVICTION_THRESHOLD":
        min_threshold = float(os.getenv("PRODUCTION_MIN_CONVICTION_SCORE", "75.0"))
        current_score = payload.get("metrics", {}).get("ensemble_conviction_score", 0.0)
        return current_score >= min_threshold

    # Fallback default: Permit raw core signals to bypass checks for testing
    return True

def run_scheduler():
    """
    Live Production Multi-Strategy Scan Orchestrator.
    
    Pulls live universe ticker components, triggers concurrent matrix evaluations,
    applies active policy constraints, and routes alerts directly to production tables.
    """
    logger.info("🚀 Commencing Production Parallel Strategic Telemetry Scan Pass...")
    
    try:
        # Initialize storage layer abstractions
        db = DatabaseClient()
        engine = db.get_engine()
        
        # Instantiate the scanner in production mode to process live data streams
        scanner = EquityScanner(engine, mode='PROD', source_table='prices_ohlc')
        
        # Pull down runtime execution rules from environment configs
        POLICY_MODE = os.getenv("PRODUCTION_POLICY_MODE", "CONVICTION_THRESHOLD")
        logger.info(f"📋 Enforcing Production Policy Matrix Layer Configuration: {POLICY_MODE}")

        # Extract symbols using the offline backtest setup configuration instance
        from src.veridian_quant.core.schedulers.backtest_engine import BacktestEngine
        mock_engine = BacktestEngine()
        symbols = mock_engine.get_watchlist_symbols()

        if not symbols:
            logger.error("❌ Production Watchlist target array retrieved empty. Aborting run.")
            return

        # Map current system assets to establish relational references
        query = "SELECT instrument_key, symbol FROM instruments WHERE symbol IN :symbols AND instrument_key LIKE 'NSE_EQ|%';"
        try:
            instruments = db.execute_query(query, {"symbols": tuple(symbols)})
        except Exception as e:
            logger.error(f"❌ Failed to query execution instruments from master dictionary: {e}")
            return

        if not instruments:
            logger.warning("⚠️ No active instruments matched target tickers inside production database.")
            return

        logger.info(f"🧐 Processing parallel metrics across {len(instruments)} active assets...")
        signals_found = 0

        # Live Execution Step Loop
        for inst_key, symbol in instruments:
            try:
                # Check for duplication to prevent flooding active operational databases
                if scanner.is_already_recommended(symbol):
                    continue

                # Run multi-dimensional concurrent analysis against real-time market data
                payload = scanner.scan_instrument(inst_key, symbol)

                if not payload:
                    continue

                # Log runtime telemetry metrics to the console for live terminal audit trails
                if payload.get("core_setup_triggered"):
                    # Enhanced live diagnostics tracking supporting real-time Wavelet Intensity checks
                    logger.info(
                        f"📊 [BASE SIGNAL TRIGGERED] {symbol} | Base Z: {payload['metrics']['z_score']:.2f} "
                        f"| Conviction: {payload['metrics']['ensemble_conviction_score']}% "
                        f"| CWT Intensity: {payload['metrics']['wavelet_intensity']:.2f}"
                    )

                # Route full multi-strategy payload through active production selection constraints
                if enforce_production_policy(payload, POLICY_MODE):
                    # Package the matrix into a structured database record format
                    recommendation = {
                        'instrument_key': inst_key,
                        'symbol': symbol,
                        'entry_price': payload['entry_price'],
                        'target_price': payload['target_price'],    # Key name mapped directly to internal scanner expectations
                        'stop_loss_price': payload['stop_loss_price'],
                        'vix_value': payload['metrics']['vix_value'],
                        'market_regime': payload['market_regime'],
                        'z_score': payload['metrics']['z_score'],
                        'expected_duration_days': payload['expected_duration_days'],
                        'metrics': payload['metrics'],              # Propagate nested structures safely down to scanner.save
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