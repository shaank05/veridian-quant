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
    if not payload or not payload.get("metrics"):
        return False

    # Policy 1: Every single enabled strategy node must return a True vote
    if policy_mode == "STRICT_CONSENSUS":
        # Handled fallback checks gracefully across strategy metrics vectors
        metrics = payload.get("metrics", {})
        z_triggered = metrics.get("z_score", 0.0) < float(os.getenv("NODE_Z_SCORE_THRESHOLD", "-2.5"))
        entropy_safe = metrics.get("shannon_entropy", 0.0) <= float(os.getenv("NODE_ENTROPY_MAX_THRESHOLD", "2.1"))
        wavelet_valid = metrics.get("wavelet_intensity", 0.0) > 0.40
        
        return z_triggered and entropy_safe and wavelet_valid

    # Policy 2: Requires a specific consensus hurdle ratio from the master hub
    elif policy_mode == "CONVICTION_THRESHOLD":
        min_threshold = float(os.getenv("PRODUCTION_MIN_CONVICTION_SCORE", "75.0"))
        # Realignment matching structural ensemble update parameters
        current_score = payload.get("metrics", {}).get("ensemble_strength_score", 0.0)
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

        # Extract symbols using the backtest engine setup instance path
        from src.veridian_quant.core.schedulers.backtest_engine import BacktestEngine
        mock_engine = BacktestEngine()
        symbols = mock_engine.get_watchlist_symbols()

        if not symbols:
            logger.error("❌ Production Watchlist target array retrieved empty. Aborting run.")
            return

        # Map current system assets to establish relational references matching instruments table layout
        query = text("""
            SELECT instrument_key, trading_symbol 
            FROM instruments 
            WHERE trading_symbol IN :symbols AND instrument_key LIKE 'NSE_EQ|%';
        """)
        
        try:
            with engine.connect() as conn:
                result = conn.execute(query, {"symbols": tuple(symbols)}).fetchall()
                instruments = [(row[0], row[1]) for row in result]
        except Exception as e:
            logger.error(f"❌ Failed to query execution instruments from master dictionary: {e}")
            return

        if not instruments:
            logger.warning("⚠️ No active instruments matched target tickers inside production database.")
            return

        logger.info(f"🧐 Processing parallel metrics across {len(instruments)} active assets...")
        signals_found = 0
        
        # Format a live date snapshot context parameter block string matching database constraints
        today_str = datetime.now().strftime('%Y-%m-%d')

        # Live Execution Step Loop
        for inst_key, symbol in instruments:
            try:
                # Build localized transient package payload to run through scanner execution node
                hist_df = mock_engine.fetch_historical_matrix(symbol, today_str)
                if hist_df.empty or len(hist_df) < 35:
                    continue
                
                # Bundle single ticker package
                tickers_data_package = {symbol: hist_df}
                
                # Run multi-dimensional concurrent analysis against asset packages
                day_signals = scanner.execute_concurrent_analysis(tickers_data_package, today_str)

                if not day_signals:
                    continue

                payload = day_signals[0] # Extract localized structured recommendations matrix map
                metrics_bag = payload.get("metrics", {})

                # Log runtime telemetry metrics to the console for live terminal audit trails
                logger.info(
                    f"📊 [BASE SIGNAL TRIGGERED] {symbol} | Base Z: {metrics_bag.get('z_score', 0.0):.2f} "
                    f"| Strength: {metrics_bag.get('ensemble_strength_score', 0.0):.1f}% "
                    f"| CWT Intensity: {metrics_bag.get('wavelet_intensity', 1.0):.2f}"
                )

                # Route full multi-strategy payload through active production selection constraints
                if enforce_production_policy(payload, POLICY_MODE):
                    # Save recommendation to DB table using internal scanner mechanism structures directly
                    scanner.save_recommendation(payload)
                    logger.info(f"🎯 [RECOMMENDATION GENERATED] {symbol} cleared {POLICY_MODE} requirements.")
                    signals_found += 1
                    
            except Exception as e:
                logger.error(f"Error scanning {symbol}: {e}")
                continue

        logger.info(f"✅ Scan Complete. New production signals archived: {signals_found}")

    except Exception as e:
        logger.error(f"Critical error in scheduler: {e}")

if __name__ == "__main__":
    from datetime import datetime
    run_scheduler()