import pandas as pd
import numpy as np
import os

def analyze_backtest_matrix():
    # Target your newly generated multi-strategy matrix file
    csv_file = "backtest_report_20200101.csv"
    
    if not os.path.exists(csv_file):
        print(f"❌ Could not locate {csv_file}. Verify your current working directory.")
        return

    print("\n============================================================")
    print("  📊 PARALLEL STRATEGY REGISTRY BASELINE PERFORMANCE REPORT  ")
    print("============================================================\n")
    
    df = pd.read_csv(csv_file)
    total_trades = len(df)
    print(f"📈 Total Baseline Z-Score Signals Triggered: {total_trades}")
    print("-" * 60)

    # Helper function to compute institutional analytics
    def calculate_metrics(data_slice, label):
        if len(data_slice) == 0:
            print(f"⚠️ No matching trades found for setup: {label}")
            return
        
        # Flexibly handle both shortened and long-form string outcomes
        wins = len(data_slice[data_slice['outcome'].isin(['HIT_TARGET', 'TARGET'])])
        losses = len(data_slice[data_slice['outcome'].isin(['HIT_STOP_LOSS', 'SL'])])
        expired = len(data_slice[data_slice['outcome'].isin(['EXPIRED'])])
        
        win_rate = (wins / len(data_slice)) * 100
        
        total_profit = data_slice[data_slice['pnl_amount'] > 0]['pnl_amount'].sum()
        total_loss = abs(data_slice[data_slice['pnl_amount'] < 0]['pnl_amount'].sum())
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        # Calculate average tracking holding periods
        avg_days = data_slice[data_slice['outcome'].isin(['HIT_TARGET', 'TARGET'])]['days_to_result'].mean()
        
        print(f"🧬 PROFILE: {label}")
        print(f"   Trades Executed : {len(data_slice)}")
        print(f"   Win Rate        : {win_rate:.2f}% (Targets: {wins} | Stops: {losses} | Expired: {expired})")
        print(f"   Profit Factor   : {profit_factor:.2f}x")
        print(f"   Avg Days to TP  : {avg_days:.1f} sessions" if not np.isnan(avg_days) else "   Avg Days to TP  : N/A")
        print("-" * 60)

    # 1. Evaluate the absolute Baseline performance profile
    calculate_metrics(df, "RAW CORE Z-SCORE SETUP (No Filtering Multi-Matrix)")

    # 2. Evaluate the Shannon Entropy Noise Shield Gate
    if 'shannon_entropy_vote' in df.columns:
        calculate_metrics(df[df['shannon_entropy_vote'] == 1], "FILTERED BY SHANNON ENTROPY (Low Chaos Noise Shield Active)")

    # 3. Evaluate the FFT Phase Timing Gate
    if 'fft_cycle_turning_vote_vote' in df.columns: 
        calculate_metrics(df[df['fft_cycle_turning_vote_vote'] == 1], "FILTERED BY FFT CYCLE (Momentum Turning Verified)")
    elif 'fft_cycle_turning_vote' in df.columns:
        calculate_metrics(df[df['fft_cycle_turning_vote'] == 1], "FILTERED BY FFT CYCLE (Momentum Turning Verified)")

    # 4. Evaluate the Volume Spread Analysis Stance Gate
    if 'vsa_confirmed_vote_vote' in df.columns:
        calculate_metrics(df[df['vsa_confirmed_vote_vote'] == 1], "FILTERED BY VSA (Institutional Accumulation Confirmed)")
    elif 'vsa_confirmed_vote' in df.columns:
        calculate_metrics(df[df['vsa_confirmed_vote'] == 1], "FILTERED BY VSA (Institutional Accumulation Confirmed)")

    # 5. Evaluate the Anti-Cascade Markov Transition State Gate
    if 'markov_vote_vote' in df.columns:
        calculate_metrics(df[df['markov_vote_vote'] == 1], "FILTERED BY MARKOV OVERLAYS (Protected from State 0 Cascades)")
    elif 'markov_vote' in df.columns:
        calculate_metrics(df[df['markov_vote'] == 1], "FILTERED BY MARKOV OVERLAYS (Protected from State 0 Cascades)")

    # 6. Evaluate High Conviction Ensemble Sweet Spots (Stage 5 Simulation)
    if 'ensemble_conviction_score' in df.columns:
        high_conviction = df[df['ensemble_conviction_score'] >= 75.0]
        calculate_metrics(high_conviction, "HIGH CONVICTION ENSEMBLE (Conviction Score >= 75.0%)")

def run_advanced_quant_audit(csv_path, capital_per_trade=100000):
    if not os.path.exists(csv_path):
        print(f"❌ Error: Ledger file not found at {csv_path}")
        return

    # Load the backtest historical ledger
    df = pd.read_csv(csv_path)
    
    # Map precisely to your engine's true historical ledger keys
    df['signal_date'] = pd.to_datetime(df['signal_date'])
    df['exit_date_daily'] = pd.to_datetime(df['exit_date_daily'], errors='coerce')
    df['year'] = df['signal_date'].dt.year

    print("\n==================================================================")
    print("      🏆 VERIDIAN QUANT ADVANCED MULTI-DIMENSIONAL AUDIT REPORT  ")
    print("==================================================================\n")

    years = sorted(df['year'].unique())
    
    for year in years:
        df_year = df[df['year'] == year]
        
        # --- 1. PERFORMANCE & PNL LAYER ---
        targets = df_year[df_year['outcome'].isin(['TARGET', 'HIT_TARGET'])]
        sls = df_year[df_year['outcome'].isin(['SL', 'HIT_STOP_LOSS'])]
        
        # Calculate total absolute performance metrics per year
        yearly_net_profit = df_year['pnl_amount'].sum() if 'pnl_amount' in df_year.columns else 0.0
        
        # --- 2. WAVELET INTENSITY ANALYTICS (MEDIAN & MEAN TO CUT SKUES) ---
        avg_cwt_target = targets['wavelet_intensity'].mean() if not targets.empty else 0
        avg_cwt_sl = sls['wavelet_intensity'].mean() if not sls.empty else 0
        median_cwt_sl = sls['wavelet_intensity'].median() if not sls.empty else 0
        
        # --- 3. PEAK LOCKED CAPITAL & IDLE TIME TIMELINE PARSING ---
        date_range = pd.date_range(start=f"{year}-01-01", end=f"{year}-12-31")
        daily_capital_allocation = pd.Series(0, index=date_range)
        
        for _, trade in df_year.iterrows():
            if pd.isna(trade['signal_date']):
                continue
                
            start_dt = trade['signal_date']
            
            # Handle EXPIRED trades lacking an exit date safely
            if pd.isna(trade['exit_date_daily']):
                if 'days_to_result' in trade and not pd.isna(trade['days_to_result']):
                    end_dt = start_dt + pd.Timedelta(days=int(trade['days_to_result']))
                else:
                    end_dt = start_dt 
            else:
                end_dt = trade['exit_date_daily']
                
            trade_days = pd.date_range(start=start_dt, end=end_dt)
            valid_days = trade_days.intersection(date_range)
            daily_capital_allocation.loc[valid_days] += capital_per_trade
            
        peak_capital_locked = daily_capital_allocation.max()
        concurrent_trades = int(peak_capital_locked / capital_per_trade)
        
        # Calculate Capital Idle Days (Days where no capital was deployed at all)
        idle_days = (daily_capital_allocation == 0).sum()
        active_days = len(date_range) - idle_days
        capital_efficiency = (active_days / len(date_range)) * 100

        # --- 4. PRINT DIAGNOSTIC OUTCOMES ---
        print(f"📅 YEAR: {year}")
        print(f"------------------------------------------------------------------")
        print(f"💵 Total Net Profit Generated : ₹{yearly_net_profit:,.2f}")
        print(f"💰 Peak Capital Locked         : ₹{peak_capital_locked:,.2f} ({concurrent_trades} Simultaneous Positions)")
        print(f"💤 Capital Idle Deployment      : {idle_days} Days Clear | {active_days} Days Active ({capital_efficiency:.1f}% Market Exposure)")
        print(f"🌊 Avg CWT Intensity (Target)  : {avg_cwt_target:.4f}")
        print(f"🌊 Avg CWT Intensity (Stop Loss): {avg_cwt_sl:.4f} (Median: {median_cwt_sl:.4f})")
        print(f"📊 Total Trades Logged         : {len(df_year)} | Hits: {len(targets)} | Losses: {len(sls)}")
        print(f"------------------------------------------------------------------\n")

if __name__ == "__main__":
    # Point directly to your historical 6-year ledger file
    ledger_file = "backtest_report_20200101.csv"
    
    # Execution Step 1: Run your strategy-by-strategy matrix breakdown
    analyze_backtest_matrix()
    
    print("\n" + "="*70 + "\n")
    
    # Execution Step 2: Run the peak capital-lock timeline and CWT signature audit
    run_advanced_quant_audit(ledger_file, capital_per_trade=100000)