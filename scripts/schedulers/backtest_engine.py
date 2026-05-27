import pandas as pd
import os
import json
import time  # Added to calculate total execution time of the script in the console
from sqlalchemy import text
from dotenv import load_dotenv
from src.veridian_quant.data.db_client import DatabaseClient
from src.veridian_quant.core.signals.equity_scanner import EquityScanner
from src.veridian_quant.core.analytics.markov_analysis import calculate_transition_matrix
from src.veridian_quant.core.analytics.vectorized_math import calculate_shannon_entropy
from datetime import datetime
# import timezonefinder # Or simply use datetime with fixed offsets to stay lightweight

load_dotenv()

class BacktestEngine:
    def __init__(self):
        self.db = DatabaseClient()
        # Ensure source_table matches your DB: 'prices_ohlc'
        # Mode is explicitly passed as 'BACKTEST' to isolate it cleanly from 'PROD' scanner executions
        self.scanner = EquityScanner(self.db.get_engine(), mode='BACKTEST', source_table='prices_ohlc')
        
        # Parse new environment configuration toggles for the Markov engine structure
        self.markov_enabled = os.getenv("MARKOV_FILTER_ENABLED", "false").lower() == "true"
        self.markov_lookback = int(os.getenv("MARKOV_LOOKBACK_DAYS", "90"))
        # Swapped from min probability hurdle to an anti-cascade maximum persistence ceiling threshold
        self.markov_max_persistence = float(os.getenv("MARKOV_MAX_PERSISTENCE_THRESHOLD", "0.60"))

        # Parse environment configurations for Stage 2.1 Shannon Entropy Noise Shield Gate
        self.entropy_enabled = os.getenv("ENTROPY_FILTER_ENABLED", "false").lower() == "true"
        self.entropy_lookback = int(os.getenv("ENTROPY_LOOKBACK_DAYS", "20"))
        self.entropy_max_threshold = float(os.getenv("ENTROPY_MAX_THRESHOLD", "0.75"))

    def get_watchlist_symbols(self):
        """Loads symbols from root > config > watchlist.json"""
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
        """Checks future data to see if Target or SL was hit first."""
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

            for idx, row in df.iterrows():
                if row['high'] >= target: return "HIT_TARGET", row['timestamp'], idx + 1
                if row['low'] <= stop_loss: return "HIT_STOP_LOSS", row['timestamp'], idx + 1
            return "EXPIRED", None, 30
        except Exception as e:
            print(f"Error verifying outcome: {e}")
            return "ERROR", None, None

    def get_historical_z_scores(self, inst_key, end_date):
        """
        Fetches point-in-time historical Z-scores for an instrument up to the signal date.
        This provides the lookback slice needed to build the Markov transition matrix.
        """
        query = text("""
            SELECT timestamp, close FROM prices_ohlc 
            WHERE instrument_key = :inst_key AND interval = 'day' AND timestamp <= :end_date
            ORDER BY timestamp DESC LIMIT :lookback_limit;
        """)
        try:
            df = pd.read_sql(query, self.db.get_engine(), params={
                "inst_key": inst_key,
                "end_date": end_date,
                "lookback_limit": self.markov_lookback + 20  # Fetch slightly extra rows to guarantee clean Z calculations
            })
            if df.empty or len(df) < self.markov_lookback:
                return pd.Series(dtype='float64')
                
            # Reverse dataframe order so it reads sequentially in standard chronological order
            df = df.iloc[::-1].reset_index(drop=True)
            
            # Compute point-in-time rolling parameters matching historical state windows
            rolling_mean = df['close'].rolling(window=20).mean()
            rolling_std = df['close'].rolling(window=20).std()
            z_scores = (df['close'] - rolling_mean) / rolling_std
            
            # Extract and return precisely the final window length slice
            return z_scores.tail(self.markov_lookback).reset_index(drop=True)
        except Exception as e:
            print(f"❌ Error fetching historical Z-scores for Markov calculation: {e}")
            return pd.Series(dtype='float64')

    def get_historical_prices_for_entropy(self, inst_key, end_date):
        """
        Fetches point-in-time historical closing prices up to the current backtest date 
        to guarantee calculation safety for the Shannon Entropy gate.
        """
        query = text("""
            SELECT timestamp, close FROM prices_ohlc 
            WHERE instrument_key = :inst_key AND interval = 'day' AND timestamp <= :end_date
            ORDER BY timestamp DESC LIMIT :lookback_limit;
        """)
        try:
            df = pd.read_sql(query, self.db.get_engine(), params={
                "inst_key": inst_key,
                "end_date": end_date,
                "lookback_limit": self.entropy_lookback + 5
            })
            if df.empty or len(df) < self.entropy_lookback:
                return pd.Series(dtype='float64')
            return df.iloc[::-1]['close'].reset_index(drop=True)
        except Exception as e:
            print(f"❌ Error fetching historical prices for Entropy calculation: {e}")
            return pd.Series(dtype='float64')

    def run(self, start_date, end_date):
        """
        Executes the backtest evaluating the absolute net yield of a fixed 
        ₹1,00,000 allocation layout per recommendation.
        """
        # Start performance profile timer
        start_perf_time = time.perf_counter()
        start_time_ist = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")

        # Reverted back to a baseline allocation unit tracking baseline
        INITIAL_BACKTEST_EQUITY = 100000.0
        current_balance = INITIAL_BACKTEST_EQUITY
        
        symbols = self.get_watchlist_symbols()
        if not symbols:
            print("Watchlist is empty. Exiting.")
            return

        query = "SELECT instrument_key, symbol FROM instruments WHERE symbol IN :symbols AND (instrument_key LIKE 'NSE_EQ|%' OR instrument_key LIKE 'NSE_INDEX|%');"
        
        # query = text("""SELECT instrument_key, symbol FROM instruments WHERE symbol = ANY(:symbols) AND (instrument_key LIKE 'NSE_EQ|%' OR instrument_key LIKE 'NSE_INDEX|%')""")

        try:
            instruments = self.db.execute_query(query, {"symbols": tuple(symbols)})
        except Exception as e:
            print(f"❌ Error fetching instruments: {e}")
            return

        if not instruments:
            print("No matching instruments found in DB.")
            return

        print(f"🧐 Scanning {len(instruments)} instruments from {start_date} to {end_date}...")
        
        if self.entropy_enabled:
            print(f"🛑 Shannon Entropy Noise Shield Engaged: Window={self.entropy_lookback} Days, Max Chaos Threshold={self.entropy_max_threshold}")
        else:
            print("⚠️ Shannon Entropy Filter Disabled.")

        if self.markov_enabled:
            print(f"⛓️ Markov Anti-Cascade Filter Engaged: Window={self.markov_lookback} Days, Max Persistence Ceiling={self.markov_max_persistence * 100}%")
        else:
            print("⚠️ Markov Filter Disabled: Running baseline metrics configuration.")

        test_days = pd.date_range(start=start_date, end=end_date, freq='B')
        results = []

        for current_day in test_days:
            for inst_key, symbol in instruments:
                # Pure point-in-time signal scanning
                signal = self.scanner.scan_instrument(inst_key, symbol, as_of_date=current_day)
                
                if signal:
                    # --- CONFIGURATION-BASED SHANNON ENTROPY GATE-CHECK FILTER ---
                    if self.entropy_enabled:
                        historical_prices = self.get_historical_prices_for_entropy(inst_key, current_day)
                        if not historical_prices.empty and len(historical_prices) >= self.entropy_lookback:
                            current_entropy = calculate_shannon_entropy(historical_prices, window=self.entropy_lookback)
                            if current_entropy > self.entropy_max_threshold:
                                # Suppress backtest signal generation if dataset exhibits structural noise chaos
                                continue

                    # --- CONFIGURATION-BASED MARKOV GATE-CHECK FILTER ---
                    if self.markov_enabled:
                        # Extract the exact historical point-in-time sequence preceding this setup trigger
                        historical_z = self.get_historical_z_scores(inst_key, current_day)
                        
                        # Generate the row-normalized 3x3 regime matrix
                        transition_matrix = calculate_transition_matrix(historical_z)
                        
                        # Extract entry probability parameter measuring State 0 (Crater) persistence stability
                        p_crater_persistence = transition_matrix[0][0]
                        
                        # Suppress trade generation if stock has a high probability of cascading down further inside State 0
                        if p_crater_persistence > self.markov_max_persistence:
                            # print(f"🛡️ [Blocked by Markov Anti-Cascade] {symbol} at {current_day.date()} | P(0->0): {p_crater_persistence:.2f} > {self.markov_max_persistence}")
                            continue

                    outcome, hit_date, days_taken = self.verify_outcome(
                        inst_key, current_day, signal['target_1'], signal['stop_loss']
                    )
                    
                    # --- PnL CALCULATION ENGINE ---
                    entry_price = signal['entry_price']
                    
                    # Calculate exact quantity based on fixed 1 Lakh allocation per recommendation
                    qty = int(INITIAL_BACKTEST_EQUITY // entry_price)
                    
                    if qty <= 0:
                        continue

                    # Map outcome targets directly to exit price benchmarks
                    if outcome == "HIT_TARGET":
                        exit_price = signal['target_1']
                    elif outcome == "HIT_STOP_LOSS":
                        exit_price = signal['stop_loss']
                    else:
                        exit_price = entry_price  # Fallback metric for EXPIRED or ERROR states
                    
                    # Compute monetary PnL yield generated by this trade setup
                    pnl_amount = qty * (exit_price - entry_price)
                    pnl_pct = ((exit_price - entry_price) / entry_price) * 100
                    
                    # Advance running net output ledger
                    current_balance += pnl_amount
                    
                    # Log parameters to data storage array, dropping precise_exit_time_ist cleanly
                    results.append({
                        'signal_date': current_day.date(),
                        'symbol': symbol,
                        'entry_price': round(entry_price, 2),
                        'exit_price': round(exit_price, 2),
                        'pnl_amount': round(pnl_amount, 2),
                        'pnl_percentage': round(pnl_pct, 2),
                        'cumulative_balance': round(current_balance, 2),
                        'outcome': outcome,
                        'vix_value': round(signal['vix_value'], 2),
                        'market_regime': signal['market_regime'],
                        'exit_date_daily': hit_date.date() if hasattr(hit_date, 'date') and hit_date else hit_date,
                        'days_to_result': days_taken,
                        'z_score': round(signal['z_score'], 2)
                    })
                    
                    print(f"🎯 [{current_day.date()}] {symbol}: {outcome} | PnL: ₹{pnl_amount:,.2f} | Shares: {qty}")

        if results:
            report = pd.DataFrame(results)
            filename = f"backtest_report_{start_date.replace('-','')}.csv"
            report.to_csv(filename, index=False)
            print(f"\n📊 Report saved: {os.getcwd()}/{filename}")
            print(f"💰 Final Yield Position Balance: ₹{current_balance:,.2f}")
        else:
            print("No signals found. Consider using more volatile tickers or relaxing Z-score.")

        # Stop performance timer and log execution profile
        end_perf_time = time.perf_counter()
        end_time_ist = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        total_execution_time = end_perf_time - start_perf_time

        # Convert raw seconds into an integer duration tracking hours, minutes, and seconds
        hours = int(total_execution_time // 3600)
        minutes = int((total_execution_time % 3600) // 60)
        seconds = total_execution_time % 60
        # print(f"⏱️ Total Script Execution Time: {total_execution_time:.4f} seconds")
        print("\n" + "="*50)
        print(f"🛫 Backtest Started (IST) : {start_time_ist}")
        print(f"🛬 Backtest Ended (IST)   : {end_time_ist}")
        print(f"⏱️ Total Execution Time   : {hours} hrs, {minutes} mins, {seconds:.2f} secs")
        print("="*50 + "\n")

if __name__ == "__main__":
    engine = BacktestEngine()
    engine.run("2020-01-01", "2026-04-30")