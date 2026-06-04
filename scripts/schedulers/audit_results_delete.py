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
    print("\n📊 MASTER LOG DATA DISTRIBUTION CHARACTERISTICS")
    print("-" * 60)
    for col in ['shannon_entropy', 'fft_cycle_period', 'rawrs_score']:
        if col in df.columns:
            print(f"🔹 {col:<20} -> Min: {df[col].min():.2f} | 25%: {df[col].quantile(0.25):.2f} | 50% (Med): {df[col].quantile(0.50):.2f} | 75%: {df[col].quantile(0.75):.2f} | Max: {df[col].max():.2f}")
    print("-" * 60)
    total_trades = len(df)
    print(f"📈 Total Baseline Z-Score Signals Triggered: {total_trades}")
    print("-" * 60)

    # Helper function to compute institutional analytics
    def calculate_metrics(data_slice, label):
        if len(data_slice) == 0:
            print(f"⚠️ No matching trades found for setup: {label}")
            return
        
        # Flexibly handle both shortened and long-form string outcomes
        wins = len(data_slice[data_slice['outcome'].isin(['HIT_TARGET', 'TARGET', 'T'])])
        losses = len(data_slice[data_slice['outcome'].isin(['HIT_STOP_LOSS', 'SL', 'S'])])
        expired = len(data_slice[data_slice['outcome'].isin(['EXPIRED', 'E'])])
        
        win_rate = (wins / len(data_slice)) * 100
        
        total_profit = data_slice[data_slice['pnl_amount'] > 0]['pnl_amount'].sum()
        total_loss = abs(data_slice[data_slice['pnl_amount'] < 0]['pnl_amount'].sum())
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        # Calculate average tracking holding periods
        avg_days = data_slice[data_slice['outcome'].isin(['HIT_TARGET', 'TARGET', 'T'])]['days_to_result'].mean()
        
        print(f"🧬 PROFILE: {label}")
        print(f"   Trades Executed : {len(data_slice)}")
        print(f"   Win Rate        : {win_rate:.2f}% (Targets: {wins} | Stops: {losses} | Expired: {expired})")
        print(f"   Profit Factor   : {profit_factor:.2f}x")
        print(f"   Avg Days to TP  : {avg_days:.1f} sessions" if not np.isnan(avg_days) else "   Avg Days to TP  : N/A")
        print("-" * 60)

    # 1. Evaluate the absolute Baseline performance profile
    calculate_metrics(df, "RAW CORE Z-SCORE SETUP (No Filtering Multi-Matrix)")

    # 2. Evaluate the Shannon Entropy Noise Shield Gate (Calibrated to true <= 1.84 median)
    if 'shannon_entropy' in df.columns:
        low_chaos_slice = df[df['shannon_entropy'] <= 1.84]
        calculate_metrics(low_chaos_slice, "FILTERED BY SHANNON ENTROPY (Low Chaos Noise Shield Active <= 1.84)")

    # 3. Evaluate the FFT Cycle Period Gate (Calibrated to look for swing setups between 3 and 30 sessions)
    if 'fft_cycle_period' in df.columns:
        valid_cycle_slice = df[(df['fft_cycle_period'] >= 3.0) & (df['fft_cycle_period'] <= 30.0)]
        calculate_metrics(valid_cycle_slice, "FILTERED BY FFT CYCLE (3-30 Session Swing Wave Extracted)")

    # 4. Evaluate the New RAWRS Continuous Surface Score Gate
    rawrs_col = 'rawrs_modifier' if 'rawrs_modifier' in df.columns else ('rawrs_score' if 'rawrs_score' in df.columns else None)
    if rawrs_col:
        high_wavelet_conviction = df[df[rawrs_col] >= 0.65]
        calculate_metrics(high_wavelet_conviction, f"FILTERED BY RAWRS WAVELET SURFACE ({rawrs_col} >= 0.65)")

    # 5. Evaluate the Macro Alignment Gate (Using your newly patched live nifty_slope metric)
    if 'nifty_slope' in df.columns:
        macro_aligned_slice = df[df['nifty_slope'] > 0.0]
        calculate_metrics(macro_aligned_slice, "FILTERED BY MACRO ALIGNMENT (Nifty Regime Slope > 0.0)")

    # 6. Evaluate High Conviction Ensemble Sweet Spots
    if 'ensemble_strength_score' in df.columns:
        high_conviction = df[df['ensemble_strength_score'] >= 70.0]
        calculate_metrics(high_conviction, "HIGH CONVICTION ENSEMBLE SYSTEM (Strength Score >= 70.0%)")

def run_advanced_quant_audit(csv_path, capital_per_trade=100000):
    if not os.path.exists(csv_path):
        print(f"❌ Error: Ledger file not found at {csv_path}")
        return

    # Load the backtest historical ledger with explicit date format parsing
    df = pd.read_csv(csv_path)
    
    # Force pandas to recognize day-first Indian/UK date layouts (e.g., 13-04-2020)
    df['backtest_date'] = pd.to_datetime(df['backtest_date'], dayfirst=True, errors='coerce')
    df['exit_date'] = pd.to_datetime(df['exit_date'], dayfirst=True, errors='coerce')
    
    # Backup mapping: if dropping NaT leaves gaps, fall back to parsing string slices
    if df['backtest_date'].isna().sum() > 0:
        # Re-read raw to extract string elements safely if timestamp conversion was jagged
        raw_strings = pd.read_csv(csv_path)
        df['year'] = raw_strings['backtest_date'].apply(lambda x: int(str(x).split('-')[-1].split(' ')[0]) if pd.notna(x) else np.nan)
    else:
        df['year'] = df['backtest_date'].dt.year

    # Drop true null records if they lack any year data footprint
    df = df.dropna(subset=['year'])
    df['year'] = df['year'].astype(int)

    print("\n==================================================================")
    print("      🏆 VERIDIAN QUANT ADVANCED MULTI-DIMENSIONAL AUDIT REPORT  ")
    print("==================================================================")

    # Track aggregate calculation values to double check against file totals
    calculated_cumulative_pnl = 0.0
    processed_trades_count = 0

    # Clean multi-year group processing loop
    for year, df_year in df.groupby('year'):
        
        # --- 1. PERFORMANCE & PNL LAYER ---
        # Capture all variations of target strings comprehensively
        targets = df_year[df_year['outcome'].isin(['TARGET', 'HIT_TARGET', 'T'])]
        sls = df_year[df_year['outcome'].isin(['SL', 'HIT_STOP_LOSS', 'S'])]
        exps = df_year[df_year['outcome'].isin(['EXPIRED', 'E'])]
        
        # Pull clean summation directly across the year subset spectrum
        yearly_net_profit = df_year['pnl_amount'].sum() if 'pnl_amount' in df_year.columns else 0.0
        calculated_cumulative_pnl += yearly_net_profit
        processed_trades_count += len(df_year)
        
        # --- 2. WAVELET INTENSITY ANALYTICS ---
        wave_col = 'wavelet_intensity' if 'wavelet_intensity' in df_year.columns else ('rawrs_modifier' if 'rawrs_modifier' in df_year.columns else None)
        if wave_col:
            avg_cwt_target = targets[wave_col].mean() if not targets.empty else 0
            avg_cwt_sl = sls[wave_col].mean() if not sls.empty else 0
            median_cwt_sl = sls[wave_col].median() if not sls.empty else 0
        else:
            avg_cwt_target, avg_cwt_sl, median_cwt_sl = 0.0, 0.0, 0.0
            
        # --- 3. PEAK LOCKED CAPITAL & IDLE TIME TIMELINE PARSING ---
        date_range = pd.date_range(start=f"{year}-01-01", end=f"{year}-12-31")
        daily_capital_allocation = pd.Series(0, index=date_range)
        
        for _, trade in df_year.iterrows():
            start_dt = trade['backtest_date']
            if pd.isna(start_dt):
                continue
                
            if pd.isna(trade['exit_date']):
                if 'days_to_result' in trade and not pd.isna(trade['days_to_result']):
                    end_dt = start_dt + pd.Timedelta(days=int(trade['days_to_result']))
                else:
                    end_dt = start_dt 
            else:
                end_dt = trade['exit_date']
                
            try:
                trade_days = pd.date_range(start=start_dt, end=end_dt)
                valid_days = trade_days.intersection(date_range)
                daily_capital_allocation.loc[valid_days] += capital_per_trade
            except Exception:
                # Fallback if specific row has corrupted bounds to protect matrix loop execution
                daily_capital_allocation.loc[start_dt] += capital_per_trade
            
        peak_capital_locked = daily_capital_allocation.max()
        concurrent_trades = int(peak_capital_locked / capital_per_trade) if capital_per_trade > 0 else 0
        
        idle_days = (daily_capital_allocation == 0).sum()
        active_days = len(date_range) - idle_days
        capital_efficiency = (active_days / len(date_range)) * 100

        # --- 4. PRINT DIAGNOSTIC OUTCOMES ---
        print(f"\n📅 YEAR: {year}")
        print(f"------------------------------------------------------------------")
        print(f"💵 Total Net Profit Generated : ₹{yearly_net_profit:,.2f}")
        print(f"💰 Peak Capital Locked         : ₹{peak_capital_locked:,.2f} ({concurrent_trades} Simultaneous Positions)")
        print(f"💤 Capital Idle Deployment      : {idle_days} Days Clear | {active_days} Days Active ({capital_efficiency:.1f}% Market Exposure)")
        print(f"🌊 Avg Wavelet Intensity (T)  : {avg_cwt_target:.4f}")
        print(f"🌊 Avg Wavelet Intensity (SL) : {avg_cwt_sl:.4f} (Median: {median_cwt_sl:.4f})")
        print(f"📊 Total Trades Logged         : {len(df_year)} | Hits: {len(targets)} | Losses: {len(sls)} | Expired: {len(exps)}")
        print(f"------------------------------------------------------------------")

    print("\n" + "="*66)
    print(f"🧮 SYSTEM INTEGRITY CHECKSUM")
    print(f"   Processed Audit Trades Count : {processed_trades_count} / {len(df)}")
    print(f"   Calculated Consolidated PnL  : ₹{calculated_cumulative_pnl:,.2f}")
    print("="*66 + "\n")

if __name__ == "__main__":
    ledger_file = "backtest_report_20200101.csv"
    
    # Step 1: Run your baseline strategy-by-strategy filter matrices
    analyze_backtest_matrix()
    
    # Step 2: Run the chronological clean annual audit timeline
    run_advanced_quant_audit(ledger_file, capital_per_trade=100000)