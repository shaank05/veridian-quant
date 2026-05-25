import pandas as pd
import os
import json
from sqlalchemy import text
from dotenv import load_dotenv
from src.veridian_quant.data.db_client import DatabaseClient
from src.veridian_quant.core.signals.equity_scanner import EquityScanner

load_dotenv()

class BacktestEngine:
    def __init__(self):
        self.db = DatabaseClient()
        # Ensure source_table matches your DB: 'prices_ohlc'
        self.scanner = EquityScanner(self.db.get_engine(), mode='BACKTEST', source_table='prices_ohlc')

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

    def get_precise_exit_time(self, inst_key, exit_date, execution_type, target_boundary):
        """
        Queries 1-minute historical intraday charts exclusively on the day of the trade exit.
        Returns precise IST granular time of breach to minimize memory pipeline overhead.
        """
        if not exit_date:
            return None
            
        column_filter = "high >= :boundary" if execution_type == "HIT_TARGET" else "low <= :boundary"
        
        query = text(f"""
            SELECT timestamp FROM prices_ohlc
            WHERE instrument_key = :inst_key 
              AND interval = '1m'
              AND timestamp::date = :exit_date
              AND {column_filter}
            ORDER BY timestamp ASC LIMIT 1;
        """)
        
        try:
            clean_date = exit_date.strftime('%Y-%m-%d') if hasattr(exit_date, 'strftime') else str(exit_date)[:10]
            clean_boundary = float(target_boundary)

            with self.db.get_engine().connect() as conn:
                res = conn.execute(query, {
                    "inst_key": inst_key,
                    "exit_date": clean_date,
                    "boundary": clean_boundary
                }).fetchone()
                
                if res:
                    return res[0]
            return exit_date
        except Exception as e:
            print(f"Warning extraction minute-level execution data failed: {e}")
            return exit_date

    def run(self, start_date, end_date):
        """
        Executes the backtest and calculates compounding mathematical returns
        driven by the Stage 2.5 Risk-Equalized Sizing Engine.
        """
        # Compounding balance initialization baseline
        INITIAL_BACKTEST_EQUITY = 10000000.0
        current_balance = INITIAL_BACKTEST_EQUITY
        
        symbols = self.get_watchlist_symbols()
        if not symbols:
            print("Watchlist is empty. Exiting.")
            return

        query = "SELECT instrument_key, symbol FROM instruments WHERE symbol IN :symbols;"
        
        try:
            instruments = self.db.execute_query(query, {"symbols": tuple(symbols)})
        except Exception as e:
            print(f"❌ Error fetching instruments: {e}")
            return

        if not instruments:
            print("No matching instruments found in DB.")
            return

        print(f"🧐 Scanning {len(instruments)} instruments from {start_date} to {end_date}...")
        test_days = pd.date_range(start=start_date, end=end_date, freq='B')
        results = []

        for current_day in test_days:
            for inst_key, symbol in instruments:
                # Upgraded to pass the dynamic compounding portfolio balance straight into scanner logic
                signal = self.scanner.scan_instrument(
                    inst_key, symbol, as_of_date=current_day, portfolio_equity=current_balance
                )
                
                if signal:
                    outcome, hit_date, days_taken = self.verify_outcome(
                        inst_key, current_day, signal['target_1'], signal['stop_loss']
                    )
                    
                    # --- PnL CALCULATION ENGINE ---
                    entry_price = signal['entry_price']
                    qty = signal['final_share_quantity']
                    
                    # Skip signal parsing if quantity calculations drop to zero (due to capital squeeze boundaries)
                    if qty <= 0:
                        continue

                    # Map outcome to price and extract hyper-precision 1-minute exit timestamp
                    if outcome == "HIT_TARGET":
                        exit_price = signal['target_1']
                        precise_exit_timestamp = self.get_precise_exit_time(inst_key, hit_date, outcome, signal['target_1'])
                    elif outcome == "HIT_STOP_LOSS":
                        exit_price = signal['stop_loss']
                        precise_exit_timestamp = self.get_precise_exit_time(inst_key, hit_date, outcome, signal['stop_loss'])
                    else:
                        exit_price = entry_price  # No-op for EXPIRED/ERROR
                        precise_exit_timestamp = hit_date
                    
                    # Compute actual monetary PnL based on calculated risk-equalized quantities
                    pnl_amount = qty * (exit_price - entry_price)
                    pnl_pct = ((exit_price - entry_price) / entry_price) * 100
                    
                    # Track compounding running wallet expansion/contraction
                    current_balance += pnl_amount
                    
                    # Log parameters to data storage array
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
                        'precise_exit_time_ist': precise_exit_timestamp,
                        'days_to_result': days_taken,
                        'z_score': round(signal['z_score'], 2),
                        
                        # Capturing sizing traces in backtest spreadsheets
                        'shares_held': qty,
                        'capital_deployed': round(signal['final_capital_allocation'], 2),
                        'is_allocation_clamped': signal['is_allocation_clamped']
                    })
                    
                    print(f"🎯 [{current_day.date()}] {symbol}: {outcome} | PnL: ₹{pnl_amount:,.2f} | Shares: {qty} | Clamped: {signal['is_allocation_clamped']}")

        if results:
            report = pd.DataFrame(results)
            filename = f"backtest_report_{start_date.replace('-','')}.csv"
            report.to_csv(filename, index=False)
            print(f"\n📊 Report saved: {os.getcwd()}/{filename}")
            print(f"💰 Final Backtest Balance: ₹{current_balance:,.2f}")
        else:
            print("No signals found. Consider using more volatile tickers or relaxing Z-score.")

if __name__ == "__main__":
    engine = BacktestEngine()
    engine.run("2020-03-01", "2025-12-31")