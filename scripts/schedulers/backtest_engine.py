import pandas as pd
import os
import json
import time  
from sqlalchemy import text
from dotenv import load_dotenv
from src.veridian_quant.data.db_client import DatabaseClient
from src.veridian_quant.core.signals.equity_scanner import EquityScanner
from datetime import datetime

# Initialize the environment wrapper configuration parameters
load_dotenv()

class BacktestEngine:
    """
    Chronological Ledger Loop Engine.
    
    Responsible for executing multi-year business day backtests over pristine historical 
    market datasets. This module acts strictly as an execution logging layout; it carries 
    no statistical math or indicator filtering. It loops chronologically, routes dates 
    directly down to EquityScanner, and converts the multi-strategy nested telemetry payloads 
    into a flat, multi-dimensional analytical matrix CSV for deep statistical auditing.
    """
    def __init__(self):
        # Establish persistence framework connection instance
        self.db = DatabaseClient()
        
        # Instantiate the unified quantitative calculation hub.
        # Mode is passed explicitly as 'BACKTEST' to force the engine to bypass live execution constraints
        # and gather parallel strategy voting records.
        self.scanner = EquityScanner(self.db.get_engine(), mode='BACKTEST', source_table='prices_ohlc')

    def get_watchlist_symbols(self):
        """
        Loads configured universe ticker targets from root > config > watchlist.json.
        Combines target lists into a single consolidated execution tracking array.
        """
        current_dir = os.path.dirname(os.path.abspath(__file__))
        watchlist_path = os.path.join(current_dir, '..', '..', 'config', 'watchlist.json')
        watchlist_path = os.path.normpath(watchlist_path)

        try:
            if not os.path.exists(watchlist_path):
                print(f"❌ File not found at: {watchlist_path}")
                return []

            with open(watchlist_path, 'r') as f:
                data = json.load(f)
                symbols = data.get('one_minute_targets', []) + data.get('one_day_targets', [])
                print(f"✅ Loaded {len(symbols)} symbols from watchlist.")
                return symbols
        except Exception as e:
            print(f"❌ Error loading watchlist: {e}")
            return []

    def verify_outcome(self, inst_key, signal_date, target, stop_loss):
        """
        Chronological Window Audit Track.
        
        Evaluates a 30-day forward price matrix following a signal timestamp to find out 
        whether the profit target boundary or risk stop-loss limit was crossed first.
        """
        query = text("""
            SELECT timestamp, high, low FROM prices_ohlc 
            WHERE instrument_key = :inst_key AND interval = 'day' AND timestamp > :signal_date
            ORDER BY timestamp ASC LIMIT 30;
        """)
        try:
            df = pd.read_sql(query, self.db.get_engine(), params={
                "inst_key": inst_key, 
                "signal_date": signal_date
            })
            
            if df.empty: return "NO_FUTURE_DATA", None, None

            # Loop through future data ticks day-by-day to verify trade exit resolution
            for idx, row in df.iterrows():
                if row['high'] >= target: return "HIT_TARGET", row['timestamp'], idx + 1
                if row['low'] <= stop_loss: return "HIT_STOP_LOSS", row['timestamp'], idx + 1
            return "EXPIRED", None, 30
        except Exception as e:
            print(f"Error verifying outcome: {e}")
            return "ERROR", None, None

    def run(self, start_date, end_date):
        """
        Main Engine Execution Loop.
        
        Advances capital balances over sequential business days, unpacking nested, 
        parallel strategy matrices dynamically to construct a multi-variant backtest ledger.
        """
        # Start performance profile tracking timers
        start_perf_time = time.perf_counter()
        start_time_ist = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")

        # Fixed-unit capital allocation benchmark parameters (₹1,00,000 per asset)
        INITIAL_BACKTEST_EQUITY = 100000.0
        current_balance = INITIAL_BACKTEST_EQUITY
        
        symbols = self.get_watchlist_symbols()
        if not symbols:
            print("Watchlist is empty. Exiting.")
            return

        query = "SELECT instrument_key, symbol FROM instruments WHERE symbol IN :symbols AND (instrument_key LIKE 'NSE_EQ|%' OR instrument_key LIKE 'NSE_INDEX|%');"

        try:
            instruments = self.db.execute_query(query, {"symbols": tuple(symbols)})
        except Exception as e:
            print(f"❌ Error fetching instruments: {e}")
            return

        if not instruments:
            print("No matching instruments found in DB.")
            return

        print(f"🧐 Scanning {len(instruments)} instruments from {start_date} to {end_date}...")
        print("⛓️ Parallel Strategy Registry Matrix Engaged. Extracting all metrics simultaneously.")

        # Construct chronological index across business day frequencies
        test_days = pd.date_range(start=start_date, end=end_date, freq='B')
        results = []

        # Chronological Engine Loop (The System Clock)
        for current_day in test_days:
            for inst_key, symbol in instruments:
                
                # Fetch full structural telemetry matrix payload from the unified scanner framework
                payload = self.scanner.scan_instrument(inst_key, symbol, as_of_date=current_day)
                
                # In Backtest mode, we check only if the base statistical entry setup was reached.
                # All other signal nodes are tracked and logged simultaneously without dropping rows.
                if payload and payload.get("core_setup_triggered"):
                    
                    # Track future timeline resolution using boundaries computed natively by the scanner
                    outcome, hit_date, days_taken = self.verify_outcome(
                        inst_key, current_day, payload['target_price'], payload['stop_loss_price']
                    )
                    
                    entry_price = payload['entry_price']
                    
                    # Calculate position size constraints based on static rupee limits
                    qty = int(INITIAL_BACKTEST_EQUITY // entry_price)
                    if qty <= 0:
                        continue

                    # Determine exact exit execution benchmark pricing structures
                    if outcome == "HIT_TARGET":
                        exit_price = payload['target_price']
                    elif outcome == "HIT_STOP_LOSS":
                        exit_price = payload['stop_loss_price']
                    else:
                        exit_price = entry_price  # Expired horizon fallback
                    
                    # Compute financial adjustments
                    pnl_amount = qty * (exit_price - entry_price)
                    pnl_pct = ((exit_price - entry_price) / entry_price) * 100
                    current_balance += pnl_amount
                    
                    # Create the base flat transaction log row
                    trade_row = {
                        'signal_date': current_day.date(),
                        'symbol': symbol,
                        'entry_price': round(entry_price, 2),
                        'target_price': round(payload['target_price'], 2),
                        'stop_loss_price': round(payload['stop_loss_price'], 2),
                        'exit_price': round(exit_price, 2),
                        'pnl_amount': round(pnl_amount, 2),
                        'pnl_percentage': round(pnl_pct, 2),
                        'cumulative_balance': round(current_balance, 2),
                        'outcome': outcome,
                        'market_regime': payload['market_regime'],
                        'exit_date_daily': hit_date.date() if hasattr(hit_date, 'date') and hit_date else hit_date,
                        'days_to_result': days_taken,
                        'shares_traded': qty
                    }
                    
                    # DYNAMIC TELEMETRY UNPACKING MATRIX
                    # Unpacks nested 'metrics' dictionaries (e.g., z_score, shannon_entropy, vix_value) 
                    # into top-level columns automatically to eliminate rigid code dependencies.
                    for metric_key, metric_value in payload.get("metrics", {}).items():
                        trade_row[metric_key] = round(metric_value, 4) if isinstance(metric_value, float) else metric_value
                        
                    # Unpacks individual strategy boolean 'votes' into clean 1 or 0 binary indicators 
                    # to enable multi-variable spreadsheet optimization passes.
                    for vote_key, vote_status in payload.get("votes", {}).items():
                        trade_row[f"{vote_key}_vote"] = 1 if vote_status else 0
                    
                    results.append(trade_row)
                    
                    # Enhanced Terminal Diagnostic Logging supporting Stage 2.2 metrics validation tracking
                    print(f"🎯 [{current_day.date()}] {symbol}: {outcome} | PnL: ₹{pnl_amount:,.2f} | Conviction: {payload.get('metrics', {}).get('ensemble_conviction_score', 0.0)}% | CWT Intensity: {payload.get('metrics', {}).get('wavelet_intensity', 1.0):.2f}")

        # Output persistence processing
        if results:
            report = pd.DataFrame(results)
            filename = f"backtest_report_{start_date.replace('-','')}.csv"
            report.to_csv(filename, index=False)
            print(f"\n📊 Multi-Dimensional Matrix Report saved: {os.getcwd()}/{filename}")
            print(f"💰 Final Yield Position Balance: ₹{current_balance:,.2f}")
        else:
            print("No signals found. Check tracking parameters or universe dataset depth.")

        # Complete runtime execution diagnostics reporting profile
        end_perf_time = time.perf_counter()
        end_time_ist = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        total_execution_time = end_perf_time - start_perf_time

        hours = int(total_execution_time // 3600)
        minutes = int((total_execution_time % 3600) // 60)
        seconds = total_execution_time % 60
        
        print("\n" + "="*50)
        print(f"🛫 Backtest Pass Started (IST) : {start_time_ist}")
        print(f"🛬 Backtest Pass Ended (IST)   : {end_time_ist}")
        print(f"⏱️ Matrix Run Ingestion Time   : {hours} hrs, {minutes} mins, {seconds:.2f} secs")
        print("="*50 + "\n")

if __name__ == "__main__":
    engine = BacktestEngine()
    engine.run("2020-01-01", "2026-04-30")