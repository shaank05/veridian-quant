import pandas as pd
import os
import json
import time  
import numpy as np
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
    market datasets. Coordinates daily processing pipelines by loading parameters from 
    watchlist configurations while eliminating multi-firing signal anomalies via an 
    in-memory portfolio position registry tracking matrix.
    """
    def __init__(self):
        self.db = DatabaseClient()
        self.scanner = EquityScanner(self.db.get_engine(), mode='BACKTEST', source_table='prices_ohlc')

    def get_watchlist_symbols(self):
        """
        Loads configured universe ticker targets from root > config setup profiles.
        """
        try:
            with open('config/watchlist.json', 'r') as f:
                data = json.load(f)
                symbols = data.get('one_minute_targets', []) + data.get('one_day_targets', [])
                
                if "NIFTY" not in symbols:
                    symbols.append("NIFTY")
                    
                print(f"✅ Loaded {len(symbols)} symbols from watchlist matrix configurations.")
                return symbols
        except Exception as e:
            print(f"❌ Error loading system backtest active target ticker array: {str(e)}")
            return []

    def fetch_historical_matrix(self, symbol, end_date):
        """
        Pulls sequential historical data by joining the prices ledger with the 
        instruments metadata table to match human-readable watchlist symbols.
        """
        if symbol == "NIFTY":
            query = text("""
                SELECT p.timestamp AS date, p.open, p.high, p.low, p.close, p.volume 
                FROM prices_ohlc p
                WHERE p.instrument_key = 'NSE_INDEX|Nifty 50' AND p.timestamp::date <= :end_date
                ORDER BY p.timestamp DESC LIMIT 100;
            """)
        else:
            query = text("""
                SELECT p.timestamp AS date, p.open, p.high, p.low, p.close, p.volume 
                FROM prices_ohlc p
                INNER JOIN instruments i ON p.instrument_key = i.instrument_key
                WHERE (i.symbol = :symbol OR i.trading_symbol = :symbol)
                  AND p.timestamp::date <= :end_date
                ORDER BY p.timestamp DESC LIMIT 100;
            """)
            
        try:
            with self.db.get_engine().connect() as conn:
                df = pd.read_sql(query, conn, params={"symbol": symbol, "end_date": end_date})
                if not df.empty:
                    df = df.iloc[::-1].reset_index(drop=True)
                    df['date'] = pd.to_datetime(df['date'])
                return df
        except Exception as e:
            print(f"❌ Structural exception pulling database timeframe matrix slice for [{symbol}]: {str(e)}")
            return pd.DataFrame()

    def verify_outcome(self, symbol, signal_date, target, stop_loss):
        """
        Chronological Window Audit Track.
        Evaluates a 30-day forward price matrix following a signal timestamp 
        by joining with metadata to map symbols onto internal table records.
        """
        query = text("""
            SELECT p.timestamp, p.high, p.low 
            FROM prices_ohlc p
            INNER JOIN instruments i ON p.instrument_key = i.instrument_key
            WHERE (i.symbol = :symbol OR i.trading_symbol = :symbol)
              AND p.timestamp::date > :signal_date
            ORDER BY p.timestamp ASC LIMIT 30;
        """)
        try:
            with self.db.get_engine().connect() as conn:
                df = pd.read_sql(query, conn, params={"symbol": symbol, "signal_date": signal_date})
            
            if df.empty: 
                return "NO_FUTURE_DATA", None, None

            # Loop through future data ticks day-by-day to verify trade exit resolution
            for idx, row in df.iterrows():
                if row['high'] >= target: 
                    return "HIT_TARGET", row['timestamp'], idx + 1
                if row['low'] <= stop_loss: 
                    return "HIT_STOP_LOSS", row['timestamp'], idx + 1
                    
            return "EXPIRED", None, 30
        except Exception as e:
            print(f"❌ Error verifying outcome for [{symbol}] on {signal_date}: {str(e)}")
            return "ERROR", None, None

    def run_backtest_ledger_loop(self, start_date, end_date):
        """
        Executes strict forward chronological iteration sequences with continuous position modulation.
        """
        print("="*60)
        print(f"🚀 VERIDIAN QUANT BACKTEST MATRIX ITERATION LOOP ENGINE DEPLOYED")
        print(f"🗓️ Horizon Scope: {start_date} to {end_date}")
        print("="*60)
        
        start_perf_time = time.perf_counter()
        start_time_ist = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")

        trading_days = pd.bdate_range(start=start_date, end=end_date)
        symbols = self.get_watchlist_symbols()
        
        if not symbols or len(symbols) <= 1:
            print("⚠️ Empty active stock tracking universe asset registry matrix. Aborting loop.")
            return

        results = []
        initial_balance = 1000000.00  # Shift baseline account scale up for portfolio tracking simulation
        current_balance = initial_balance
        base_unit_capital = 100000.00  # Reference sizing unit

        # IN-MEMORY REGISTRY: Simulates database recommendation table state tracking
        active_positions = {}

        for current_day in trading_days:
            day_str = current_day.strftime('%Y-%m-%d')
            current_date_obj = current_day.date()

            # 1. Housekeeping: Remove expired or hit positions whose exit boundaries have passed
            active_positions = {sym: ext_dt for sym, ext_dt in active_positions.items() if ext_dt > current_date_obj}

            print(f"⌛ [BACKTEST LOOP PROGRESS] processing historical slice matrix data timeline window for date node -> [{day_str}]")

            tickers_data_package = {}
            for symbol in symbols:
                if symbol in active_positions:
                    continue

                hist_df = self.fetch_historical_matrix(symbol, day_str)
                if not hist_df.empty and len(hist_df) >= 35:
                    tickers_data_package[symbol] = hist_df

            # Always guarantee NIFTY historical depth context is loaded for macro filters
            if "NIFTY" not in tickers_data_package and "NIFTY" not in active_positions:
                nifty_df = self.fetch_historical_matrix("NIFTY", day_str)
                if not nifty_df.empty:
                    tickers_data_package["NIFTY"] = nifty_df

            if not tickers_data_package or (len(tickers_data_package) == 1 and "NIFTY" in tickers_data_package):
                continue
            
            day_signals = self.scanner.execute_concurrent_analysis(tickers_data_package, day_str)
            
            for payload in day_signals:
                symbol = payload.get("symbol")
                
                if symbol in active_positions:
                    continue

                entry_price = payload.get("entry_price")
                target_price = payload.get("target_price")
                stop_loss_price = payload.get("stop_loss_price")
                metrics_bag = payload.get("metrics", {})
                
                # Extract Continuous Conviction metrics to modulate size
                rawrs_mod = metrics_bag.get("rawrs_modifier", 0.5)
                strength_score = metrics_bag.get("ensemble_strength_score", 50.0)
                
                # --- NEW UNLOCKED CONTINUOUS CONVICTION POSITION MODULATION ENGINE ---
                # Derive multiplier based smoothly on mathematical features
                strength_factor = (strength_score / 100.0)
                conviction_multiplier = (0.6 * rawrs_mod) + (0.4 * strength_factor)
                
                # Bound adjustments cleanly between 0.25x and 1.50x of our baseline allocation capital
                modulated_multiplier = float(np.clip(conviction_multiplier * 2.0, 0.25, 1.50))
                allocated_capital = base_unit_capital * modulated_multiplier
                
                # Adjust capital sizing proportionally if account growth or deep drawdown shifts account scale
                compounding_scaling_factor = current_balance / initial_balance
                final_adjusted_capital = allocated_capital * max(0.5, min(2.0, compounding_scaling_factor))
                
                # Safeguard rule: protect portfolio logic from risking more than 20% total equity on one ticker
                if final_adjusted_capital > (current_balance * 0.20):
                    final_adjusted_capital = current_balance * 0.20

                # Run the chronological window audit check against future data
                outcome, hit_date, days_taken = self.verify_outcome(
                    symbol, day_str, target_price, stop_loss_price
                )
                
                if hit_date:
                    exit_date_obj = pd.to_datetime(hit_date).date()
                else:
                    exit_date_obj = (current_day + pd.Timedelta(days=30)).date()

                active_positions[symbol] = exit_date_obj
                
                # Establish execution volume using modulated capital bounds
                qty = int(final_adjusted_capital // entry_price) if entry_price and entry_price > 0 else 0
                if qty <= 0:
                    continue
                    
                if outcome == "HIT_TARGET":
                    exit_price = target_price
                elif outcome == "HIT_STOP_LOSS":
                    exit_price = stop_loss_price
                else:
                    exit_price = entry_price  # Expired horizon fallback
                    
                # Compute financial balance adjustments
                pnl_amount = qty * (exit_price - entry_price)
                pnl_pct = ((exit_price - entry_price) / entry_price) * 100 if entry_price else 0.0
                current_balance += pnl_amount
                
                flattened_row = {
                    "backtest_date": day_str,
                    "symbol": symbol,
                    "entry_price": entry_price,
                    "target_price": target_price,
                    "stop_loss_price": stop_loss_price,
                    "exit_price": exit_price,
                    "outcome": outcome,
                    "exit_date": exit_date_obj.strftime('%Y-%m-%d'),
                    "days_to_result": days_taken,
                    "shares_traded": qty,
                    "allocated_capital": round(final_adjusted_capital, 2),
                    "pnl_amount": round(pnl_amount, 2),
                    "pnl_percentage": round(pnl_pct, 2),
                    "cumulative_balance": round(current_balance, 2),
                    "market_regime": payload.get("market_regime"),
                    "vix_value": metrics_bag.get("vix_value", 15.0),
                    "nifty_slope": metrics_bag.get("nifty_slope", 0.0),
                    "z_score": metrics_bag.get("z_score", 0.0),
                    "expected_move": metrics_bag.get("expected_move", 0.0),
                    "shannon_entropy": metrics_bag.get("shannon_entropy", 0.0),
                    "fft_cycle_period": metrics_bag.get("fft_cycle_period", 0.0),
                    "markov_regime_state": metrics_bag.get("markov_regime_state", 0),
                    "wavelet_intensity": metrics_bag.get("wavelet_intensity", 1.0),
                    "rawrs_score": rawrs_mod,
                    "ensemble_strength_score": strength_score
                }
                results.append(flattened_row)
                
                print(f"📡 [SIGNAL LOGGED WITH CONVICTION SIZE] Day: {day_str} | Asset: {symbol} | size-mult: {modulated_multiplier:.2f}x | Outcome: {outcome} | "
                      f"PnL: ₹{pnl_amount:,.2f} | Balance: ₹{current_balance:,.2f}")

        if results:
            report = pd.DataFrame(results)
            filename = f"backtest_report_{start_date.replace('-','')}.csv"
            report.to_csv(filename, index=False)
            print(f"\n📊 Multi-Dimensional Matrix Report saved: {os.getcwd()}/{filename}")
            print(f"💰 Final Yield Position Balance: ₹{current_balance:,.2f}")
        else:
            print("No signals found. Check tracking parameters or universe dataset depth.")

        end_perf_time = time.perf_counter()
        end_time_ist = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        total_execution_time = end_perf_time - start_perf_time

        hours = int(total_execution_time // 3600)
        minutes = int((total_execution_time % 3600) // 60)
        seconds = total_execution_time % 60
        
        print("\n" + "="*50)
        print(f"🛫 Backtest Pass Started (IST) : {start_time_ist}")
        print(f"🛬 Backtest Pass Finished (IST): {end_time_ist}")
        print(f"⏱️ Total Ledger Search Compute Window: {hours}h {minutes}m {seconds:.2f}s")
        print("="*50 + "\n")

if __name__ == "__main__":
    engine = BacktestEngine()
    engine.run_backtest_ledger_loop("2020-01-01", "2026-04-30")